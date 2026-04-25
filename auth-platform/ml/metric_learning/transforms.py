"""Image transforms for training and inference."""

import io
import numpy as np
from PIL import Image
import torch
from torchvision import transforms


def get_train_transform(input_size: int = 224, augmentations: bool = True) -> transforms.Compose:
    if augmentations:
        return transforms.Compose([
            transforms.Resize((input_size, input_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(p=0.2),
            transforms.RandomRotation(degrees=10),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def get_eval_transform(input_size: int = 224) -> transforms.Compose:
    return transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def bytes_to_pil(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def preprocess_for_inference(data: bytes, input_size: int = 224) -> torch.Tensor:
    """Preprocess image bytes to a model-ready tensor. Returns [1, 3, H, W]."""
    img = bytes_to_pil(data)
    transform = get_eval_transform(input_size)
    return transform(img).unsqueeze(0)
