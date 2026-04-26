"""Image processing utilities for the authentication pipeline."""

from __future__ import annotations

import hashlib
import io
import math
from typing import Any

import numpy as np

try:
    from PIL import ExifTags, Image
except ImportError:  # pragma: no cover - exercised only in incomplete local dev environments
    ExifTags = None  # type: ignore[assignment]
    Image = None  # type: ignore[assignment]

SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF", "BMP"}
MIN_DIMENSION = 64  # minimum width or height


def validate_image(data: bytes) -> dict[str, Any]:
    """Validate image data and return metadata.

    Returns dict with keys: valid, width, height, image_format, color_mode,
    sha256_checksum, file_size_bytes, issues.
    Raises ValueError if data is empty.
    """
    if not data:
        return {
            "valid": False,
            "issues": ["EMPTY_FILE"],
            "file_size_bytes": 0,
        }

    if Image is None:
        return {
            "valid": False,
            "issues": ["PILLOW_NOT_INSTALLED"],
            "file_size_bytes": len(data),
            "sha256_checksum": hashlib.sha256(data).hexdigest(),
        }

    sha256 = hashlib.sha256(data).hexdigest()
    result: dict[str, Any] = {
        "file_size_bytes": len(data),
        "sha256_checksum": sha256,
        "issues": [],
    }

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # verify integrity
        # Re-open after verify (verify closes the file)
        img = Image.open(io.BytesIO(data))
    except Exception:
        result["valid"] = False
        result["issues"].append("DECODE_FAILED")
        return result

    fmt = img.format or "UNKNOWN"
    if fmt not in SUPPORTED_FORMATS:
        result["valid"] = False
        result["issues"].append(f"UNSUPPORTED_FORMAT:{fmt}")
        return result

    w, h = img.size
    result.update({
        "width": w,
        "height": h,
        "image_format": fmt,
        "color_mode": img.mode,
    })

    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        result["valid"] = False
        result["issues"].append("IMAGE_TOO_SMALL")
        return result

    result["valid"] = True
    return result


def compute_quality_metrics(data: bytes) -> dict[str, Any]:
    """Compute real image quality metrics.

    Returns sharpness_score, exposure_score, glare_score, quality_status, issues.
    """
    import cv2

    issues: list[str] = []

    try:
        arr = np.frombuffer(data, dtype=np.uint8)
        img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return {
                "sharpness_score": 0.0,
                "exposure_score": 0.0,
                "glare_score": 1.0,
                "quality_status": "FAIL",
                "issues": ["DECODE_FAILED"],
            }
    except Exception:
        return {
            "sharpness_score": 0.0,
            "exposure_score": 0.0,
            "glare_score": 1.0,
            "quality_status": "FAIL",
            "issues": ["DECODE_FAILED"],
        }

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Sharpness: variance of Laplacian, normalized to 0-1
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    # Normalize: typical sharp image has var > 100, blurry < 20
    sharpness_score = min(1.0, laplacian_var / 200.0)

    # Exposure: mean luminance, ideal around 128
    mean_lum = float(gray.mean())
    # Score peaks at 128, falls off toward 0 and 255
    exposure_score = 1.0 - abs(mean_lum - 128.0) / 128.0
    exposure_score = max(0.0, min(1.0, exposure_score))

    # Glare: percentage of pixels that are very bright (>240) and low saturation
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    bright_mask = hsv[:, :, 2] > 240
    low_sat_mask = hsv[:, :, 1] < 30
    glare_pixels = np.count_nonzero(bright_mask & low_sat_mask)
    total_pixels = h * w
    glare_score = glare_pixels / total_pixels if total_pixels > 0 else 0.0

    # Underexposure: mean luminance < 40
    if mean_lum < 40:
        issues.append("UNDEREXPOSED")

    # Overexposure: mean luminance > 220
    if mean_lum > 220:
        issues.append("OVEREXPOSED")

    # Low sharpness
    if sharpness_score < 0.15:
        issues.append("LOW_SHARPNESS")

    # Excessive glare
    if glare_score > 0.15:
        issues.append("EXCESSIVE_GLARE")

    # Resolution check
    if h < MIN_DIMENSION or w < MIN_DIMENSION:
        issues.append("IMAGE_TOO_SMALL")

    quality_status = "PASS" if not issues else "FAIL"

    return {
        "sharpness_score": round(sharpness_score, 4),
        "exposure_score": round(exposure_score, 4),
        "glare_score": round(glare_score, 4),
        "quality_status": quality_status,
        "issues": issues,
    }


def normalize_image(data: bytes, target_size: int = 512) -> bytes:
    """Normalize an image: EXIF orientation, RGB, center-crop to square, resize.

    Returns PNG bytes.
    """
    if Image is None:
        raise RuntimeError("Pillow is required to normalize images")

    img = Image.open(io.BytesIO(data))

    # Apply EXIF orientation
    try:
        for orientation_tag in ExifTags.TAGS:
            if ExifTags.TAGS[orientation_tag] == "Orientation":
                break
        exif = img._getexif()
        if exif and orientation_tag in exif:
            orientation = exif[orientation_tag]
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    except (AttributeError, KeyError):
        pass

    # Convert to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Center crop to square
    w, h = img.size
    short_side = min(w, h)
    left = (w - short_side) // 2
    top = (h - short_side) // 2
    img = img.crop((left, top, left + short_side, top + short_side))

    # Resize to target
    img = img.resize((target_size, target_size), Image.LANCZOS)

    # Save as PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def compute_texture_embedding(data: bytes, dim: int = 128) -> list[float]:
    """Compute a deterministic baseline texture embedding from normalized image bytes.

    This is NOT a trained ML model. It extracts hand-crafted texture features:
    - Grayscale intensity histogram (32 bins)
    - Color channel histograms (3x16 = 48 bins)
    - Edge density via gradient histogram (32 bins)
    - Local variance features (16 bins)

    Total: 128 dimensions, normalized to unit length.
    """
    import cv2

    arr = np.frombuffer(data, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        # Return zero vector if decode fails
        return [0.0] * dim

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    features: list[float] = []

    # 1. Grayscale histogram (32 bins)
    gray_hist = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten()
    gray_hist = gray_hist / (gray_hist.sum() + 1e-10)
    features.extend(gray_hist.tolist())

    # 2. Color histograms (3 channels x 16 bins = 48)
    for ch in range(3):
        ch_hist = cv2.calcHist([img_bgr], [ch], None, [16], [0, 256]).flatten()
        ch_hist = ch_hist / (ch_hist.sum() + 1e-10)
        features.extend(ch_hist.tolist())

    # 3. Edge/gradient histogram (32 bins)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    mag_hist = np.histogram(magnitude.flatten(), bins=32, range=(0, 500))[0].astype(float)
    mag_hist = mag_hist / (mag_hist.sum() + 1e-10)
    features.extend(mag_hist.tolist())

    # 4. Local variance features (16 bins)
    # Compute local variance using box filter
    mean = cv2.blur(gray.astype(float), (7, 7))
    sqmean = cv2.blur((gray.astype(float))**2, (7, 7))
    local_var = np.clip(sqmean - mean**2, 0, None)
    var_hist = np.histogram(local_var.flatten(), bins=16, range=(0, 5000))[0].astype(float)
    var_hist = var_hist / (var_hist.sum() + 1e-10)
    features.extend(var_hist.tolist())

    # Truncate or pad to target dim
    features = features[:dim]
    while len(features) < dim:
        features.append(0.0)

    # Normalize to unit length
    mag = math.sqrt(sum(x * x for x in features))
    if mag > 0:
        features = [x / mag for x in features]

    return features


def compute_texture_embedding_v2(data: bytes, dim: int = 256) -> list[float]:
    """Compute enhanced texture embedding with LBP and Gabor features.

    texture_baseline_v0.2.0: 256-dimensional hand-crafted feature vector.

    Features (256 total):
    - Grayscale intensity histogram (32 bins)
    - Color channel histograms (3×16 = 48 bins)
    - Edge/gradient histogram (32 bins)
    - Local variance features (16 bins)
    - LBP histogram (64 bins)
    - Gabor filter response summaries (8 orientations × 4 frequencies × 2 stats = 64)

    Normalized to unit length.
    """
    import cv2

    arr = np.frombuffer(data, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return [0.0] * dim

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    features: list[float] = []

    # 1. Grayscale histogram (32 bins)
    gray_hist = cv2.calcHist([gray], [0], None, [32], [0, 256]).flatten()
    gray_hist = gray_hist / (gray_hist.sum() + 1e-10)
    features.extend(gray_hist.tolist())

    # 2. Color histograms (3×16 = 48 bins)
    for ch in range(3):
        ch_hist = cv2.calcHist([img_bgr], [ch], None, [16], [0, 256]).flatten()
        ch_hist = ch_hist / (ch_hist.sum() + 1e-10)
        features.extend(ch_hist.tolist())

    # 3. Edge/gradient histogram (32 bins)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    mag_hist = np.histogram(magnitude.flatten(), bins=32, range=(0, 500))[0].astype(float)
    mag_hist = mag_hist / (mag_hist.sum() + 1e-10)
    features.extend(mag_hist.tolist())

    # 4. Local variance features (16 bins)
    mean_img = cv2.blur(gray.astype(float), (7, 7))
    sqmean = cv2.blur((gray.astype(float)) ** 2, (7, 7))
    local_var = np.clip(sqmean - mean_img**2, 0, None)
    var_hist = np.histogram(local_var.flatten(), bins=16, range=(0, 5000))[0].astype(float)
    var_hist = var_hist / (var_hist.sum() + 1e-10)
    features.extend(var_hist.tolist())

    # 5. LBP histogram (64 bins)
    padded = cv2.copyMakeBorder(gray, 1, 1, 1, 1, cv2.BORDER_REFLECT)
    lbp = np.zeros_like(gray, dtype=np.uint8)
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    for bit, (dy, dx) in enumerate(offsets):
        neighbor = padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        lbp |= (neighbor >= gray).astype(np.uint8) << bit
    lbp_hist = np.histogram(lbp.flatten(), bins=64, range=(0, 256))[0].astype(float)
    lbp_hist = lbp_hist / (lbp_hist.sum() + 1e-10)
    features.extend(lbp_hist.tolist())

    # 6. Gabor filter responses (8 orientations × 4 frequencies × 2 stats = 64)
    gabor_features: list[float] = []
    for theta_idx in range(8):
        theta = theta_idx * np.pi / 8
        for wavelength in [4, 8, 16, 32]:
            kernel = cv2.getGaborKernel(
                ksize=(21, 21), sigma=4.0, theta=theta,
                lambd=float(wavelength), gamma=0.5, psi=0, ktype=cv2.CV_64F,
            )
            filtered = cv2.filter2D(gray.astype(float), cv2.CV_64F, kernel)
            gabor_features.append(float(np.mean(np.abs(filtered))))
            gabor_features.append(float(np.std(filtered)))

    gabor_arr = np.array(gabor_features)
    gabor_max = gabor_arr.max()
    if gabor_max > 0:
        gabor_arr = gabor_arr / gabor_max
    features.extend(gabor_arr.tolist())

    # Truncate or pad
    features = features[:dim]
    while len(features) < dim:
        features.append(0.0)

    # L2 normalize
    mag = math.sqrt(sum(x * x for x in features))
    if mag > 0:
        features = [x / mag for x in features]

    return features
