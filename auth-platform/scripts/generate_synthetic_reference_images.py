#!/usr/bin/env python3
"""Generate synthetic reference images for local pipeline testing.

Creates deterministic texture images that simulate:
- Authentic-like textures (smooth, regular patterns)
- Counterfeit-like textures (rougher, irregular patterns)
- Query images for each group
- Bad quality images (blurry, overexposed, underexposed, glare)

These are NOT real product images. They are synthetic textures for pipeline testing only.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

OUTPUT_DIR = Path("sample_data")
REGIONS = [
    "EXTERIOR_CANVAS",
    "FRONT_LOGO_PRINT",
    "INTERIOR_HEAT_STAMP",
    "HARDWARE_ENGRAVING",
    "STITCHING_DETAIL",
]
IMG_SIZE = 512
RNG = np.random.RandomState(42)


def make_texture(seed: int, roughness: float = 0.3, size: int = IMG_SIZE) -> np.ndarray:
    """Generate a synthetic texture image.

    Lower roughness = smoother/more regular (authentic-like).
    Higher roughness = rougher/more irregular (counterfeit-like).
    """
    rng = np.random.RandomState(seed)
    # Base: smooth gradient with noise
    x = np.linspace(0, 4 * np.pi, size)
    y = np.linspace(0, 4 * np.pi, size)
    xx, yy = np.meshgrid(x, y)

    # Regular pattern component
    pattern = np.sin(xx * (2 + seed % 3)) * np.cos(yy * (2 + seed % 4))
    pattern = (pattern + 1) / 2  # normalize to 0-1

    # Noise component scaled by roughness
    noise = rng.normal(0, roughness, (size, size))

    # Color channels with slight variation
    r = np.clip((pattern + noise) * 180 + 40, 0, 255)
    g = np.clip((pattern + noise * 0.8) * 160 + 50, 0, 255)
    b = np.clip((pattern + noise * 0.6) * 140 + 60, 0, 255)

    img = np.stack([r, g, b], axis=-1).astype(np.uint8)
    return img


def save_image(arr: np.ndarray, path: Path, fmt: str = "JPEG") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.fromarray(arr)
    img.save(str(path), format=fmt, quality=95)


def make_blurry(arr: np.ndarray) -> np.ndarray:
    img = Image.fromarray(arr)
    img = img.filter(ImageFilter.GaussianBlur(radius=15))
    return np.array(img)


def make_overexposed(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr.astype(float) * 2.5, 0, 255).astype(np.uint8)


def make_underexposed(arr: np.ndarray) -> np.ndarray:
    return np.clip(arr.astype(float) * 0.15, 0, 255).astype(np.uint8)


def make_glare(arr: np.ndarray) -> np.ndarray:
    result = arr.copy()
    h, w = result.shape[:2]
    cy, cx = h // 2, w // 2
    y, x = np.ogrid[:h, :w]
    mask = ((x - cx)**2 + (y - cy)**2) < (min(h, w) // 4)**2
    result[mask] = 255
    return result


def main():
    print("Generating synthetic reference images...")

    # Authentic reference images (low roughness)
    for i, region in enumerate(REGIONS):
        for j in range(3):  # 3 per region
            seed = 100 + i * 10 + j
            arr = make_texture(seed, roughness=0.15)
            path = OUTPUT_DIR / "reference" / "authentic" / "Louis_Vuitton" / "handbag" / "monogram_canvas" / region / f"auth_{i}_{j}.jpg"
            save_image(arr, path)
    print(f"  Created {len(REGIONS) * 3} authentic reference images")

    # Counterfeit reference images (high roughness)
    for i, region in enumerate(REGIONS):
        for j in range(3):
            seed = 500 + i * 10 + j
            arr = make_texture(seed, roughness=0.55)
            path = OUTPUT_DIR / "reference" / "counterfeit" / "Louis_Vuitton" / "handbag" / "monogram_canvas" / region / f"fake_{i}_{j}.jpg"
            save_image(arr, path)
    print(f"  Created {len(REGIONS) * 3} counterfeit reference images")

    # Query images - authentic-like
    for i, region in enumerate(REGIONS):
        seed = 200 + i * 10
        arr = make_texture(seed, roughness=0.18)
        path = OUTPUT_DIR / "query" / "authentic_like" / region / f"query_auth_{i}.jpg"
        save_image(arr, path)
    print(f"  Created {len(REGIONS)} authentic-like query images")

    # Query images - counterfeit-like
    for i, region in enumerate(REGIONS):
        seed = 600 + i * 10
        arr = make_texture(seed, roughness=0.50)
        path = OUTPUT_DIR / "query" / "counterfeit_like" / region / f"query_fake_{i}.jpg"
        save_image(arr, path)
    print(f"  Created {len(REGIONS)} counterfeit-like query images")

    # Bad quality images
    base = make_texture(999, roughness=0.2)
    bad_dir = OUTPUT_DIR / "query" / "bad_quality"

    save_image(make_blurry(base), bad_dir / "blurry.jpg")
    save_image(make_overexposed(base), bad_dir / "overexposed.jpg")
    save_image(make_underexposed(base), bad_dir / "underexposed.jpg")
    save_image(make_glare(base), bad_dir / "glare.jpg")
    # Tiny image
    tiny = Image.fromarray(base).resize((30, 30))
    (bad_dir).mkdir(parents=True, exist_ok=True)
    tiny.save(str(bad_dir / "too_small.jpg"), quality=95)
    print("  Created 5 bad quality images")

    print(f"\nAll images written to {OUTPUT_DIR}/")
    print("NOTE: These are synthetic textures for pipeline testing only.")
    print("They do NOT represent real luxury products.")


if __name__ == "__main__":
    main()
