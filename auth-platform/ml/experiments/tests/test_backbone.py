"""Tests for backbone and freeze_backbone support."""

import torch

from experiments.learned_metric_experiment import (
    LMExperimentConfig,
    create_model,
)


class TestFreezeBackbone:
    def test_frozen_reduces_trainable_params(self):
        unfrozen = create_model(backbone="resnet18", pretrained=False,
                                embedding_dim=256, allow_random_init=True, freeze_backbone=False)
        frozen = create_model(backbone="resnet18", pretrained=False,
                              embedding_dim=256, allow_random_init=True, freeze_backbone=True)

        trainable_unfrozen = sum(p.numel() for p in unfrozen.parameters() if p.requires_grad)
        trainable_frozen = sum(p.numel() for p in frozen.parameters() if p.requires_grad)

        assert trainable_frozen < trainable_unfrozen
        assert trainable_frozen > 0  # projection head still trainable

    def test_frozen_backbone_params_not_grad(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=256, allow_random_init=True, freeze_backbone=True)
        for param in model.features.parameters():
            assert not param.requires_grad

    def test_frozen_projection_still_trainable(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=256, allow_random_init=True, freeze_backbone=True)
        for param in model.projection.parameters():
            assert param.requires_grad

    def test_unfrozen_all_trainable(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=256, allow_random_init=True, freeze_backbone=False)
        for param in model.parameters():
            assert param.requires_grad


class TestEmbeddingDim:
    def test_256_dim(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=256, allow_random_init=True)
        out = model(torch.randn(2, 3, 224, 224))
        assert out.shape == (2, 256)

    def test_512_dim(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=512, allow_random_init=True)
        out = model(torch.randn(2, 3, 224, 224))
        assert out.shape == (2, 512)

    def test_output_normalized(self):
        model = create_model(backbone="resnet18", pretrained=False,
                             embedding_dim=512, allow_random_init=True)
        out = model(torch.randn(4, 3, 224, 224))
        norms = torch.norm(out, dim=1)
        assert torch.allclose(norms, torch.ones(4), atol=0.01)


class TestResNet50:
    def test_resnet50_creates(self):
        model = create_model(backbone="resnet50", pretrained=False,
                             embedding_dim=256, allow_random_init=True)
        out = model(torch.randn(2, 3, 224, 224))
        assert out.shape == (2, 256)

    def test_resnet50_frozen(self):
        model = create_model(backbone="resnet50", pretrained=False,
                             embedding_dim=256, allow_random_init=True, freeze_backbone=True)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total = sum(p.numel() for p in model.parameters())
        assert trainable < total

    def test_resnet50_more_params_than_18(self):
        m18 = create_model(backbone="resnet18", pretrained=False,
                           embedding_dim=256, allow_random_init=True)
        m50 = create_model(backbone="resnet50", pretrained=False,
                           embedding_dim=256, allow_random_init=True)
        p18 = sum(p.numel() for p in m18.parameters())
        p50 = sum(p.numel() for p in m50.parameters())
        assert p50 > p18


class TestConfigParsing:
    def test_freeze_backbone_default_false(self):
        config = LMExperimentConfig()
        assert config.freeze_backbone is False

    def test_freeze_backbone_in_config(self):
        config = LMExperimentConfig(freeze_backbone=True)
        assert config.freeze_backbone is True

    def test_old_config_without_freeze(self):
        """Config files without freeze_backbone should still parse."""
        import tempfile

        import yaml
        data = {
            "model_name": "learned_metric",
            "model_version": "v0.2.0",
            "backbone": "resnet18",
            "pretrained": True,
            "embedding_dim": 256,
            "dataset_version": "test",
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            path = f.name
        config = LMExperimentConfig.from_yaml(path)
        assert config.freeze_backbone is False  # default
