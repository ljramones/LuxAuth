"""Training configuration."""

from dataclasses import dataclass, field


@dataclass
class TrainingConfig:
    # Model
    model_name: str = "learned_metric"
    model_version: str = "v0.1.0"
    embedding_dim: int = 128
    input_size: int = 224

    # Training
    epochs: int = 10
    batch_size: int = 8
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    margin: float = 1.0
    seed: int = 42

    # Loss
    loss_type: str = "contrastive"

    # Data
    dataset_version: str = "synthetic_lv_monogram_v0.1.0"
    preprocessing_version: str = "normalize_image_v0.1.0"

    # Infrastructure
    db_dsn: str = "postgresql://authplatform:authplatform@localhost:5432/authplatform"
    s3_endpoint: str = "http://localhost:4566"
    s3_bucket_artifacts: str = "auth-platform-ml-artifacts"
    s3_bucket_reference: str = "auth-platform-reference-library"
    s3_bucket_normalized: str = "auth-platform-normalized-evidence"

    def artifact_prefix(self) -> str:
        return f"models/{self.model_name}_{self.model_version}"
