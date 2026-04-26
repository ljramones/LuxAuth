"""Feature extractor wrappers for baseline comparison experiments."""

import math

import cv2
import numpy as np


def texture_baseline_v010(img_bytes: bytes, dim: int = 128) -> list[float]:
    """texture_baseline_v0.1.0 — original hand-crafted features.

    Wraps auth_common.imaging.compute_texture_embedding.
    """
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "imaging",
        str(Path(__file__).parent.parent.parent / "libs" / "auth_common" / "auth_common" / "imaging.py"),
    )
    imaging = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imaging)
    return imaging.compute_texture_embedding(img_bytes, dim=dim)


def texture_baseline_v020(img_bytes: bytes, dim: int = 256) -> list[float]:
    """texture_baseline_v0.2.0 — enhanced hand-crafted features with LBP and Gabor.

    Feature composition (256 dimensions):
    - Grayscale intensity histogram: 32 bins
    - Color channel histograms: 3×16 = 48 bins
    - Edge/gradient histogram: 32 bins
    - Local variance histogram: 16 bins
    - LBP histogram: 64 bins
    - Gabor filter response summaries: 64 values (8 orientations × 4 frequencies × 2 stats)

    Total: 256 dimensions, L2-normalized to unit length.
    """
    arr = np.frombuffer(img_bytes, dtype=np.uint8)
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

    # 4. Local variance histogram (16 bins)
    mean = cv2.blur(gray.astype(float), (7, 7))
    sqmean = cv2.blur((gray.astype(float)) ** 2, (7, 7))
    local_var = np.clip(sqmean - mean**2, 0, None)
    var_hist = np.histogram(local_var.flatten(), bins=16, range=(0, 5000))[0].astype(float)
    var_hist = var_hist / (var_hist.sum() + 1e-10)
    features.extend(var_hist.tolist())

    # 5. LBP-like histogram (64 bins)
    # Simple 8-neighbor LBP computed manually with OpenCV
    padded = cv2.copyMakeBorder(gray, 1, 1, 1, 1, cv2.BORDER_REFLECT)
    lbp = np.zeros_like(gray, dtype=np.uint8)
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]
    for bit, (dy, dx) in enumerate(offsets):
        neighbor = padded[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w]
        lbp |= ((neighbor >= gray).astype(np.uint8) << bit)
    # Use 64-bin histogram (uniform-ish quantization)
    lbp_hist = np.histogram(lbp.flatten(), bins=64, range=(0, 256))[0].astype(float)
    lbp_hist = lbp_hist / (lbp_hist.sum() + 1e-10)
    features.extend(lbp_hist.tolist())

    # 6. Gabor filter response summaries (8 orientations × 4 frequencies × 2 stats = 64)
    gabor_features: list[float] = []
    for theta_idx in range(8):
        theta = theta_idx * np.pi / 8
        for _freq_idx, wavelength in enumerate([4, 8, 16, 32]):
            kernel = cv2.getGaborKernel(
                ksize=(21, 21),
                sigma=4.0,
                theta=theta,
                lambd=float(wavelength),
                gamma=0.5,
                psi=0,
                ktype=cv2.CV_64F,
            )
            filtered = cv2.filter2D(gray.astype(float), cv2.CV_64F, kernel)
            gabor_features.append(float(np.mean(np.abs(filtered))))
            gabor_features.append(float(np.std(filtered)))

    # Normalize Gabor features to [0,1] range approximately
    gabor_arr = np.array(gabor_features)
    gabor_max = gabor_arr.max()
    if gabor_max > 0:
        gabor_arr = gabor_arr / gabor_max
    features.extend(gabor_arr.tolist())

    # Truncate or pad to target dim
    features = features[:dim]
    while len(features) < dim:
        features.append(0.0)

    # L2 normalize
    mag = math.sqrt(sum(x * x for x in features))
    if mag > 0:
        features = [x / mag for x in features]

    return features


EXTRACTORS = {
    "texture_baseline_v0.1.0": texture_baseline_v010,
    "texture_baseline_v0.2.0": texture_baseline_v020,
}
