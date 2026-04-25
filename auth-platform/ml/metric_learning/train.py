"""Training loop for metric learning."""

import json
import uuid
from datetime import datetime, timezone

import psycopg2
import torch
from torch.utils.data import DataLoader

from metric_learning.config import TrainingConfig
from metric_learning.dataset import ReferenceImageDataset, ContrastivePairDataset
from metric_learning.model import EmbeddingModel
from metric_learning.losses import ContrastiveLoss


def train(config: TrainingConfig) -> dict:
    """Run training and return metrics."""
    torch.manual_seed(config.seed)

    print(f"Loading dataset: {config.dataset_version}, split=train")
    base_train = ReferenceImageDataset(config, split="train")
    print(f"  Train images: {len(base_train)}")

    if len(base_train) < 4:
        raise ValueError(f"Not enough training images: {len(base_train)}")

    pairs_per_epoch = max(50, len(base_train) * 4)
    pair_dataset = ContrastivePairDataset(base_train, pairs_per_epoch=pairs_per_epoch, seed=config.seed)
    loader = DataLoader(pair_dataset, batch_size=config.batch_size, shuffle=True)

    # Load validation set
    base_val = ReferenceImageDataset(config, split="validation", is_eval=True)
    val_pairs = ContrastivePairDataset(base_val, pairs_per_epoch=max(20, len(base_val) * 2), seed=config.seed + 1)
    val_loader = DataLoader(val_pairs, batch_size=config.batch_size)

    model = EmbeddingModel(embedding_dim=config.embedding_dim)
    criterion = ContrastiveLoss(margin=config.margin)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )

    # Record training run in DB
    conn = psycopg2.connect(config.db_dsn)
    conn.autocommit = True
    cur = conn.cursor()

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    cur.execute("""
        INSERT INTO training_runs (id, model_name, model_version, dataset_version,
            embedding_dimension, loss_type, status, started_at, config_json)
        VALUES (%s, %s, %s, %s, %s, %s, 'RUNNING', %s, %s)
    """, (run_id, config.model_name, config.model_version, config.dataset_version,
          config.embedding_dim, config.loss_type, started_at,
          json.dumps({
              "epochs": config.epochs, "batch_size": config.batch_size,
              "lr": config.learning_rate, "margin": config.margin, "seed": config.seed,
              "input_size": config.input_size,
          })))

    # Audit
    cur.execute("""
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'TRAINING_RUN_STARTED', %s, %s)
    """, (str(uuid.uuid4()), json.dumps({"training_run_id": run_id}), started_at))

    best_val_loss = float("inf")
    train_losses = []
    val_losses = []

    print(f"\nTraining {config.model_name}_{config.model_version}")
    print(f"  Epochs: {config.epochs}, Batch: {config.batch_size}, LR: {config.learning_rate}")

    for epoch in range(config.epochs):
        model.train()
        epoch_loss = 0.0
        n_batches = 0

        for img1, img2, labels in loader:
            optimizer.zero_grad()
            emb1 = model(img1)
            emb2 = model(img2)
            loss = criterion(emb1, emb2, labels)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        avg_train_loss = epoch_loss / max(n_batches, 1)
        train_losses.append(avg_train_loss)

        # Validation
        model.eval()
        val_loss = 0.0
        n_val = 0
        with torch.no_grad():
            for img1, img2, labels in val_loader:
                emb1 = model(img1)
                emb2 = model(img2)
                loss = criterion(emb1, emb2, labels)
                val_loss += loss.item()
                n_val += 1
        avg_val_loss = val_loss / max(n_val, 1)
        val_losses.append(avg_val_loss)

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss

        print(f"  Epoch {epoch+1}/{config.epochs}: train_loss={avg_train_loss:.4f}, val_loss={avg_val_loss:.4f}")

    completed_at = datetime.now(timezone.utc)
    metrics = {
        "final_train_loss": train_losses[-1] if train_losses else None,
        "final_val_loss": val_losses[-1] if val_losses else None,
        "best_val_loss": best_val_loss,
        "train_losses": train_losses,
        "val_losses": val_losses,
    }

    # Update training run
    cur.execute("""
        UPDATE training_runs SET status = 'COMPLETED', completed_at = %s, metrics_json = %s
        WHERE id = %s
    """, (completed_at, json.dumps(metrics), run_id))

    cur.execute("""
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'TRAINING_RUN_COMPLETED', %s, %s)
    """, (str(uuid.uuid4()), json.dumps({"training_run_id": run_id, "metrics": metrics}), completed_at))

    cur.close()
    conn.close()

    return {
        "model": model,
        "run_id": run_id,
        "metrics": metrics,
        "config": config,
        "started_at": started_at,
        "completed_at": completed_at,
    }
