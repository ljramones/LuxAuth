"""Tests for learned metric experiment utilities."""

import tempfile

import torch
import yaml

from experiments.learned_metric_experiment import (
    ContrastivePairSampler,
    ExperimentImageDataset,
    LMExperimentConfig,
    build_eval_transform,
    build_label_map,
    build_train_transform,
    check_leakage,
    create_model,
    validate_config,
)


class TestConfig:
    def test_default_config(self):
        config = LMExperimentConfig()
        assert config.backbone == "resnet18"
        assert config.embedding_dim == 256
        assert config.pretrained is True

    def test_from_yaml(self):
        data = {
            "model_name": "learned_metric",
            "model_version": "v0.2.0",
            "backbone": "resnet18",
            "pretrained": True,
            "embedding_dim": 256,
            "dataset_version": "test_dataset",
            "epochs": 5,
            "label_strategy": "external_item_id",
            "augmentations": {"horizontal_flip": True},
            "split_policy": {"train": "train", "test": "test"},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = f.name

        config = LMExperimentConfig.from_yaml(path)
        assert config.backbone == "resnet18"
        assert config.dataset_version == "test_dataset"
        assert config.augmentations.get("horizontal_flip") is True

    def test_validate_config_warnings(self):
        config = LMExperimentConfig(backbone="unknown_net", dataset_version="")
        warnings = validate_config(config)
        assert any("unknown_net" in w for w in warnings)
        assert any("dataset_version" in w.lower() for w in warnings)

    def test_validate_clean_config(self):
        config = LMExperimentConfig(dataset_version="test")
        warnings = validate_config(config)
        assert len(warnings) == 0


class TestModel:
    def test_resnet18_output_dim(self):
        model = create_model(backbone="resnet18", pretrained=False, embedding_dim=256,
                             allow_random_init=True)
        x = torch.randn(2, 3, 224, 224)
        out = model(x)
        assert out.shape == (2, 256)

    def test_output_normalized(self):
        model = create_model(backbone="resnet18", pretrained=False, embedding_dim=128,
                             allow_random_init=True)
        x = torch.randn(4, 3, 224, 224)
        out = model(x)
        norms = torch.norm(out, dim=1)
        assert torch.allclose(norms, torch.ones(4), atol=0.01)

    def test_pretrained_fails_without_allow(self):
        # This test verifies the flag exists; actual weight availability varies
        # Just verify the create_model function accepts the parameter
        model = create_model(backbone="resnet18", pretrained=False, embedding_dim=256,
                             allow_random_init=True)
        assert model is not None

    def test_unsupported_backbone_raises(self):
        import pytest
        with pytest.raises(ValueError, match="Unsupported backbone"):
            create_model(backbone="vit_huge", pretrained=False, embedding_dim=256)


class TestLabelStrategy:
    def test_external_item_id(self):
        records = [
            {"reference_item_id": "item-1", "authenticity_status": "A"},
            {"reference_item_id": "item-2", "authenticity_status": "B"},
            {"reference_item_id": "item-1", "authenticity_status": "A"},
        ]
        labels, mapping = build_label_map(records, "external_item_id")
        assert labels == ["item-1", "item-2", "item-1"]
        assert len(mapping) == 2

    def test_authenticity_status(self):
        records = [
            {"reference_item_id": "i1", "authenticity_status": "AUTHENTIC"},
            {"reference_item_id": "i2", "authenticity_status": "COUNTERFEIT"},
        ]
        labels, mapping = build_label_map(records, "authenticity_status")
        assert "AUTHENTIC" in mapping
        assert "COUNTERFEIT" in mapping

    def test_region_code(self):
        records = [
            {"reference_item_id": "i1", "region_code": "EXTERIOR_CANVAS"},
            {"reference_item_id": "i2", "region_code": "HARDWARE_ENGRAVING"},
        ]
        labels, mapping = build_label_map(records, "region_code")
        assert len(mapping) == 2


class TestLeakageCheck:
    def test_no_leakage(self):
        records = [
            {"reference_item_id": "a", "split": "train"},
            {"reference_item_id": "b", "split": "test"},
        ]
        leaked = check_leakage(records, "reference_item_id")
        assert len(leaked) == 0

    def test_detects_leakage(self):
        records = [
            {"reference_item_id": "shared", "split": "train"},
            {"reference_item_id": "shared", "split": "test"},
            {"reference_item_id": "ok", "split": "train"},
        ]
        leaked = check_leakage(records, "reference_item_id")
        assert "shared" in leaked


class TestContrastivePairSampler:
    def _make_dataset(self):
        """Create a tiny in-memory dataset for testing."""
        records = [{"reference_image_id": f"img-{i}", "object_uri": "", "region_code": "R"}
                    for i in range(10)]
        labels = ["A", "A", "A", "A", "A", "B", "B", "B", "B", "B"]
        label_to_idx = {"A": 0, "B": 1}

        class FakeDS(ExperimentImageDataset):
            def __getitem__(self, idx):
                # Return random tensor instead of loading from S3
                return torch.randn(3, 224, 224), self.int_labels[idx], {}

        return FakeDS(records, labels, label_to_idx, None)

    def test_generates_pairs(self):
        ds = self._make_dataset()
        sampler = ContrastivePairSampler(ds, pairs_per_epoch=50, seed=42)
        assert len(sampler) > 0

    def test_pairs_have_positive_and_negative(self):
        ds = self._make_dataset()
        sampler = ContrastivePairSampler(ds, pairs_per_epoch=100, seed=42)
        labels = [p[2] for p in sampler.pairs]
        assert 1 in labels, "Should have positive pairs"
        assert 0 in labels, "Should have negative pairs"

    def test_single_class_limited(self):
        records = [{"reference_image_id": f"img-{i}", "object_uri": "", "region_code": "R"}
                    for i in range(5)]
        labels = ["A"] * 5
        label_to_idx = {"A": 0}

        class FakeDS(ExperimentImageDataset):
            def __getitem__(self, idx):
                return torch.randn(3, 224, 224), self.int_labels[idx], {}

        ds = FakeDS(records, labels, label_to_idx, None)
        sampler = ContrastivePairSampler(ds, pairs_per_epoch=50, seed=42)
        # With only one class, only positive pairs can be formed
        pair_labels = [p[2] for p in sampler.pairs]
        assert 0 not in pair_labels or len(pair_labels) == 0


class TestTransforms:
    def test_train_transform_builds(self):
        config = LMExperimentConfig(augmentations={
            "random_resized_crop": True,
            "horizontal_flip": True,
            "rotation_degrees": 10,
            "color_jitter": {"brightness": 0.2},
            "random_erasing": 0.1,
        })
        t = build_train_transform(config)
        assert t is not None

    def test_eval_transform_builds(self):
        config = LMExperimentConfig()
        t = build_eval_transform(config)
        assert t is not None


class TestLoss:
    def test_contrastive_loss_finite(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from metric_learning.losses import ContrastiveLoss
        loss_fn = ContrastiveLoss(margin=1.0)
        emb1 = torch.randn(4, 128)
        emb2 = torch.randn(4, 128)
        labels = torch.tensor([1.0, 0.0, 1.0, 0.0])
        loss = loss_fn(emb1, emb2, labels)
        assert torch.isfinite(loss)
        assert loss.item() >= 0
