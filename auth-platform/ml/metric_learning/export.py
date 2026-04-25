"""Export trained model artifact to S3."""

import io
import json
import uuid
from datetime import UTC, datetime

import boto3
import psycopg2
import torch

from metric_learning.config import TrainingConfig


def export_model(model: torch.nn.Module, train_result: dict, config: TrainingConfig) -> str:
    """Export model to S3 and register in model_versions. Returns artifact URI."""

    s3 = boto3.client(
        "s3",
        endpoint_url=config.s3_endpoint,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )

    prefix = config.artifact_prefix()

    # Save model.pt
    buf = io.BytesIO()
    torch.save(model.state_dict(), buf)
    buf.seek(0)
    model_key = f"{prefix}/model.pt"
    s3.put_object(Bucket=config.s3_bucket_artifacts, Key=model_key, Body=buf.getvalue())
    artifact_uri = f"s3://{config.s3_bucket_artifacts}/{model_key}"
    print(f"  Model artifact: {artifact_uri}")

    # Save metadata.json
    metadata = {
        "model_name": config.model_name,
        "model_version": config.model_version,
        "embedding_dimension": config.embedding_dim,
        "dataset_version": config.dataset_version,
        "training_run_id": train_result["run_id"],
        "training_started_at": train_result["started_at"].isoformat(),
        "training_completed_at": train_result["completed_at"].isoformat(),
        "epochs": config.epochs,
        "batch_size": config.batch_size,
        "learning_rate": config.learning_rate,
        "loss_type": config.loss_type,
        "final_train_loss": train_result["metrics"].get("final_train_loss"),
        "final_val_loss": train_result["metrics"].get("final_val_loss"),
        "input_size": config.input_size,
        "preprocessing_version": config.preprocessing_version,
    }
    metadata_key = f"{prefix}/metadata.json"
    s3.put_object(
        Bucket=config.s3_bucket_artifacts,
        Key=metadata_key,
        Body=json.dumps(metadata, indent=2),
        ContentType="application/json",
    )
    metadata_uri = f"s3://{config.s3_bucket_artifacts}/{metadata_key}"
    print(f"  Metadata: {metadata_uri}")

    # Register in model_versions
    conn = psycopg2.connect(config.db_dsn)
    conn.autocommit = True
    cur = conn.cursor()

    full_version = f"{config.model_name}_{config.model_version}"

    # Check if already registered
    cur.execute("SELECT id FROM model_versions WHERE model_name = %s AND model_version = %s",
                (config.model_name, full_version))
    existing = cur.fetchone()
    if existing:
        cur.execute("UPDATE model_versions SET artifact_uri = %s, is_active = TRUE WHERE id = %s",
                    (artifact_uri, existing[0]))
    else:
        cur.execute("""
            INSERT INTO model_versions (id, model_name, model_version, model_type,
                artifact_uri, description, is_active)
            VALUES (%s, %s, %s, 'EMBEDDING', %s, %s, TRUE)
        """, (str(uuid.uuid4()), config.model_name, full_version,
              artifact_uri,
              f"Trained metric-learning model on {config.dataset_version}"))

    # Update training run with artifact URI
    cur.execute("""
        UPDATE training_runs SET artifact_uri = %s, metadata_uri = %s WHERE id = %s
    """, (artifact_uri, metadata_uri, train_result["run_id"]))

    # Audit
    cur.execute("""
        INSERT INTO audit_events (id, event_type, payload, created_at)
        VALUES (%s, 'MODEL_VERSION_REGISTERED', %s, %s)
    """, (str(uuid.uuid4()),
          json.dumps({"model_name": config.model_name, "model_version": full_version, "artifact_uri": artifact_uri}),
          datetime.now(UTC)))

    cur.close()
    conn.close()

    return artifact_uri
