"""CrisperWhisper front end for verbatim transcription.

The roadmap explicitly calls out that vanilla Whisper can erase repetitions and
false starts. This wrapper therefore refuses known vanilla Whisper model ids and
defaults to nyrahealth's CrisperWhisper. For tests and offline development it
also accepts JSON token fixtures, so the rest of the pipeline can be exercised
without downloading ASR weights.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable


@dataclass
class VerbatimToken:
    word: str
    start: float | None = None
    end: float | None = None
    is_filler: bool = False
    is_stutter: bool = False

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "VerbatimToken":
        return cls(
            word=str(row.get("word", "")).strip(),
            start=_maybe_float(row.get("start")),
            end=_maybe_float(row.get("end")),
            is_filler=bool(row.get("is_filler", False)),
            is_stutter=bool(row.get("is_stutter", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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

        result = self._load_pipeline()(str(path))
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
