# out_of_scope/ — audio/ASR code archived out of this repository's scope

This repository is the **text reformulation ("word") module** of the larger
Speech-AI system. Its job starts once text already exists: transcribed or
typed input, plus problematic phoneme/word information, in — a reformulated
sentence out. Producing that transcription and identifying the problematic
segments is the job of the separate **Audio Module**, which is not part of
this repository (see the top-level `README.md` for the full picture).

Earlier development in this repo grew audio-facing code directly alongside
the text-reformulation pipeline: a CrisperWhisper ASR wrapper, a rule-based
disfluency detector that operates on ASR word timestamps, and a browser
Speech-to-Text/Text-to-Speech UI layer. None of that is wrong or discarded —
it just belongs to the Audio Module's concern, not this one. As part of the
Stage 2 scope-narrowing pass (see `../DECISION_LOG.md`), it was moved here
rather than deleted, so the implementation and its test coverage are
preserved for whoever builds/maintains the Audio Module repository.

## What's here

| Path | What it was | Original location |
|---|---|---|
| `voice.py` | Browser-native STT (Web Speech API) / TTS (`speechSynthesis`) via injected HTML/JS, wired into `app.py`'s sidebar and result cards. | repo root |
| `profiling/asr.py` | `CrisperWhisperASR` — verbatim ASR wrapper (Hugging Face `transformers` pipeline) with a WAV-timing fallback (`tokens_from_audio_timing`) for when the ASR stack isn't installed. | `profiling/asr.py` |
| `profiling/detect.py` | Rule-based disfluency detector (repetition / block / prolongation / filler) that operates on ASR word timestamps. | `profiling/detect.py` |
| `profiling/config.py` | Copy of the live config loader, duplicated here (not moved) so this archived package still runs standalone. The live copy stays at `../profiling/config.py` because the text-reformulation module still needs it for profile/rewrite weights. | copy of `profiling/config.py` |
| `sample_stutter.json` | Test fixture: a hand-built verbatim-token JSON used to exercise the detector without needing a real CrisperWhisper model. | repo root |
| `tests/roadmap_test_audio.py` | The detector/ASR test cases extracted from `tests/roadmap_test.py`. | part of `tests/roadmap_test.py` |

## Status

**Not imported by the live app.** `app.py`, `profiling/__init__.py`, and
`tests/roadmap_test.py` no longer reference any file in this directory. The
code here is preserved as-is (not redesigned, not fixed, not updated) and is
runnable standalone:

```bash
DISABLE_DATAMUSE=1 python out_of_scope/tests/roadmap_test_audio.py
```

If/when the Audio Module becomes its own repository, this is the natural
starting point for it — including the one already-known issue: `HANDOFF.md`'s
pitfall list (in the main repo) notes that `st.iframe` in `voice.py` was never
verified against the pinned Streamlit version.

## What replaced the audio-ingestion UI in this repo

The "Voice / transcript profile update" panel (mic recording + CrisperWhisper
upload) that used to call into `asr.py`/`detect.py` was removed from `app.py`.
The **speaker difficulty profile itself** (`profiling/profile.py`,
`profiling/coldstart.py`) stayed in the live module — it's the representation
of "problematic phoneme/word information" that this module treats as an
*input*, currently populated by the user's manual self-report ("Phoneme
Profile — Stuttering Patterns" text fields). In the full Speech-AI pipeline,
that same profile-update path (`profile.update(session_events)`) is where the
Audio Module's disfluency-detection output would be fed in — the interface
was left intact; only this repo's own audio-capture UI was removed.
