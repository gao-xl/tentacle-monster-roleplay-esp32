"""
One-Euro Filter (1€ Filter) for YOLO-Pose 26 Temporal Keypoint Smoothing (v4.0)
Eliminates high-frequency frame jitter and occlusion snap jumps:
- Low-speed motion: Strong smoothing (minimizes jitter)
- High-speed motion: Low smoothing (minimizes phase lag/delay)
Reference: Casiez et al., CHI 2012.
"""

import math
import time
import numpy as np
from typing import Optional, List


class LowPassFilter:
    def __init__(self, alpha: float = 0.5):
        self._alpha = alpha
        self._hatx_prev = 0.0
        self._initialized = False

    def filter(self, x: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self._alpha = alpha
        if not self._initialized:
            self._hatx_prev = x
            self._initialized = True
            return x
        hatx = self._alpha * x + (1.0 - self._alpha) * self._hatx_prev
        self._hatx_prev = hatx
        return hatx

    def reset(self):
        self._initialized = False


class OneEuroFilter1D:
    def __init__(self, mincutoff: float = 1.0, beta: float = 0.007, dcutoff: float = 1.0):
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.xfilt = LowPassFilter()
        self.dxfilt = LowPassFilter()
        self.tprev: Optional[float] = None
        self.xprev: Optional[float] = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        if timestamp is None:
            timestamp = time.time()
        if self.tprev is None:
            self.tprev = timestamp
            self.xprev = x
            return x

        dt = max(1e-4, timestamp - self.tprev)
        self.tprev = timestamp

        # Compute derivative (speed)
        dx = (x - self.xprev) / dt
        edx = self.dxfilt.filter(dx, self._alpha(self.dcutoff, dt))
        self.xprev = x

        # Adaptive cutoff frequency based on speed
        cutoff = self.mincutoff + self.beta * abs(edx)
        return self.xfilt.filter(x, self._alpha(cutoff, dt))

    def reset(self):
        self.tprev = None
        self.xprev = None
        self.xfilt.reset()
        self.dxfilt.reset()


class Skeleton26OneEuroFilter:
    """Applies individual 1D One-Euro filters to (X, Y) of all 26 dense pose keypoints."""

    def __init__(self, num_kpts: int = 26, mincutoff: float = 1.2, beta: float = 0.05):
        self.num_kpts = num_kpts
        self.filters_x = [OneEuroFilter1D(mincutoff, beta) for _ in range(num_kpts)]
        self.filters_y = [OneEuroFilter1D(mincutoff, beta) for _ in range(num_kpts)]

    def filter_keypoints(self, kpts: np.ndarray, timestamp: Optional[float] = None) -> np.ndarray:
        """
        kpts: np.ndarray of shape (N, 3) where [:, 0]=x, [:, 1]=y, [:, 2]=conf
        """
        if timestamp is None:
            timestamp = time.time()

        smooth_kpts = kpts.copy()
        n = min(len(kpts), self.num_kpts)
        for i in range(n):
            if kpts[i, 2] > 0.25: # Only filter valid detected points
                smooth_kpts[i, 0] = self.filters_x[i].filter(kpts[i, 0], timestamp)
                smooth_kpts[i, 1] = self.filters_y[i].filter(kpts[i, 1], timestamp)
            else:
                self.filters_x[i].reset()
                self.filters_y[i].reset()

        return smooth_kpts

    def reset(self):
        for fx, fy in zip(self.filters_x, self.filters_y):
            fx.reset()
            fy.reset()
