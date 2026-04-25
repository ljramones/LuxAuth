"""Dataset loader from governed reference database."""

import io
import random
from typing import Any

import boto3
import psycopg2
import torch
from PIL import Image
from torch.utils.data import Dataset

from metric_learning.config import TrainingConfig
from metric_learning.transforms import get_eval_transform, get_train_transform


class ReferenceImageDataset(Dataset):
    """Loads reference images from S3 via database metadata."""

    def __init__(self, config: TrainingConfig, split: str = "train", is_eval: bool = False):
        self.config = config
        self.split = split
        self.transform = get_eval_transform(config.input_size) if is_eval else get_train_transform(config.input_size)

        self.s3 = boto3.client(
            "s3",
            endpoint_url=config.s3_endpoint,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        # Load metadata from DB
        conn = psycopg2.connect(config.db_dsn)
        cur = conn.cursor()

        split_filter = "AND dm.split = %s" if split != "all" else ""
        params: list[Any] = [config.dataset_version]
        if split != "all":
            params.append(split)

        cur.execute(f"""
            SELECT ri.id, ri.object_uri, ri.region_code,
                   rit.authenticity_status, rit.brand, rit.category, rit.material
            FROM reference_dataset_members dm
            JOIN reference_images ri ON ri.id = dm.reference_image_id
            JOIN reference_items rit ON rit.id = ri.reference_item_id
            JOIN reference_dataset_versions rdv ON rdv.id = dm.dataset_version_id
            WHERE rdv.dataset_version = %s
              AND rdv.status != 'retired'
              {split_filter}
              AND dm.include_in_training = TRUE
            ORDER BY ri.id
        """, params)

        cols = [desc[0] for desc in cur.description]
        self.items = [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
        cur.close()
        conn.close()

        # Build label map: CONFIRMED_AUTHENTIC=1, CONFIRMED_COUNTERFEIT=0
        self.labels = [
            1 if item["authenticity_status"] == "CONFIRMED_AUTHENTIC" else 0
            for item in self.items
        ]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int, dict]:
        item = self.items[idx]
        label = self.labels[idx]

        # Download image from S3
        uri = item["object_uri"]
        uri_parts = uri.replace("s3://", "").split("/", 1)
        bucket, key = uri_parts[0], uri_parts[1]

        response = self.s3.get_object(Bucket=bucket, Key=key)
        img_bytes = response["Body"].read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        if self.transform:
            img = self.transform(img)

        return img, label, {"id": str(item["id"]), "region_code": item["region_code"]}


class ContrastivePairDataset(Dataset):
    """Generates contrastive pairs from a base dataset."""

    def __init__(self, base_dataset: ReferenceImageDataset, pairs_per_epoch: int = 100, seed: int = 42):
        self.base = base_dataset
        self.rng = random.Random(seed)

        # Split indices by label
        self.pos_indices = [i for i, label in enumerate(base_dataset.labels) if label == 1]
        self.neg_indices = [i for i, label in enumerate(base_dataset.labels) if label == 0]

        # Generate pairs
        self.pairs: list[tuple[int, int, int]] = []
        for _ in range(pairs_per_epoch):
            if self.rng.random() < 0.5 and len(self.pos_indices) >= 2:
                # Positive pair (same class)
                i, j = self.rng.sample(self.pos_indices, 2)
                self.pairs.append((i, j, 1))
            elif len(self.neg_indices) >= 2:
                # Positive pair from negative class
                i, j = self.rng.sample(self.neg_indices, 2)
                self.pairs.append((i, j, 1))
            else:
                continue

            # Negative pair (different class)
            if self.pos_indices and self.neg_indices:
                i = self.rng.choice(self.pos_indices)
                j = self.rng.choice(self.neg_indices)
                self.pairs.append((i, j, 0))

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        i, j, label = self.pairs[idx]
        img1, _, _ = self.base[i]
        img2, _, _ = self.base[j]
        return img1, img2, torch.tensor(label, dtype=torch.float32)
