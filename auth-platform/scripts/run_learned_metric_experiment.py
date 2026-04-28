#!/usr/bin/env python3
"""Run learned metric model experiment.

Trains a configurable learned metric model on a governed dataset and compares
embedding quality against texture_baseline_v0.2.0.

Results are diagnostic only — they do not prove authentication accuracy.

Usage:
  python scripts/run_learned_metric_experiment.py --config ../experiments/configs/learned_metric_v0.2.0_leadata.yaml
  python scripts/run_learned_metric_experiment.py --config ../experiments/configs/learned_metric_v0.2.0_leadata.yaml --epochs 2 --limit 100
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent.parent / "ml"))

from experiments.dataset_loader import load_dataset_records
from experiments.learned_metric_experiment import (
    ContrastivePairSampler,
    ExperimentImageDataset,
    LMExperimentConfig,
    build_eval_transform,
    build_label_map,
    build_train_transform,
    check_leakage,
    create_model,
    evaluate_embeddings,
    train_model,
    validate_config,
)


def main():
    parser = argparse.ArgumentParser(description="Run learned metric experiment")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--dataset", default=None, help="Override dataset_version")
    parser.add_argument("--model-version", default=None, help="Override model_version")
    parser.add_argument("--epochs", type=int, default=None, help="Override epochs")
    parser.add_argument("--limit", type=int, default=None, help="Limit images per split")
    parser.add_argument("--dry-run", action="store_true", help="Load data and validate only")
    parser.add_argument("--device", default="auto", help="Device: auto/cpu/mps/cuda")
    parser.add_argument("--allow-random-init", action="store_true", help="Allow random init if pretrained unavailable")
    parser.add_argument("--register-model", action="store_true", help="Register model in DB/S3 (default: false)")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--notes", default="", help="Free-form notes")
    args = parser.parse_args()

    # Load config
    config = LMExperimentConfig.from_yaml(args.config)
    if args.dataset:
        config.dataset_version = args.dataset
    if args.model_version:
        config.model_version = args.model_version
    if args.epochs:
        config.epochs = args.epochs

    output_dir = (
        Path(args.output_dir) if args.output_dir
        else Path(__file__).parent.parent.parent / "experiments" / "outputs" / "learned-metric"
    )

    # Validate
    warnings = validate_config(config)
    for w in warnings:
        print(f"WARNING: {w}")

    if not config.dataset_version:
        print("ERROR: No dataset_version in config or --dataset argument")
        sys.exit(1)

    # Device
    if args.device == "auto":
        if torch.cuda.is_available():
            device = torch.device("cuda")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = torch.device("mps")
        else:
            device = torch.device("cpu")
    else:
        device = torch.device(args.device)

    print(f"Config:     {args.config}")
    print(f"Dataset:    {config.dataset_version}")
    print(f"Model:      {config.model_name}_{config.model_version}")
    print(f"Backbone:   {config.backbone} (pretrained={config.pretrained}, freeze={config.freeze_backbone})")
    print(f"Emb dim:    {config.embedding_dim}")
    from experiments.losses import BATCH_LOSSES, get_loss_name
    loss_name = get_loss_name(config)
    print(f"Loss:       {loss_name} (config.loss={config.loss})")
    print(f"Epochs:     {config.epochs}")
    print(f"Batch:      {config.batch_size}")
    print(f"LR:         {config.learning_rate}")
    print(f"Labels:     {config.label_strategy}")
    print(f"Device:     {device}")
    print(f"Output:     {output_dir}")

    torch.manual_seed(config.seed)

    # Load dataset records
    print("\nLoading dataset records...")
    train_records = load_dataset_records(config.dataset_version, split="train", limit=args.limit)
    val_records = load_dataset_records(config.dataset_version, split="validation", limit=args.limit)
    test_records = load_dataset_records(config.dataset_version, split="test", limit=args.limit)

    print(f"  Train:      {len(train_records)} records")
    print(f"  Validation: {len(val_records)} records")
    print(f"  Test:       {len(test_records)} records")

    if not train_records:
        print("ERROR: No training records found.")
        sys.exit(1)

    # Build labels
    all_records = train_records + val_records + test_records
    all_labels, label_to_idx = build_label_map(all_records, config.label_strategy)
    n_classes = len(label_to_idx)
    print(f"  Classes:    {n_classes}")
    print(f"  Label strategy: {config.label_strategy}")

    train_labels = all_labels[:len(train_records)]
    val_labels = all_labels[len(train_records):len(train_records) + len(val_records)]
    test_labels = all_labels[len(train_records) + len(val_records):]

    # Label distribution
    train_class_counts = {}
    for lbl in train_labels:
        train_class_counts[lbl] = train_class_counts.get(lbl, 0) + 1
    multi_sample_classes = sum(1 for c in train_class_counts.values() if c >= 2)
    print(f"  Train classes with 2+ images: {multi_sample_classes}/{len(train_class_counts)}")

    if multi_sample_classes < 2:
        print("WARNING: Fewer than 2 classes with 2+ images in training set.")
        print("  Contrastive pair generation will be limited.")
        print("  This dataset may not support meaningful supervised metric learning.")

    # Leakage check
    leak_field = config.split_policy.get("leakage_check_field", "reference_item_id")
    leaked = check_leakage(all_records, leak_field)
    if leaked:
        print(f"WARNING: Potential leakage on '{leak_field}': {len(leaked)} values in multiple splits")
    else:
        print(f"  No leakage detected on '{leak_field}'")

    if args.dry_run:
        print("\nDry run complete. No training performed.")
        return

    # Build datasets
    print("\nBuilding datasets...")
    train_transform = build_train_transform(config)
    eval_transform = build_eval_transform(config)

    train_ds = ExperimentImageDataset(train_records, train_labels, label_to_idx, train_transform)
    val_ds = ExperimentImageDataset(val_records, val_labels, label_to_idx, eval_transform) if val_records else None
    test_ds = ExperimentImageDataset(test_records, test_labels, label_to_idx, eval_transform) if test_records else None

    # Build dataloader based on loss type
    use_batch_mode = loss_name in BATCH_LOSSES
    if use_batch_mode:
        print(f"  Using batch mode for {loss_name}")
        train_loader = torch.utils.data.DataLoader(
            train_ds, batch_size=config.batch_size, shuffle=True, drop_last=True,
        )
        val_loader = torch.utils.data.DataLoader(
            val_ds, batch_size=config.batch_size, drop_last=True,
        ) if val_ds and len(val_ds) >= 4 else None
    else:
        pairs_per_epoch = max(100, len(train_records) * 3)
        train_pairs = ContrastivePairSampler(train_ds, pairs_per_epoch=pairs_per_epoch, seed=config.seed)
        print(f"  Train pairs: {len(train_pairs)}")

        if len(train_pairs) == 0:
            print("ERROR: Could not generate any contrastive pairs.")
            print("  Check label strategy and class distribution.")
            sys.exit(1)

        val_pairs = None
        if val_ds and len(val_ds) >= 4:
            val_pairs = ContrastivePairSampler(val_ds, pairs_per_epoch=max(50, len(val_records) * 2), seed=config.seed + 1)

        train_loader = torch.utils.data.DataLoader(train_pairs, batch_size=config.batch_size, shuffle=True)
        val_loader = torch.utils.data.DataLoader(val_pairs, batch_size=config.batch_size) if val_pairs else None

    # Create model
    print("\nCreating model...")
    model = create_model(
        backbone=config.backbone,
        pretrained=config.pretrained,
        embedding_dim=config.embedding_dim,
        allow_random_init=args.allow_random_init,
        freeze_backbone=config.freeze_backbone,
        projection_head=config.projection_head,
    )
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = total_params - trainable_params
    print(f"  Total params:     {total_params:,}")
    print(f"  Trainable params: {trainable_params:,}")
    if frozen_params > 0:
        print(f"  Frozen params:    {frozen_params:,}")

    # Train
    print("\nTraining...")
    t0 = time.monotonic()
    loss_mode = "batch" if use_batch_mode else "pair"
    training_metrics = train_model(model, train_loader, val_loader, config, device, loss_mode)
    train_time = time.monotonic() - t0
    print(f"  Training time: {train_time:.1f}s")

    # Evaluate on test set
    eval_results = {}
    if test_ds and len(test_ds) >= 2:
        print("\nEvaluating on test set...")
        model = model.to(torch.device("cpu"))
        eval_results = evaluate_embeddings(model, test_ds, torch.device("cpu"), config.batch_size)
        m = eval_results["metrics"]
        print(f"  Embeddings: {eval_results['embedding_count']}")
        print(f"  Dimension: {eval_results['embedding_dimension']}")
        print(f"  Cluster sep: {m.get('cluster_separation', 'N/A')}")
        print(f"  NN agree:    {m.get('nn_agreement_rate', 'N/A')}")
        print(f"  Recall@1:    {m.get('recall_at_1', 'N/A')}")

    # Save outputs
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC)
    ds_tag = config.dataset_version.replace(".", "_")
    prefix = f"{ds_tag}__learned_metric_{config.model_version.replace('.', '_')}__{loss_name}"

    # Training metrics
    training_path = output_dir / f"{prefix}__training_metrics.json"
    training_metrics["training_time_seconds"] = round(train_time, 2)
    training_path.write_text(json.dumps(training_metrics, indent=2))

    # Evaluation metrics
    if eval_results:
        eval_path = output_dir / f"{prefix}__evaluation_metrics.json"
        eval_path.write_text(json.dumps(eval_results, indent=2, default=str))

    # Experiment record
    record = {
        "experiment_type": "learned_metric",
        "model_version": f"{config.model_name}_{config.model_version}",
        "dataset_version": config.dataset_version,
        "backbone": config.backbone,
        "pretrained": config.pretrained,
        "freeze_backbone": config.freeze_backbone,
        "embedding_dim": config.embedding_dim,
        "total_params": total_params,
        "trainable_params": trainable_params,
        "frozen_params": frozen_params,
        "loss": loss_name,
        "loss_config": config.loss if isinstance(config.loss, dict) else {"name": config.loss},
        "augmentation_profile": config.augmentation_profile or "custom",
        "optimizer": config.optimizer,
        "scheduler": config.scheduler,
        "projection_head": config.projection_head,
        "epochs": config.epochs,
        "batch_size": config.batch_size,
        "learning_rate": config.learning_rate,
        "label_strategy": config.label_strategy,
        "n_classes": n_classes,
        "train_count": len(train_records),
        "val_count": len(val_records),
        "test_count": len(test_records),
        "device": str(device),
        "training_time_seconds": round(train_time, 2),
        "training_metrics": training_metrics,
        "evaluation_metrics": eval_results.get("metrics") if eval_results else None,
        "timestamp": now.isoformat(),
        "notes": args.notes or config.notes,
    }
    record_path = output_dir / f"{prefix}__experiment_record.json"
    record_path.write_text(json.dumps(record, indent=2, default=str))

    # Model artifact (local only unless --register-model)
    model_path = output_dir / f"{prefix}__model.pt"
    torch.save(model.state_dict(), model_path)

    # Report
    report_lines = [
        "# Learned Metric Experiment Report",
        "",
        f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "> Results are diagnostic only. They do not prove authentication accuracy.",
        "",
        "## Configuration",
        "",
        f"- **Model:** `{config.model_name}_{config.model_version}`",
        f"- **Dataset:** `{config.dataset_version}`",
        f"- **Backbone:** {config.backbone} (pretrained={config.pretrained})",
        f"- **Embedding dim:** {config.embedding_dim}",
        f"- **Loss:** {config.loss} (margin={config.margin})",
        f"- **Epochs:** {config.epochs}",
        f"- **Classes:** {n_classes}",
        f"- **Train/Val/Test:** {len(train_records)}/{len(val_records)}/{len(test_records)}",
        f"- **Device:** {device}",
        f"- **Training time:** {train_time:.1f}s",
        "",
        "## Training",
        "",
        f"- Final train loss: {training_metrics.get('final_train_loss', 'N/A')}",
        f"- Final val loss: {training_metrics.get('final_val_loss', 'N/A')}",
        "",
    ]
    if eval_results:
        m = eval_results["metrics"]
        report_lines.extend([
            "## Test Evaluation",
            "",
            f"- Embeddings: {eval_results['embedding_count']}",
            f"- Cluster separation: {m.get('cluster_separation', 'N/A')}",
            f"- NN agreement: {m.get('nn_agreement_rate', 'N/A')}",
            f"- Recall@1: {m.get('recall_at_1', 'N/A')}",
            f"- Recall@3: {m.get('recall_at_3', 'N/A')}",
            f"- Recall@5: {m.get('recall_at_5', 'N/A')}",
            "",
        ])
    report_lines.extend([
        "## Limitations",
        "",
        "- Public texture datasets, not luxury authentication datasets.",
        "- Results are diagnostic only.",
        "",
    ])
    report_path = output_dir / f"{prefix}__report.md"
    report_path.write_text("\n".join(report_lines) + "\n")

    print(f"\nRecord:   {record_path}")
    print(f"Training: {training_path}")
    if eval_results:
        print(f"Eval:     {eval_path}")
    print(f"Model:    {model_path}")
    print(f"Report:   {report_path}")

    if args.register_model:
        print("\nWARNING: --register-model not implemented in experiment runner.")
        print("  Use scripts/train_model.py for production model registration.")


if __name__ == "__main__":
    main()
