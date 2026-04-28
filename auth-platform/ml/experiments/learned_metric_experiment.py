"""Learned metric experiment utilities.

Supports configurable backbone, pretrained weights, label strategy, and
augmentations for comparing learned models against hand-crafted baselines.

Results are diagnostic only — they do not prove authentication accuracy.
"""

from __future__ import annotations

import io
import random
from dataclasses import dataclass, field
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812
import yaml
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms

from experiments.dataset_loader import load_image_bytes
from experiments.metrics import compute_metrics

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class LMExperimentConfig:
    model_name: str = "learned_metric"
    model_version: str = "v0.2.0"
    dataset_version: str = ""
    backbone: str = "resnet18"
    pretrained: bool = True
    embedding_dim: int = 256
    input_size: int = 224
    loss: str = "contrastive"
    margin: float = 1.0
    epochs: int = 20
    batch_size: int = 16
    learning_rate: float = 0.0005
    weight_decay: float = 0.0001
    seed: int = 42
    freeze_backbone: bool = False
    label_strategy: str = "external_item_id"
    augmentation_profile: str = ""  # none/light/medium/strong; empty = use augmentations dict
    augmentations: dict = field(default_factory=dict)
    optimizer: dict = field(default_factory=lambda: {"name": "adam"})
    scheduler: dict = field(default_factory=lambda: {"name": "none"})
    projection_head: dict = field(default_factory=lambda: {"hidden_dim": 256, "dropout": 0.0, "layers": 2})
    split_policy: dict = field(default_factory=lambda: {
        "train": "train", "validation": "validation", "test": "test",
        "leakage_check_field": "reference_item_id",
    })
    notes: str = ""

    @classmethod
    def from_yaml(cls, path: str | Path) -> LMExperimentConfig:
        data = yaml.safe_load(Path(path).read_text())
        # Extract dict fields that need special handling
        aug = data.pop("augmentations", {})
        split = data.pop("split_policy", {})
        opt = data.pop("optimizer", {})
        sched = data.pop("scheduler", {})
        proj = data.pop("projection_head", {})
        # Filter only known scalar fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(
            **filtered,
            augmentations=aug or {},
            split_policy=split or {},
            optimizer=opt or {"name": "adam"},
            scheduler=sched or {"name": "none"},
            projection_head=proj or {"hidden_dim": 256, "dropout": 0.0, "layers": 2},
        )


def validate_config(config: LMExperimentConfig) -> list[str]:
    """Validate config and return list of warnings."""
    warnings = []
    if config.backbone not in ("resnet18", "resnet50"):
        warnings.append(f"Backbone '{config.backbone}' may not be supported yet")
    from experiments.losses import LOSS_REGISTRY, get_loss_name
    loss_name = get_loss_name(config)
    if loss_name not in LOSS_REGISTRY:
        warnings.append(f"Loss '{loss_name}' may not be implemented yet")
    if not config.dataset_version:
        warnings.append("No dataset_version specified")
    return warnings


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

BACKBONE_FEATURE_DIMS = {"resnet18": 512, "resnet50": 2048}


def create_model(
    backbone: str = "resnet18",
    pretrained: bool = True,
    embedding_dim: int = 256,
    allow_random_init: bool = False,
    freeze_backbone: bool = False,
    projection_head: dict | None = None,
) -> nn.Module:
    """Create an embedding model with configurable backbone.

    If freeze_backbone=True, backbone parameters are frozen and only the
    projection head is trainable.

    Raises ValueError if pretrained=True but weights unavailable and
    allow_random_init=False.
    """
    if backbone == "resnet18":
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        try:
            base = models.resnet18(weights=weights)
        except Exception:
            if not allow_random_init:
                raise ValueError(
                    f"Pretrained weights for {backbone} unavailable. "
                    "Use --allow-random-init to proceed without pretrained weights."
                ) from None
            base = models.resnet18(weights=None)
    elif backbone == "resnet50":
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        try:
            base = models.resnet50(weights=weights)
        except Exception:
            if not allow_random_init:
                raise ValueError(
                    f"Pretrained weights for {backbone} unavailable. "
                    "Use --allow-random-init to proceed without pretrained weights."
                ) from None
            base = models.resnet50(weights=None)
    else:
        raise ValueError(f"Unsupported backbone: {backbone}")

    feat_dim = BACKBONE_FEATURE_DIMS.get(backbone, 512)
    features = nn.Sequential(*list(base.children())[:-1])

    if freeze_backbone:
        for param in features.parameters():
            param.requires_grad = False

    ph = projection_head or {}
    proj_hidden = ph.get("hidden_dim", min(512, feat_dim))
    dropout = ph.get("dropout", 0.0)

    proj_layers: list[nn.Module] = [
        nn.Linear(feat_dim, proj_hidden),
        nn.ReLU(inplace=True),
    ]
    if dropout > 0:
        proj_layers.append(nn.Dropout(p=dropout))
    proj_layers.append(nn.Linear(proj_hidden, embedding_dim))
    projection = nn.Sequential(*proj_layers)

    class _EmbModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = features
            self.projection = projection

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            f = self.features(x)
            f = f.view(f.size(0), -1)
            e = self.projection(f)
            return F.normalize(e, p=2, dim=1)

    return _EmbModel()


# ---------------------------------------------------------------------------
# Augmented transforms
# ---------------------------------------------------------------------------

AUGMENTATION_PROFILES = {
    "none": {},
    "light": {
        "horizontal_flip": True,
        "rotation_degrees": 10,
        "color_jitter": {"brightness": 0.1, "contrast": 0.1},
    },
    "medium": {
        "random_resized_crop": True,
        "horizontal_flip": True,
        "rotation_degrees": 15,
        "color_jitter": {"brightness": 0.2, "contrast": 0.2, "saturation": 0.1},
        "random_erasing": 0.1,
    },
    "strong": {
        "random_resized_crop": True,
        "horizontal_flip": True,
        "vertical_flip": True,
        "rotation_degrees": 20,
        "color_jitter": {"brightness": 0.3, "contrast": 0.3, "saturation": 0.2},
        "random_erasing": 0.2,
        "gaussian_blur": True,
    },
}


def build_train_transform(config: LMExperimentConfig) -> transforms.Compose:
    """Build training transform from augmentation profile or dict settings."""
    profile = config.augmentation_profile
    if profile and profile in AUGMENTATION_PROFILES:
        aug = AUGMENTATION_PROFILES[profile]
    elif profile and profile not in AUGMENTATION_PROFILES:
        raise ValueError(f"Unknown augmentation profile: {profile}. "
                         f"Available: {list(AUGMENTATION_PROFILES.keys())}")
    else:
        aug = config.augmentations

    t = []
    if aug.get("random_resized_crop"):
        t.append(transforms.RandomResizedCrop(config.input_size, scale=(0.8, 1.0)))
    else:
        t.append(transforms.Resize((config.input_size, config.input_size)))
    if aug.get("horizontal_flip"):
        t.append(transforms.RandomHorizontalFlip())
    if aug.get("vertical_flip"):
        t.append(transforms.RandomVerticalFlip(p=0.2))
    rot = aug.get("rotation_degrees", 0)
    if rot:
        t.append(transforms.RandomRotation(degrees=rot))
    cj = aug.get("color_jitter", {})
    if cj:
        t.append(transforms.ColorJitter(
            brightness=cj.get("brightness", 0),
            contrast=cj.get("contrast", 0),
            saturation=cj.get("saturation", 0),
        ))
    if aug.get("gaussian_blur"):
        t.append(transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)))
    t.append(transforms.ToTensor())
    re = aug.get("random_erasing", 0)
    if re:
        t.append(transforms.RandomErasing(p=re))
    t.append(transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]))
    return transforms.Compose(t)


def build_eval_transform(config: LMExperimentConfig) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((config.input_size, config.input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


# ---------------------------------------------------------------------------
# Label strategy
# ---------------------------------------------------------------------------

def _extract_species_from_uri(uri: str) -> str:
    """Extract species from S3 object URI path.

    LeaData URIs follow: .../raw/{Species}_{SampleCode}/{image_id}.jpg
    Example: .../raw/Sheep_SBTS25/abc.jpg → "Sheep"
    """
    parts = uri.rstrip("/").split("/")
    for part in reversed(parts):
        if "_" in part and any(part.startswith(s) for s in
                               ("Buffalo", "Cow", "Goat", "Sheep",
                                "buffalo", "cow", "goat", "sheep")):
            return part.split("_")[0].capitalize()
    return "unknown"


def _extract_sample_group_from_uri(uri: str) -> str:
    """Extract sample group folder from S3 object URI path.

    LeaData URIs follow: .../raw/{Species}_{SampleCode}/{image_id}.jpg
    Example: .../raw/Sheep_SBTS25/abc.jpg → "Sheep_SBTS25"
    """
    parts = uri.rstrip("/").split("/")
    # The parent directory of the image file is the sample group
    if len(parts) >= 2:
        return parts[-2]
    return "unknown"


def extract_label(record: dict, strategy: str) -> str:
    """Extract a label from a dataset record using the specified strategy."""
    if strategy == "authenticity_status":
        return str(record.get("authenticity_status", "unknown"))
    if strategy == "external_item_id":
        return str(record.get("reference_item_id", "unknown"))
    if strategy == "region_code":
        return str(record.get("region_code", "unknown"))
    if strategy == "species":
        uri = record.get("object_uri", "")
        return _extract_species_from_uri(uri)
    if strategy == "sample_group":
        uri = record.get("object_uri", "")
        return _extract_sample_group_from_uri(uri)
    # Fallback: use reference_item_id
    return str(record.get("reference_item_id", "unknown"))


def build_label_map(records: list[dict], strategy: str) -> tuple[list[str], dict[str, int]]:
    """Build string labels and label-to-int mapping.

    Returns (labels_list, label_to_idx).
    """
    labels = [extract_label(r, strategy) for r in records]
    unique = sorted(set(labels))
    label_to_idx = {lbl: i for i, lbl in enumerate(unique)}
    return labels, label_to_idx


def check_leakage(records: list[dict], field: str = "reference_item_id") -> list[str]:
    """Check for train/test leakage on the specified field.

    Returns list of field values that appear in multiple splits.
    """
    by_split: dict[str, set[str]] = {}
    for r in records:
        split = r.get("split", "unknown")
        val = str(r.get(field, ""))
        by_split.setdefault(split, set()).add(val)

    splits = list(by_split.keys())
    leaked = set()
    for i, s1 in enumerate(splits):
        for s2 in splits[i + 1:]:
            overlap = by_split[s1] & by_split[s2]
            leaked.update(overlap)
    return sorted(leaked)


# ---------------------------------------------------------------------------
# Dataset for experiment
# ---------------------------------------------------------------------------

class ExperimentImageDataset(Dataset):
    """Simple dataset loading images from S3 with configurable labels."""

    def __init__(
        self,
        records: list[dict],
        labels: list[str],
        label_to_idx: dict[str, int],
        transform: transforms.Compose | None = None,
    ):
        self.records = records
        self.labels = labels
        self.label_to_idx = label_to_idx
        self.int_labels = [label_to_idx[lbl] for lbl in labels]
        self.transform = transform

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int, dict]:
        rec = self.records[idx]
        label_int = self.int_labels[idx]

        img_bytes = load_image_bytes(rec["object_uri"])
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        if self.transform:
            img = self.transform(img)

        return img, label_int, {"id": str(rec["reference_image_id"])}


class ContrastivePairSampler(Dataset):
    """Generate contrastive pairs from a base dataset."""

    def __init__(self, base: ExperimentImageDataset, pairs_per_epoch: int = 200, seed: int = 42):
        self.base = base
        self.rng = random.Random(seed)

        # Group indices by class
        self.class_indices: dict[int, list[int]] = {}
        for i, lbl in enumerate(base.int_labels):
            self.class_indices.setdefault(lbl, []).append(i)

        # Need at least 2 classes for contrastive learning
        self.classes_with_data = [c for c, idxs in self.class_indices.items() if len(idxs) >= 1]
        self.multi_sample_classes = [c for c, idxs in self.class_indices.items() if len(idxs) >= 2]

        self.pairs: list[tuple[int, int, int]] = []
        self._generate_pairs(pairs_per_epoch)

    def _generate_pairs(self, n: int) -> None:
        for _ in range(n):
            # Positive pair: same class (if any class has 2+ samples)
            if self.multi_sample_classes and self.rng.random() < 0.5:
                c = self.rng.choice(self.multi_sample_classes)
                i, j = self.rng.sample(self.class_indices[c], 2)
                self.pairs.append((i, j, 1))
            # Negative pair: different classes
            if len(self.classes_with_data) >= 2:
                c1, c2 = self.rng.sample(self.classes_with_data, 2)
                i = self.rng.choice(self.class_indices[c1])
                j = self.rng.choice(self.class_indices[c2])
                self.pairs.append((i, j, 0))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        i, j, label = self.pairs[idx]
        img1, _, _ = self.base[i]
        img2, _, _ = self.base[j]
        return img1, img2, torch.tensor(label, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader | None,
    config: LMExperimentConfig,
    device: torch.device,
    loss_mode: str = "pair",
) -> dict:
    """Train model and return metrics.

    loss_mode controls how the dataloader is consumed:
    - "pair": loader yields (img1, img2, label) for contrastive/triplet
    - "batch": loader yields (imgs, labels, meta) for supcon/batch-hard
    """
    from experiments.losses import create_loss

    criterion = create_loss(config)

    # Optimizer
    opt_cfg = config.optimizer if isinstance(config.optimizer, dict) else {"name": "adam"}
    opt_name = opt_cfg.get("name", "adam")
    opt_lr = opt_cfg.get("learning_rate", config.learning_rate)
    opt_wd = opt_cfg.get("weight_decay", config.weight_decay)
    trainable = [p for p in model.parameters() if p.requires_grad]
    if opt_name == "adamw":
        optimizer = torch.optim.AdamW(trainable, lr=opt_lr, weight_decay=opt_wd)
    else:
        optimizer = torch.optim.Adam(trainable, lr=opt_lr, weight_decay=opt_wd)

    # Scheduler
    sched_cfg = config.scheduler if isinstance(config.scheduler, dict) else {"name": "none"}
    sched_name = sched_cfg.get("name", "none")
    lr_scheduler = None
    if sched_name == "cosine":
        min_lr = sched_cfg.get("min_lr", 1e-6)
        lr_scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=config.epochs, eta_min=min_lr,
        )

    model = model.to(device)
    train_losses = []
    val_losses = []
    lr_history = []

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        if loss_mode == "batch":
            for imgs, labels, _meta in train_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                optimizer.zero_grad()
                embs = model(imgs)
                loss = criterion(embs, labels)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
                n_batches += 1
        else:
            for img1, img2, labels in train_loader:
                img1, img2, labels = img1.to(device), img2.to(device), labels.to(device)
                optimizer.zero_grad()
                emb1 = model(img1)
                emb2 = model(img2)
                loss = criterion(emb1, emb2, labels)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
                n_batches += 1

        avg_train = epoch_loss / max(n_batches, 1)
        train_losses.append(avg_train)

        # Validation
        avg_val = 0.0
        if val_loader:
            model.eval()
            val_loss = 0.0
            n_val = 0
            with torch.no_grad():
                if loss_mode == "batch":
                    for imgs, labels, _meta in val_loader:
                        imgs, labels = imgs.to(device), labels.to(device)
                        embs = model(imgs)
                        loss = criterion(embs, labels)
                        val_loss += loss.item()
                        n_val += 1
                else:
                    for img1, img2, labels in val_loader:
                        img1, img2, labels = img1.to(device), img2.to(device), labels.to(device)
                        emb1 = model(img1)
                        emb2 = model(img2)
                        loss = criterion(emb1, emb2, labels)
                        val_loss += loss.item()
                        n_val += 1
            avg_val = val_loss / max(n_val, 1)
            val_losses.append(avg_val)

        current_lr = optimizer.param_groups[0]["lr"]
        lr_history.append(current_lr)
        if lr_scheduler:
            lr_scheduler.step()

        print(f"  Epoch {epoch + 1}/{config.epochs}: "
              f"train_loss={avg_train:.4f}"
              f"{f', val_loss={avg_val:.4f}' if val_loader else ''}"
              f", lr={current_lr:.6f}")

    best_val_idx = int(min(range(len(val_losses)), key=lambda i: val_losses[i])) if val_losses else -1
    return {
        "train_losses": train_losses,
        "val_losses": val_losses,
        "lr_history": lr_history,
        "final_train_loss": train_losses[-1] if train_losses else None,
        "final_val_loss": val_losses[-1] if val_losses else None,
        "best_val_epoch": best_val_idx + 1 if best_val_idx >= 0 else None,
        "best_val_loss": val_losses[best_val_idx] if best_val_idx >= 0 else None,
    }


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_embeddings(
    model: nn.Module,
    dataset: ExperimentImageDataset,
    device: torch.device,
    batch_size: int = 32,
) -> dict:
    """Compute embeddings and metrics on a dataset split."""
    model.eval()
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    all_embeddings = []
    all_labels = []

    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs = imgs.to(device)
            embs = model(imgs)
            all_embeddings.extend(embs.cpu().numpy().tolist())
            all_labels.extend([dataset.labels[i] for i in range(
                len(all_labels), len(all_labels) + len(labels))])

    # Rebuild labels from dataset order
    all_labels = dataset.labels[:len(all_embeddings)]
    regions = [r.get("region_code", "") for r in dataset.records[:len(all_embeddings)]]

    metrics = compute_metrics(all_embeddings, all_labels, regions)
    return {
        "embedding_count": len(all_embeddings),
        "embedding_dimension": len(all_embeddings[0]) if all_embeddings else 0,
        "metrics": metrics,
    }
