"""CrisperWhisper front end for verbatim transcription.

The roadmap explicitly calls out that vanilla Whisper can erase repetitions and
false starts. This wrapper therefore refuses known vanilla Whisper model ids and
defaults to nyrahealth's CrisperWhisper. For tests and offline development it
also accepts JSON token fixtures, so the rest of the pipeline can be exercised
without downloading ASR weights.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable
import wave


@dataclass
class VerbatimToken:
    word: str
    start: float | None = None
    end: float | None = None
    is_filler: bool = False
    is_stutter: bool = False
    source: str = "asr"
    profile_safe: bool = True

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "VerbatimToken":
        return cls(
            word=str(row.get("word", "")).strip(),
            start=_maybe_float(row.get("start")),
            end=_maybe_float(row.get("end")),
            is_filler=bool(row.get("is_filler", False)),
            is_stutter=bool(row.get("is_stutter", False)),
            source=str(row.get("source", "asr") or "asr"),
            profile_safe=bool(row.get("profile_safe", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data.get("source") == "asr":
            data.pop("source", None)
        if data.get("profile_safe") is True:
            data.pop("profile_safe", None)
        return data


def _maybe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _looks_like_vanilla_whisper(model_id: str) -> bool:
    low = model_id.lower()
    return low.startswith("openai/whisper") or low in {"whisper", "large-v3"}


def _normalise_word(word: str) -> str:
    return re.sub(r"^\W+|\W+$", "", word or "").lower()


def _pcm_rms(frame_bytes: bytes, sample_width: int) -> float:
    if not frame_bytes or sample_width <= 0:
        return 0.0
    values: list[int] = []
    for i in range(0, len(frame_bytes) - sample_width + 1, sample_width):
        raw = frame_bytes[i:i + sample_width]
        if sample_width == 1:
            values.append(raw[0] - 128)
        else:
            values.append(int.from_bytes(raw, "little", signed=True))
    if not values:
        return 0.0
    peak = 128.0 if sample_width == 1 else float((1 << (8 * sample_width - 1)) - 1)
    power = sum((sample / peak) ** 2 for sample in values) / len(values)
    return min(1.0, math.sqrt(power))


def _merge_segments(
    segments: list[tuple[float, float]],
    merge_gap_seconds: float,
) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in segments:
        if not merged or start - merged[-1][1] > merge_gap_seconds:
            merged.append((start, end))
        else:
            prev_start, _ = merged[-1]
            merged[-1] = (prev_start, end)
    return merged


def _alpha_label(index: int) -> str:
    label = ""
    n = max(1, int(index))
    while n:
        n, rem = divmod(n - 1, 26)
        label = chr(97 + rem) + label
    return label


class CrisperWhisperASR:
    """Lazy CrisperWhisper ASR wrapper.

    Parameters
    ----------
    model_id:
        Hugging Face model id. Defaults to ``CRISPERWHISPER_MODEL`` or
        ``nyrahealth/CrisperWhisper``.
    """

    FILLERS = {"uh", "um", "er", "erm", "ah", "hmm", "like"}

    def __init__(self, model_id: str | None = None, device: str | int | None = None):
        self.model_id = model_id or os.environ.get(
            "CRISPERWHISPER_MODEL", "nyrahealth/CrisperWhisper"
        )
        if _looks_like_vanilla_whisper(self.model_id):
            raise ValueError(
                "Use CrisperWhisper for verbatim stutter transcription; "
                "vanilla Whisper can delete disfluencies."
            )
        self.device = device if device is not None else os.environ.get("ASR_DEVICE", "cpu")
        self._pipe = None

    def _load_pipeline(self):
        if self._pipe is not None:
            return self._pipe
        try:
            from transformers import pipeline
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                "transformers is required to run CrisperWhisper ASR. "
                "Install requirements or pass a JSON token fixture."
            ) from exc

        kwargs: dict[str, Any] = {
            "model": self.model_id,
            "return_timestamps": "word",
            # Incremental, meta-device weight loading (needs `accelerate`) avoids
            # the transient 2x allocation that OOMs / segfaults on tight RAM.
            "model_kwargs": {"low_cpu_mem_usage": True},
        }
        if self.device != "cpu":
            kwargs["device"] = self.device
        self._pipe = pipeline("automatic-speech-recognition", **kwargs)
        return self._pipe

    def transcribe(self, audio_path: str | Path) -> list[dict[str, Any]]:
        """Return verbatim tokens as dictionaries.

        JSON fixtures may be either a list of token dicts or
        ``{"tokens": [...]}``. Text fixtures are split on whitespace and marked
        for obvious fillers/repetition fragments.
        """

        path = Path(audio_path)
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data.get("tokens", data) if isinstance(data, dict) else data
            return [VerbatimToken.from_mapping(row).to_dict() for row in rows]
        if path.suffix.lower() in {".txt", ".transcript"}:
            text = path.read_text(encoding="utf-8")
            return [tok.to_dict() for tok in self.tokens_from_text(text)]

        if os.environ.get("ASR_FORCE_AUDIO_FALLBACK", "").strip() == "1":
            return [tok.to_dict() for tok in self.tokens_from_audio_timing(path)]

        try:
            result = self._load_pipeline()(str(path))
        except Exception:
            fallback = self.tokens_from_audio_timing(path)
            if fallback:
                return [tok.to_dict() for tok in fallback]
            raise
        chunks = result.get("chunks") or result.get("segments") or []
        if chunks:
            return [tok.to_dict() for tok in self._tokens_from_chunks(chunks)]
        return [tok.to_dict() for tok in self.tokens_from_text(result.get("text", ""))]

    def _tokens_from_chunks(self, chunks: Iterable[dict[str, Any]]) -> list[VerbatimToken]:
        tokens: list[VerbatimToken] = []
        for chunk in chunks:
            word = str(chunk.get("text") or chunk.get("word") or "").strip()
            if not word:
                continue
            timestamp = chunk.get("timestamp") or (chunk.get("start"), chunk.get("end"))
            start, end = None, None
            if isinstance(timestamp, (list, tuple)) and len(timestamp) >= 2:
                start, end = _maybe_float(timestamp[0]), _maybe_float(timestamp[1])
            else:
                start, end = _maybe_float(chunk.get("start")), _maybe_float(chunk.get("end"))
            low = _normalise_word(word)
            tokens.append(
                VerbatimToken(
                    word=word,
                    start=start,
                    end=end,
                    is_filler=low in self.FILLERS or bool(chunk.get("is_filler", False)),
                    is_stutter=bool(chunk.get("is_stutter", False)) or word.endswith("-"),
                )
            )
        return tokens

    def tokens_from_audio_timing(self, audio_path: str | Path) -> list[VerbatimToken]:
        """Fallback tokenization from WAV timing when ASR is unavailable.

        This does not know the spoken words. It only marks speech regions with
        start/end timestamps so the detector can still find long pauses and
        prolonged regions in a microphone recording.
        """

        path = Path(audio_path)
        if path.suffix.lower() not in {".wav", ".wave"}:
            return []

        try:
            with wave.open(str(path), "rb") as wav:
                sample_rate = int(wav.getframerate())
                sample_width = int(wav.getsampwidth())
                channels = max(1, int(wav.getnchannels()))
                window_frames = max(1, int(sample_rate * 0.03))
                frame_index = 0
                windows: list[tuple[float, float, float]] = []
                while True:
                    data = wav.readframes(window_frames)
                    if not data:
                        break
                    frames_read = max(1, len(data) // max(sample_width * channels, 1))
                    start = frame_index / sample_rate
                    end = (frame_index + frames_read) / sample_rate
                    windows.append((start, end, _pcm_rms(data, sample_width)))
                    frame_index += frames_read
        except Exception:
            return []

        if not windows:
            return []

        rms_values = [rms for _, _, rms in windows]
        max_rms = max(rms_values)
        if max_rms < 0.01:
            return []
        # Voiced/unvoiced split relative to the recording's own noise floor and
        # peak. A fixed multiple of the *median* breaks when speech dominates the
        # clip (the usual case for a mic recording with only short pauses): the
        # median lands inside speech, so median*k exceeds the peak and nothing is
        # detected. Anchoring to (noise_floor, peak) stays correct whether the
        # clip is mostly silence or mostly speech.
        ordered = sorted(rms_values)
        noise_floor = ordered[max(0, int(len(ordered) * 0.15))]
        peak = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
        threshold = max(0.012, noise_floor + 0.18 * (peak - noise_floor))

        raw_segments: list[tuple[float, float]] = []
        current_start: float | None = None
        current_end: float | None = None
        for start, end, rms in windows:
            if rms >= threshold:
                if current_start is None:
                    current_start = start
                current_end = end
            elif current_start is not None and current_end is not None:
                raw_segments.append((current_start, current_end))
                current_start = None
                current_end = None
        if current_start is not None and current_end is not None:
            raw_segments.append((current_start, current_end))

        segments = [
            (start, end)
            for start, end in _merge_segments(raw_segments, merge_gap_seconds=0.16)
            if end - start >= 0.08
        ]
        return [
            VerbatimToken(
                word=f"speech_{_alpha_label(idx)}",
                start=round(start, 3),
                end=round(end, 3),
                source="audio_timing_fallback",
                profile_safe=False,
            )
            for idx, (start, end) in enumerate(segments, start=1)
        ]

    def tokens_from_text(self, text: str) -> list[VerbatimToken]:
        words = re.findall(r"[A-Za-z]+-?|[.,!?;:]", text or "")
        tokens: list[VerbatimToken] = []
        for word in words:
            low = _normalise_word(word)
            tokens.append(
                VerbatimToken(
                    word=word,
                    is_filler=low in self.FILLERS,
                    is_stutter=word.endswith("-"),
                )
            )
        return tokens
