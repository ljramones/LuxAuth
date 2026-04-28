"""Tests for augmentation profiles, optimizer/scheduler configs, and projection head."""

import torch

from experiments.learned_metric_experiment import (
    AUGMENTATION_PROFILES,
    LMExperimentConfig,
    build_train_transform,
    create_model,
)


class TestAugmentationProfiles:
    def test_none_profile(self):
        config = LMExperimentConfig(augmentation_profile="none")
        t = build_train_transform(config)
        assert t is not None

    def test_light_profile(self):
        config = LMExperimentConfig(augmentation_profile="light")
        t = build_train_transform(config)
        assert t is not None

    def test_medium_profile(self):
        config = LMExperimentConfig(augmentation_profile="medium")
        t = build_train_transform(config)
        assert t is not None

    def test_strong_profile(self):
        config = LMExperimentConfig(augmentation_profile="strong")
        t = build_train_transform(config)
        assert t is not None

    def test_invalid_profile_raises(self):
        config = LMExperimentConfig(augmentation_profile="nonexistent")
        try:
            build_train_transform(config)
            raise AssertionError("Should have raised")
        except ValueError as e:
            assert "Unknown augmentation profile" in str(e)

    def test_empty_profile_uses_augmentations_dict(self):
        config = LMExperimentConfig(
            augmentation_profile="",
            augmentations={"horizontal_flip": True},
        )
        t = build_train_transform(config)
        assert t is not None

    def test_all_profiles_defined(self):
        for name in ["none", "light", "medium", "strong"]:
            assert name in AUGMENTATION_PROFILES


class TestOptimizerConfig:
    def test_adam_default(self):
        config = LMExperimentConfig()
        assert config.optimizer.get("name", "adam") == "adam"

    def test_adamw_parsed(self):
        config = LMExperimentConfig(optimizer={"name": "adamw", "weight_decay": 0.01})
        assert config.optimizer["name"] == "adamw"


class TestSchedulerConfig:
    def test_none_default(self):
        config = LMExperimentConfig()
        assert config.scheduler.get("name", "none") == "none"

    def test_cosine_parsed(self):
        config = LMExperimentConfig(scheduler={"name": "cosine", "min_lr": 1e-6})
        assert config.scheduler["name"] == "cosine"


class TestProjectionHead:
    def test_default_hidden_dim(self):
        config = LMExperimentConfig()
        assert config.projection_head.get("hidden_dim", 256) == 256

    def test_custom_hidden_dim(self):
        model = create_model(
            backbone="resnet18", pretrained=False, embedding_dim=256,
            allow_random_init=True,
            projection_head={"hidden_dim": 512, "dropout": 0.0},
        )
        out = model(torch.randn(2, 3, 224, 224))
        assert out.shape == (2, 256)

    def test_dropout_in_projection(self):
        model = create_model(
            backbone="resnet18", pretrained=False, embedding_dim=256,
            allow_random_init=True,
            projection_head={"hidden_dim": 256, "dropout": 0.1},
        )
        # Check that Dropout layer exists in projection
        has_dropout = any(
            isinstance(m, torch.nn.Dropout) for m in model.projection.modules()
        )
        assert has_dropout

    def test_no_dropout_default(self):
        model = create_model(
            backbone="resnet18", pretrained=False, embedding_dim=256,
            allow_random_init=True,
            projection_head={"hidden_dim": 256, "dropout": 0.0},
        )
        has_dropout = any(
            isinstance(m, torch.nn.Dropout) for m in model.projection.modules()
        )
        assert not has_dropout


class TestYAMLParsing:
    def test_augmentation_profile_from_yaml(self):
        import tempfile

        import yaml
        data = {
            "model_name": "learned_metric",
            "dataset_version": "test",
            "augmentation_profile": "medium",
            "optimizer": {"name": "adamw", "weight_decay": 0.01},
            "scheduler": {"name": "cosine", "min_lr": 1e-6},
            "projection_head": {"hidden_dim": 512, "dropout": 0.1},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = f.name
        config = LMExperimentConfig.from_yaml(path)
        assert config.augmentation_profile == "medium"
        assert config.optimizer["name"] == "adamw"
        assert config.scheduler["name"] == "cosine"
        assert config.projection_head["hidden_dim"] == 512
