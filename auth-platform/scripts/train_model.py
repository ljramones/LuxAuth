#!/usr/bin/env python3
"""Train a metric-learning model locally.

Usage: python scripts/train_model.py [--epochs 10] [--lr 0.001]
"""

import argparse
import sys
from pathlib import Path

# Add ml package to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from metric_learning.config import TrainingConfig
from metric_learning.train import train
from metric_learning.export import export_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--dataset", default="synthetic_lv_monogram_v0.1.0")
    args = parser.parse_args()

    config = TrainingConfig(
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
        dataset_version=args.dataset,
    )

    print("=" * 60)
    print("  Metric Learning Training")
    print("=" * 60)
    print(f"  Model: {config.model_name}_{config.model_version}")
    print(f"  Dataset: {config.dataset_version}")
    print(f"  Epochs: {config.epochs}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  Learning rate: {config.learning_rate}")
    print(f"  Loss: {config.loss_type}")
    print()

    result = train(config)
    print(f"\nTraining complete. Run ID: {result['run_id']}")
    print(f"  Final train loss: {result['metrics']['final_train_loss']:.4f}")
    print(f"  Final val loss: {result['metrics']['final_val_loss']:.4f}")

    print("\nExporting model artifact...")
    artifact_uri = export_model(result["model"], result, config)
    print(f"\nModel registered: {config.model_name}_{config.model_version}")
    print(f"Artifact: {artifact_uri}")
    print("\nNext steps:")
    print("  make reembed-reference-data MODEL=learned_metric_v0.1.0")
    print("  make run-evaluation MODEL=learned_metric_v0.1.0")


if __name__ == "__main__":
    main()
