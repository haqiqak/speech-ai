"""
eval/pilot_app.py — Stage 7 human-evaluation pilot interface.

A separate, minimal Streamlit app — deliberately not part of app.py. This
is a research instrument, not a product feature: one pair at a time, four
short questions, no internal scores (SBERT similarity, difficulty
formulas, phoneme decisions) ever shown.

Design:
  - Reads the 20 curated pairs from eval/pilot_pairs.json (built by
    eval/pilot_select_pairs.py — never regenerated here).
  - Four fixed, anonymous participant IDs (P1-P4) — no login, no
    connection to the app's own single-profile system.
  - All 4 participants rate all 20 pairs (80 responses total) so results
    can be analyzed per-pair across raters, not just per-participant.
  - Presentation order of the 20 pairs, and which sentence (Original/
    Reformulated) is shown first within each pair, are both shuffled
    deterministically per participant (seeded on participant_id) — order
    counterbalancing to avoid a fixed primacy/recency bias, not identity-
    hiding: participants need to know which sentence is which to answer
    the meaning-preservation/naturalness/ease questions honestly, so both
    are always clearly labeled.
  - Every response is written to disk immediately (one row per pair, per
    participant) so no progress is lost if the app is closed early;
    reopening resumes at the first un-rated pair for that participant.

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

PARTICIPANT_IDS = ["P1", "P2", "P3", "P4"]

RESPONSE_FIELDS = [
    "participant_id", "pair_id", "presentation_order_index",
    "shown_first", "meaning_preservation", "naturalness",
    "speaking_ease", "preference", "diagnostic_tag", "timestamp",
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
    "Other",
]

st.set_page_config(page_title="Reformulation pilot", page_icon="📝", layout="centered")


@st.cache_resource
def load_pairs() -> list[dict]:
    data = json.loads(PAIRS_PATH.read_text(encoding="utf-8"))
    return data["pairs"]


def _response_path(participant_id: str) -> Path:
    return RESPONSES_DIR / f"{participant_id}.csv"


def _load_completed(participant_id: str) -> set[str]:
    path = _response_path(participant_id)
    if not path.exists():
        return set()
    with open(path, "r", newline="", encoding="utf-8") as f:
        return {row["pair_id"] for row in csv.DictReader(f)}


def _append_response(row: dict) -> None:
    path = _response_path(row["participant_id"])
    is_new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESPONSE_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def _participant_order(participant_id: str, pairs: list[dict]) -> list[dict]:
    """Deterministic per-participant shuffle of the 20 pairs — same
    inputs always produce the same order (reproducible, testable), but
    the order differs across participants (avoids a fixed order effect)."""
    rng = random.Random(f"pilot-order-{participant_id}")
    order = list(pairs)
    rng.shuffle(order)
    return order


def _shown_first(participant_id: str, pair_id: str) -> str:
    """Deterministically decide whether 'original' or 'reformulated' is
    displayed first for this (participant, pair) — counterbalances
    display position without hiding which sentence is which."""
    rng = random.Random(f"pilot-position-{participant_id}-{pair_id}")
    return rng.choice(["original", "reformulated"])


# ── Landing: pick participant ────────────────────────────────────────────
st.title("📝 Reformulation Pilot")

if "participant_id" not in st.session_state:
    st.session_state.participant_id = None

if st.session_state.participant_id is None:
    st.markdown(
        "Thank you for helping evaluate this system. You'll see **20 pairs** "
        "of sentences — an original and a rewritten version — and answer four "
        "short questions about each. It takes about 15–20 minutes. There are "
        "no right answers; we're interested in your honest reaction."
    )
    pid = st.selectbox("Select your participant ID (given to you by the study organizer):",
                        options=["— select —"] + PARTICIPANT_IDS)
    if pid != "— select —" and st.button("Start", type="primary"):
        st.session_state.participant_id = pid
        st.rerun()
    st.stop()

participant_id = st.session_state.participant_id
pairs = load_pairs()
ordered_pairs = _participant_order(participant_id, pairs)
completed = _load_completed(participant_id)
remaining = [p for p in ordered_pairs if p["pair_id"] not in completed]

st.caption(f"Participant: **{participant_id}**  ·  Completed: {len(completed)} / {len(pairs)}")

if not remaining:
    st.success("✅ All 20 pairs completed. Thank you for participating!")
    st.stop()

current = remaining[0]
current_index = ordered_pairs.index(current) + 1
first = _shown_first(participant_id, current["pair_id"])
if first == "original":
    top_label, top_text = "Sentence 1", current["original_text"]
    bottom_label, bottom_text = "Sentence 2", current["reformulated_text"]
    original_shown_as, reformulated_shown_as = "Sentence 1", "Sentence 2"
else:
    top_label, top_text = "Sentence 1", current["reformulated_text"]
    bottom_label, bottom_text = "Sentence 2", current["original_text"]
    original_shown_as, reformulated_shown_as = "Sentence 2", "Sentence 1"

st.progress(len(completed) / len(pairs))
st.markdown(f"#### Pair {current_index} of {len(pairs)}")

st.markdown(f"**{top_label}**")
st.info(top_text)
st.markdown(f"**{bottom_label}**")
st.info(bottom_text)

st.caption(
    f"For the questions below: **Original** = {original_shown_as}, "
    f"**Reformulated (rewritten)** = {reformulated_shown_as}."
)

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
    submitted = st.form_submit_button("Submit and continue", type="primary")

    if submitted:
        if meaning is None or naturalness is None or ease is None or preference is None:
            st.warning("Please answer all four required questions before continuing.")
        else:
            _append_response({
                "participant_id": participant_id,
                "pair_id": current["pair_id"],
                "presentation_order_index": current_index,
                "shown_first": first,
                "meaning_preservation": meaning,
                "naturalness": naturalness,
                "speaking_ease": EASE_OPTIONS[ease][0],
                "preference": preference,
                "diagnostic_tag": "" if diagnostic == "(not applicable / no issue)" else diagnostic,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            st.rerun()
