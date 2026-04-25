"""Metric learning loss functions."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ContrastiveLoss(nn.Module):
    """Contrastive loss for pairs.

    positive_label=1 means same class (both authentic or both counterfeit).
    positive_label=0 means different class.
    """

    def __init__(self, margin: float = 1.0):
        super().__init__()
        self.margin = margin

    def forward(
        self, embedding1: torch.Tensor, embedding2: torch.Tensor, label: torch.Tensor
    ) -> torch.Tensor:
        """
        label=1 → similar pair (pull together)
        label=0 → dissimilar pair (push apart)
        """
        distance = F.pairwise_distance(embedding1, embedding2)
        loss_positive = label * distance.pow(2)
        loss_negative = (1 - label) * F.relu(self.margin - distance).pow(2)
        return (loss_positive + loss_negative).mean()
