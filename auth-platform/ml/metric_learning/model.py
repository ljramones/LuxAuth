"""Embedding model architecture."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models


class EmbeddingModel(nn.Module):
    """ResNet18 backbone with projection head for metric learning."""

    def __init__(self, embedding_dim: int = 128):
        super().__init__()
        backbone = models.resnet18(weights=None)
        # Remove the final FC layer
        self.features = nn.Sequential(*list(backbone.children())[:-1])
        # Projection head: 512 -> embedding_dim
        self.projection = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Linear(256, embedding_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return L2-normalized embedding."""
        features = self.features(x)
        features = features.view(features.size(0), -1)  # flatten
        embedding = self.projection(features)
        embedding = F.normalize(embedding, p=2, dim=1)
        return embedding
