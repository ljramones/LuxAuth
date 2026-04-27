"""Tests for experiment loss functions."""

import torch

from experiments.losses import (
    BATCH_LOSSES,
    LOSS_REGISTRY,
    PAIR_LOSSES,
    BatchHardTripletLoss,
    ContrastiveLoss,
    SupervisedContrastiveLoss,
    TripletLoss,
    mine_triplets_random,
)


class TestContrastiveLoss:
    def test_finite_loss(self):
        loss_fn = ContrastiveLoss(margin=1.0)
        emb1 = torch.randn(4, 128)
        emb2 = torch.randn(4, 128)
        labels = torch.tensor([1.0, 0.0, 1.0, 0.0])
        loss = loss_fn(emb1, emb2, labels)
        assert torch.isfinite(loss)
        assert loss.item() >= 0

    def test_zero_for_identical_positives(self):
        loss_fn = ContrastiveLoss(margin=1.0)
        emb = torch.randn(4, 64)
        labels = torch.ones(4)
        loss = loss_fn(emb, emb, labels)
        assert loss.item() < 0.01


class TestSupervisedContrastiveLoss:
    def test_finite_loss(self):
        loss_fn = SupervisedContrastiveLoss(temperature=0.07)
        embs = torch.nn.functional.normalize(torch.randn(8, 128), dim=1)
        labels = torch.tensor([0, 0, 1, 1, 2, 2, 3, 3])
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)

    def test_no_positive_pairs(self):
        loss_fn = SupervisedContrastiveLoss(temperature=0.07)
        embs = torch.nn.functional.normalize(torch.randn(4, 64), dim=1)
        labels = torch.tensor([0, 1, 2, 3])  # all different
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)
        assert loss.item() == 0.0

    def test_single_sample(self):
        loss_fn = SupervisedContrastiveLoss()
        embs = torch.randn(1, 64)
        labels = torch.tensor([0])
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)

    def test_all_same_class(self):
        loss_fn = SupervisedContrastiveLoss(temperature=0.07)
        embs = torch.nn.functional.normalize(torch.randn(6, 64), dim=1)
        labels = torch.zeros(6, dtype=torch.long)
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)


class TestTripletLoss:
    def test_finite_loss(self):
        loss_fn = TripletLoss(margin=0.2)
        anchor = torch.randn(4, 128)
        positive = anchor + torch.randn(4, 128) * 0.1
        negative = torch.randn(4, 128)
        loss = loss_fn(anchor, positive, negative)
        assert torch.isfinite(loss)
        assert loss.item() >= 0

    def test_easy_triplets_zero(self):
        loss_fn = TripletLoss(margin=0.2)
        anchor = torch.randn(4, 128)
        positive = anchor.clone()
        negative = anchor + torch.ones(4, 128) * 10
        loss = loss_fn(anchor, positive, negative)
        assert loss.item() < 0.01


class TestBatchHardTripletLoss:
    def test_finite_loss(self):
        loss_fn = BatchHardTripletLoss(margin=0.2)
        embs = torch.randn(8, 64)
        labels = torch.tensor([0, 0, 1, 1, 2, 2, 3, 3])
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)

    def test_single_class(self):
        loss_fn = BatchHardTripletLoss(margin=0.2)
        embs = torch.randn(4, 64)
        labels = torch.zeros(4, dtype=torch.long)
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)
        assert loss.item() == 0.0

    def test_small_batch(self):
        loss_fn = BatchHardTripletLoss(margin=0.2)
        embs = torch.randn(1, 64)
        labels = torch.tensor([0])
        loss = loss_fn(embs, labels)
        assert torch.isfinite(loss)


class TestTripletMining:
    def test_generates_triplets(self):
        labels = [0, 0, 0, 1, 1, 1, 2, 2]
        triplets = mine_triplets_random(labels, n_triplets=20, seed=42)
        assert len(triplets) > 0
        for a, p, n in triplets:
            assert labels[a] == labels[p]
            assert labels[a] != labels[n]

    def test_single_class_empty(self):
        labels = [0, 0, 0, 0]
        triplets = mine_triplets_random(labels, n_triplets=20)
        assert len(triplets) == 0

    def test_no_multi_sample_empty(self):
        labels = [0, 1, 2, 3]
        triplets = mine_triplets_random(labels, n_triplets=20)
        assert len(triplets) == 0


class TestRegistry:
    def test_all_losses_registered(self):
        assert "contrastive" in LOSS_REGISTRY
        assert "supervised_contrastive" in LOSS_REGISTRY
        assert "triplet" in LOSS_REGISTRY
        assert "batch_hard_triplet" in LOSS_REGISTRY

    def test_batch_losses_classified(self):
        assert "supervised_contrastive" in BATCH_LOSSES
        assert "batch_hard_triplet" in BATCH_LOSSES
        assert "contrastive" in PAIR_LOSSES

    def test_create_loss_from_config(self):
        from experiments.learned_metric_experiment import LMExperimentConfig
        from experiments.losses import create_loss

        for loss_name in ["contrastive", "supervised_contrastive", "batch_hard_triplet"]:
            config = LMExperimentConfig(loss=loss_name)
            loss = create_loss(config)
            assert loss is not None

    def test_create_loss_dict_config(self):
        from experiments.learned_metric_experiment import LMExperimentConfig
        from experiments.losses import create_loss

        config = LMExperimentConfig(loss={"name": "supervised_contrastive", "temperature": 0.1})
        loss = create_loss(config)
        assert loss is not None
        assert loss.temperature == 0.1
