"""Loss functions for metric learning experiments.

Provides contrastive, supervised contrastive, triplet, and batch-hard triplet
losses for embedding experiments.

Results are diagnostic only — they do not prove authentication accuracy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch
import torch.nn as nn
import torch.nn.functional as F  # noqa: N812

if TYPE_CHECKING:
    from experiments.learned_metric_experiment import LMExperimentConfig


class ContrastiveLoss(nn.Module):
    """Pairwise contrastive loss.

    label=1: similar pair (pull together)
    label=0: dissimilar pair (push apart)
    """

    def __init__(self, margin: float = 1.0):
        super().__init__()
        self.margin = margin

    def forward(self, emb1: torch.Tensor, emb2: torch.Tensor, label: torch.Tensor) -> torch.Tensor:
        distance = F.pairwise_distance(emb1, emb2)
        loss_pos = label * distance.pow(2)
        loss_neg = (1 - label) * F.relu(self.margin - distance).pow(2)
        return (loss_pos + loss_neg).mean()


class SupervisedContrastiveLoss(nn.Module):
    """Supervised contrastive loss (SupCon).

    For each anchor, all same-class samples in the batch are positives and all
    different-class samples are negatives. Operates on L2-normalized embeddings.

    Reference: Khosla et al., "Supervised Contrastive Learning", NeurIPS 2020.
    """

    def __init__(self, temperature: float = 0.07):
        super().__init__()
        self.temperature = temperature

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embeddings: (N, D) L2-normalized embeddings.
            labels: (N,) integer class labels.

        Returns:
            Scalar loss.
        """
        device = embeddings.device
        n = embeddings.shape[0]
        if n < 2:
            return torch.tensor(0.0, device=device, requires_grad=True)

        # Similarity matrix
        sim = torch.matmul(embeddings, embeddings.T) / self.temperature  # (N, N)

        # Mask: same class = 1, different class = 0, self = 0
        labels_col = labels.unsqueeze(0)  # (1, N)
        labels_row = labels.unsqueeze(1)  # (N, 1)
        pos_mask = (labels_row == labels_col).float()
        pos_mask.fill_diagonal_(0.0)

        # Check if any anchor has at least one positive
        pos_counts = pos_mask.sum(dim=1)
        has_positives = pos_counts > 0
        if not has_positives.any():
            return torch.tensor(0.0, device=device, requires_grad=True)

        # Log-sum-exp stability: subtract max per row
        self_mask = torch.ones(n, n, device=device)
        self_mask.fill_diagonal_(0.0)
        logits_max, _ = (sim * self_mask).max(dim=1, keepdim=True)
        logits = sim - logits_max.detach()

        # Denominator: sum of exp over all non-self
        exp_logits = torch.exp(logits) * self_mask
        log_denom = torch.log(exp_logits.sum(dim=1, keepdim=True) + 1e-12)

        # Log probability of positives
        log_prob = logits - log_denom  # (N, N)
        mean_log_prob_pos = (pos_mask * log_prob).sum(dim=1) / pos_counts.clamp(min=1)

        # Only average over anchors that have positives
        loss = -(mean_log_prob_pos * has_positives.float()).sum() / has_positives.float().sum().clamp(min=1)
        return loss


class TripletLoss(nn.Module):
    """Standard triplet margin loss.

    loss = max(0, d(anchor, positive) - d(anchor, negative) + margin)
    """

    def __init__(self, margin: float = 0.2):
        super().__init__()
        self.margin = margin

    def forward(
        self, anchor: torch.Tensor, positive: torch.Tensor, negative: torch.Tensor,
    ) -> torch.Tensor:
        d_pos = F.pairwise_distance(anchor, positive)
        d_neg = F.pairwise_distance(anchor, negative)
        loss = F.relu(d_pos - d_neg + self.margin)
        return loss.mean()


class BatchHardTripletLoss(nn.Module):
    """Batch-hard triplet loss.

    For each anchor, selects the hardest positive (farthest same-class) and
    hardest negative (closest different-class) within the batch.
    """

    def __init__(self, margin: float = 0.2):
        super().__init__()
        self.margin = margin

    def forward(self, embeddings: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embeddings: (N, D) embeddings.
            labels: (N,) integer class labels.
        """
        n = embeddings.shape[0]
        device = embeddings.device
        if n < 2:
            return torch.tensor(0.0, device=device, requires_grad=True)

        # Pairwise distance matrix
        dist = torch.cdist(embeddings, embeddings, p=2)  # (N, N)

        labels_row = labels.unsqueeze(1)
        labels_col = labels.unsqueeze(0)
        same_mask = (labels_row == labels_col)
        diff_mask = ~same_mask

        # Hardest positive: max distance among same-class (excluding self)
        same_no_self = same_mask.clone()
        same_no_self.fill_diagonal_(False)
        # Set non-same to -inf for max
        hard_pos_dist = (dist * same_no_self.float()).max(dim=1).values

        # Hardest negative: min distance among different-class
        # Set same-class to large value for min
        big = dist.max().item() + 1.0
        neg_dist = dist + same_mask.float() * big
        hard_neg_dist = neg_dist.min(dim=1).values

        # Only compute loss for anchors that have both pos and neg
        has_pos = same_no_self.any(dim=1)
        has_neg = diff_mask.any(dim=1)
        valid = has_pos & has_neg

        if not valid.any():
            return torch.tensor(0.0, device=device, requires_grad=True)

        triplet_loss = F.relu(hard_pos_dist[valid] - hard_neg_dist[valid] + self.margin)
        return triplet_loss.mean()


# ---------------------------------------------------------------------------
# Triplet mining helpers
# ---------------------------------------------------------------------------

def mine_triplets_random(
    labels: list[int],
    n_triplets: int = 200,
    seed: int = 42,
) -> list[tuple[int, int, int]]:
    """Generate random (anchor, positive, negative) index triplets."""
    import random as _random
    rng = _random.Random(seed)

    by_class: dict[int, list[int]] = {}
    for i, lbl in enumerate(labels):
        by_class.setdefault(lbl, []).append(i)

    multi = [c for c, idxs in by_class.items() if len(idxs) >= 2]
    all_classes = list(by_class.keys())
    if len(multi) < 1 or len(all_classes) < 2:
        return []

    triplets = []
    for _ in range(n_triplets):
        pos_class = rng.choice(multi)
        neg_classes = [c for c in all_classes if c != pos_class]
        if not neg_classes:
            continue
        neg_class = rng.choice(neg_classes)
        a, p = rng.sample(by_class[pos_class], 2)
        n = rng.choice(by_class[neg_class])
        triplets.append((a, p, n))

    return triplets


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

LOSS_REGISTRY: dict[str, type] = {
    "contrastive": ContrastiveLoss,
    "supervised_contrastive": SupervisedContrastiveLoss,
    "triplet": TripletLoss,
    "batch_hard_triplet": BatchHardTripletLoss,
}

# Losses that operate on (embeddings, labels) batches rather than pairs/triplets
BATCH_LOSSES = {"supervised_contrastive", "batch_hard_triplet"}
# Losses that operate on (anchor, positive, negative) triplets
TRIPLET_LOSSES = {"triplet"}
# Losses that operate on (emb1, emb2, label) pairs
PAIR_LOSSES = {"contrastive"}


def get_loss_name(config: LMExperimentConfig) -> str:
    """Extract loss name from config, supporting both flat and dict forms."""
    loss = config.loss
    if isinstance(loss, dict):
        return loss.get("name", "contrastive")
    return str(loss)


def get_loss_params(config: LMExperimentConfig) -> dict:
    """Extract loss parameters from config."""
    loss = config.loss
    if isinstance(loss, dict):
        params = dict(loss)
        params.pop("name", None)
        return params
    return {"margin": config.margin}


def create_loss(config: LMExperimentConfig) -> nn.Module:
    """Create a loss function from experiment config."""
    name = get_loss_name(config)
    params = get_loss_params(config)

    if name not in LOSS_REGISTRY:
        raise ValueError(f"Unknown loss: {name}. Available: {list(LOSS_REGISTRY.keys())}")

    cls = LOSS_REGISTRY[name]
    # Filter params to match constructor
    import inspect
    sig = inspect.signature(cls.__init__)
    valid_params = {k: v for k, v in params.items() if k in sig.parameters}
    return cls(**valid_params)
