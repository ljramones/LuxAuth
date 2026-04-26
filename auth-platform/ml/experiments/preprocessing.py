"""Preprocessing strategies for embedding experiments.

Each strategy accepts raw image bytes and returns either a single normalized
image (as bytes) or a list of normalized images (for multi-crop/tile strategies).

These strategies are for experimental comparison only. They do not alter the
backend normalization pipeline.
"""

import io
import math

import cv2
import numpy as np
from PIL import Image

TARGET_SIZE = 512


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _bytes_to_pil(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _center_crop_square(img: Image.Image) -> Image.Image:
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return img.crop((left, top, left + side, top + side))


# ---------------------------------------------------------------------------
# Strategy 1: center_crop_512
# ---------------------------------------------------------------------------

def center_crop_512(data: bytes) -> list[bytes]:
    """Center crop to square and resize to 512x512. Matches backend default."""
    img = _bytes_to_pil(data)
    img = _center_crop_square(img)
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
    return [_pil_to_bytes(img)]


# ---------------------------------------------------------------------------
# Strategy 2: padded_resize_512
# ---------------------------------------------------------------------------

def padded_resize_512(data: bytes) -> list[bytes]:
    """Resize to fit within 512x512, pad with edge-reflect to preserve aspect ratio.

    Padding uses reflect mode to avoid introducing artificial solid-color borders
    that could affect texture features. The full field of view is preserved.
    """
    img = _bytes_to_pil(data)
    w, h = img.size
    scale = TARGET_SIZE / max(w, h)
    new_w = round(w * scale)
    new_h = round(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)

    arr = np.array(img)
    pad_top = (TARGET_SIZE - new_h) // 2
    pad_bottom = TARGET_SIZE - new_h - pad_top
    pad_left = (TARGET_SIZE - new_w) // 2
    pad_right = TARGET_SIZE - new_w - pad_left
    arr = np.pad(arr, ((pad_top, pad_bottom), (pad_left, pad_right), (0, 0)), mode="reflect")

    result = Image.fromarray(arr)
    return [_pil_to_bytes(result)]


# ---------------------------------------------------------------------------
# Strategy 3: five_crop_512
# ---------------------------------------------------------------------------

def five_crop_512(data: bytes) -> list[bytes]:
    """Extract five crops (center, TL, TR, BL, BR), each resized to 512x512.

    For embedding aggregation, embed each crop and average + L2-normalize.
    """
    img = _bytes_to_pil(data)
    w, h = img.size
    side = min(w, h)
    crops = []

    # center
    cx, cy = w // 2, h // 2
    crops.append(img.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2)))
    # top-left
    crops.append(img.crop((0, 0, side, side)))
    # top-right
    crops.append(img.crop((max(0, w - side), 0, w, side)))
    # bottom-left
    crops.append(img.crop((0, max(0, h - side), side, h)))
    # bottom-right
    crops.append(img.crop((max(0, w - side), max(0, h - side), w, h)))

    result = []
    for crop in crops:
        crop = crop.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
        result.append(_pil_to_bytes(crop))
    return result


# ---------------------------------------------------------------------------
# Strategy 4: grayscale_center_crop_512
# ---------------------------------------------------------------------------

def grayscale_center_crop_512(data: bytes) -> list[bytes]:
    """Center crop, resize, convert to grayscale, then back to 3-channel RGB.

    Purpose: test embedding dependence on color information.
    """
    img = _bytes_to_pil(data)
    img = _center_crop_square(img)
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
    gray = img.convert("L")
    img = gray.convert("RGB")
    return [_pil_to_bytes(img)]


# ---------------------------------------------------------------------------
# Strategy 5: clahe_center_crop_512
# ---------------------------------------------------------------------------

def clahe_center_crop_512(data: bytes) -> list[bytes]:
    """Center crop, resize, then apply CLAHE to luminance channel.

    Uses OpenCV CLAHE on the L channel in LAB color space. Parameters are
    fixed for deterministic output.
    """
    img = _bytes_to_pil(data)
    img = _center_crop_square(img)
    img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)

    arr = np.array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    arr = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    result = Image.fromarray(arr)
    return [_pil_to_bytes(result)]


# ---------------------------------------------------------------------------
# Strategy 6: tile_224_average
# ---------------------------------------------------------------------------

def tile_224_average(data: bytes, max_tiles: int = 0) -> list[bytes]:
    """Resize/pad to consistent size, extract non-overlapping 224x224 tiles.

    Tiles are extracted on a fixed grid. Edge tiles that don't fill 224x224
    are padded with reflect. Returns at least one tile.

    Args:
        data: Raw image bytes.
        max_tiles: If > 0, cap the number of tiles returned (evenly sampled
            from the full grid). 0 means no limit.

    For embedding: embed each tile, average, L2-normalize.
    """
    img = _bytes_to_pil(data)
    # Resize so the short side is at least 224
    w, h = img.size
    if min(w, h) < 224:
        scale = 224 / min(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)

    arr = np.array(img)
    h, w = arr.shape[:2]
    tile_size = 224

    tiles = []
    rows = max(1, math.ceil(h / tile_size))
    cols = max(1, math.ceil(w / tile_size))

    for r in range(rows):
        for c in range(cols):
            y0 = r * tile_size
            x0 = c * tile_size
            y1 = min(y0 + tile_size, h)
            x1 = min(x0 + tile_size, w)
            tile = arr[y0:y1, x0:x1]

            # Pad if tile is smaller than 224x224
            ph = tile_size - tile.shape[0]
            pw = tile_size - tile.shape[1]
            if ph > 0 or pw > 0:
                tile = np.pad(tile, ((0, ph), (0, pw), (0, 0)), mode="reflect")

            tiles.append(_pil_to_bytes(Image.fromarray(tile)))

    if not tiles:
        tiles = [_pil_to_bytes(img.resize((tile_size, tile_size), Image.LANCZOS))]

    # Cap tiles if max_tiles is set
    if max_tiles > 0 and len(tiles) > max_tiles:
        step = len(tiles) / max_tiles
        tiles = [tiles[int(i * step)] for i in range(max_tiles)]

    return tiles


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Module-level config for tile_224_average max_tiles.
# Set via set_max_tiles() before running experiments.
_max_tiles: int = 0


def set_max_tiles(n: int) -> None:
    """Set the max tiles cap for tile_224_average. 0 means no limit."""
    global _max_tiles
    _max_tiles = n


def _tile_224_average_wrapper(data: bytes) -> list[bytes]:
    """Wrapper that passes module-level max_tiles to tile_224_average."""
    return tile_224_average(data, max_tiles=_max_tiles)


STRATEGIES: dict[str, callable] = {
    "center_crop_512": center_crop_512,
    "padded_resize_512": padded_resize_512,
    "five_crop_512": five_crop_512,
    "grayscale_center_crop_512": grayscale_center_crop_512,
    "clahe_center_crop_512": clahe_center_crop_512,
    "tile_224_average": _tile_224_average_wrapper,
}

ALL_STRATEGY_NAMES = list(STRATEGIES.keys())
