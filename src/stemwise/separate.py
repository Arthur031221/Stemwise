"""Stem separation with Demucs v4 six-stem (htdemucs_6s)."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import torch

from .audio import SAMPLE_RATE

MODEL_NAME = "htdemucs_6s"
STEMS = ("vocals", "drums", "bass", "guitar", "piano", "other")

Progress = Callable[[float], None]


def pick_device(prefer: str | None = None) -> str:
    if prefer:
        return prefer
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class Separator:
    def __init__(self, device: str | None = None, half: bool = False):
        self.device = pick_device(device)
        # fp16 autocast is about a third faster on CUDA but shifts quiet stems, so it is opt-in
        self.half = bool(half) and self.device == "cuda"
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from demucs.pretrained import get_model

            model = get_model(MODEL_NAME)
            model.to(self.device).eval()
            self._model = model
        return self._model

    def split(self, audio: np.ndarray, progress: Progress | None = None) -> dict[str, np.ndarray]:
        """Split (2, n) float32 audio at 44.1 kHz into the six stems."""
        from demucs.apply import apply_model

        model = self.model
        if audio.shape[0] == 1:
            audio = np.repeat(audio, 2, axis=0)
        mix = torch.from_numpy(audio)
        ref = mix.mean(0)
        mean, std = ref.mean(), ref.std() + 1e-8
        mix = (mix - mean) / std
        total = mix.shape[-1]
        segment = int(max(m.segment for m in getattr(model, "models", [model])) * SAMPLE_RATE)
        done = {"samples": 0}

        def on_segment(info: dict) -> None:
            if info["state"] == "end" and progress:
                done["samples"] = max(done["samples"], info["segment_offset"] + segment)
                progress(min(done["samples"] / total, 1.0))

        autocast = torch.autocast(self.device, dtype=torch.float16, enabled=self.half)
        with torch.inference_mode(), autocast:
            out = apply_model(
                model,
                mix[None].to(self.device),
                split=True,
                overlap=0.25,
                shifts=1,
                device=self.device,
                callback=on_segment,
                callback_arg={"segment_offset": 0},
            )[0]
        out = (out.float() * std + mean).cpu().numpy()
        return {name: out[i] for i, name in enumerate(model.sources)}
