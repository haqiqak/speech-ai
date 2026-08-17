"""
eval/pilot_app.py — Stage 7 human-evaluation pilot interface, v3.

A separate, minimal Streamlit app — deliberately not part of app.py. This
is a research instrument, not a product feature: one pair at a time,
four required short questions plus an optional diagnostic tag and an
optional free-text comment, no internal scores (SBERT similarity,
difficulty formulas, phoneme decisions, or whether the declared
difficulty was actually resolved) ever shown — the participant judges
ONLY meaning preservation, naturalness, speaking ease, and preference for
the wording itself, never whether the reformulation matched the hidden
difficulty profile. That question is answered automatically, separately,
in eval/pilot_pairs.json's profile_match field, and reported alongside
(never blended into) these ratings — see eval/pilot_analyze.py.

v3 (rebuilt per direct user review of v2, and of v2's own real first
pilot run): two changes from v2/v1, both fixing real problems found by
using the app, not guessed at:
  1. **Single participant, not four.** v2's mixed short/long/multi-
     sentence/paragraph design showed long sentences only changing a
     word or two — too little signal per item. v3 narrows to 30 short,
     natural, everyday sentences and one focused participant, rather
     than four participants rating a diluted set.
  2. **Original/Reformulated are now labeled directly on each box.**
     v2 labeled the two boxes "Sentence 1"/"Sentence 2" and relied on a
     separate caption below to say which was which — since presentation
     order is randomized per pair, "Sentence 1" meant Original for some
     pairs and Reformulated for others. The real v2 pilot run showed
     exactly this confusion: several free-text comments described the
     reformulated text's wording as if it were the original. Fixed by
     putting the actual "Original" / "Reformulated" label on each box,
     no indirection.

Design:
  - Reads the 30 curated pairs from eval/pilot_pairs.json (built by
    eval/pilot_select_pairs.py — never regenerated here): 18 global-
    sound-triggered, 5 declared-word-triggered, 4 word-specific-pattern-
    triggered, 3 multi-difficulty — all short, single, natural-register
    sentences.
  - One fixed participant ("P1" internally, for schema continuity with
    v2's analysis tooling) — no selection screen, starts immediately.
  - Presentation order of the 30 pairs, and which sentence (Original/
    Reformulated) is shown first on screen, are both shuffled
    deterministically (seeded) — order counterbalancing to avoid a fixed
    primacy/recency bias, not identity-hiding: both are always clearly
    labeled, per the fix above.
  - Every response is written to disk immediately (one row per pair) so
    no progress is lost if the app is closed early; reopening resumes at
    the first un-rated pair.

Run:
    streamlit run eval/pilot_app.py
"""

from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PAIRS_PATH = ROOT / "eval" / "pilot_pairs.json"
RESPONSES_DIR = ROOT / "eval" / "pilot_responses"
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

PARTICIPANT_ID = "P1"  # single-user pilot — fixed, not selected

RESPONSE_FIELDS = [
    "participant_id", "pair_id", "presentation_order_index",
    "shown_first", "meaning_preservation", "naturalness",
    "speaking_ease", "preference", "diagnostic_tag", "comment", "timestamp",
]

EASE_OPTIONS = [
    (-2, "Much harder to say"),
    (-1, "Somewhat harder to say"),
    (0, "About the same"),
    (1, "Somewhat easier to say"),
    (2, "Much easier to say"),
]

DIAGNOSTIC_OPTIONS = [
    "Meaning changed",
    "Sounds unnatural",
    "Too much changed",
    "Reformulation does not seem easier",
    "Original sentence itself was confusing or ungrammatical",
    "Other",
]

st.set_page_config(page_title="Reformulation pilot", page_icon="📝", layout="centered")


@st.cache_resource
def load_pairs() -> list[dict]:
    data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
    return data["pairs"]


def _response_path() -> Path:
    return RESPONSES_DIR / f"{PARTICIPANT_ID}.csv"


def _load_completed() -> set[str]:
    path = _response_path()
    if not path.exists():
        return set()
    with open(path, "r", newline="", encoding="utf-8") as f:
        return {row["pair_id"] for row in csv.DictReader(f)}


def _append_response(row: dict) -> None:
    path = _response_path()
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESPONSE_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def _pair_order(pairs: list[dict]) -> list[dict]:
    """Deterministic shuffle of the 30 pairs — reproducible, not a fixed
    reading order (avoids a fixed order effect across the session)."""
    rng = random.Random("pilot-v3-order")
    order = list(pairs)
    rng.shuffle(order)
    return order


def _shown_first(pair_id: str) -> str:
    """Deterministically decide whether Original or Reformulated is
    displayed first for this pair — counterbalances display position.
    Both are always labeled directly (see module docstring's v3 fix), so
    this affects reading order only, never which sentence is identifiable."""
    rng = random.Random(f"pilot-v3-position-{pair_id}")
    return rng.choice(["original", "reformulated"])


# ── Start immediately — single participant, no selection screen ────────────
st.title("📝 Reformulation Pilot")

pairs = load_pairs()
ordered_pairs = _pair_order(pairs)
completed = _load_completed()
remaining = [p for p in ordered_pairs if p["pair_id"] not in completed]

st.caption(f"Completed: {len(completed)} / {len(pairs)}")

if not remaining:
    st.success(f"✅ All {len(pairs)} pairs completed. Thank you for participating!")
    st.stop()

if not completed:
    st.markdown(
        f"Thank you for helping evaluate this system. You'll see **{len(pairs)} pairs** "
        "of sentences — an original and a rewritten version, both clearly labeled — and "
        "answer four short questions about each. It takes about 15–20 minutes. Judge only "
        "the wording itself: does it mean the same thing, does it sound natural, would it be "
        "easier to say out loud. There are no right answers; we're interested in your honest "
        "reaction."
    )

current = remaining[0]
current_index = ordered_pairs.index(current) + 1
first = _shown_first(current["pair_id"])
if first == "original":
    top_text, bottom_text = current["original_text"], current["reformulated_text"]
else:
    top_text, bottom_text = current["reformulated_text"], current["original_text"]

st.progress(len(completed) / len(pairs))
st.markdown(f"#### Pair {current_index} of {len(pairs)}")

st.markdown("**Original**" if first == "original" else "**Reformulated**")
st.info(top_text)
st.markdown("**Reformulated**" if first == "original" else "**Original**")
st.info(bottom_text)

with st.form(key=f"form_{current['pair_id']}"):
    meaning = st.radio(
        "Does the reformulated sentence preserve the meaning of the original sentence?",
        options=[1, 2, 3, 4, 5],
        format_func=lambda v: {1: "1 — Meaning is completely different", 3: "3 — Roughly the same meaning",
                                5: "5 — Meaning is fully preserved"}.get(v, str(v)),
        horizontal=True, index=None,
    )
    naturalness = st.radio(
        "How natural does the reformulated sentence sound, as something a person would normally say?",
        options=[1, 2, 3, 4, 5],
        format_func=lambda v: {1: "1 — Very unnatural / awkward", 3: "3 — Somewhat natural",
                                5: "5 — Completely natural"}.get(v, str(v)),
        horizontal=True, index=None,
    )
    ease = st.radio(
        "Compared with the original sentence, how easy would you expect the reformulated "
        "sentence to be to SAY OUT LOUD? (Judge the wording itself — not your own speech.)",
        options=list(range(len(EASE_OPTIONS))),
        format_func=lambda i: EASE_OPTIONS[i][1],
        horizontal=False, index=None,
    )
    preference = st.radio(
        "If you had to say one of these two sentences, which would you prefer?",
        options=["Original", "Reformulated", "No preference"],
        horizontal=True, index=None,
    )
    diagnostic = st.radio(
        "Optional — if you didn't prefer the reformulated sentence, what was the main issue?",
        options=["(not applicable / no issue)"] + DIAGNOSTIC_OPTIONS,
        index=0,
    )
    comment = st.text_area(
        "Optional — anything else you'd like to explain about this pair?",
        placeholder="Type here if you'd like to say more…",
    )
    submitted = st.form_submit_button("Submit and continue", type="primary")

    if submitted:
        if meaning is None or naturalness is None or ease is None or preference is None:
            st.warning("Please answer all four required questions before continuing.")
        else:
            _append_response({
                "participant_id": PARTICIPANT_ID,
                "pair_id": current["pair_id"],
                "presentation_order_index": current_index,
                "shown_first": first,
                "meaning_preservation": meaning,
                "naturalness": naturalness,
                "speaking_ease": EASE_OPTIONS[ease][0],
                "preference": preference,
                "diagnostic_tag": "" if diagnostic == "(not applicable / no issue)" else diagnostic,
                "comment": comment.strip(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            st.rerun()
