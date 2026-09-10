"""
stage_lr/judge_pairs.py — the standard Claude-as-judge mechanism for
Stage LR data path (a), effective 2026-08-30. Replaces ad hoc/manual
judging (which was the bottleneck in batches 1-2) with a documented,
repeatable pipeline component: a general-purpose Claude call, blind to
any "expected" answer, judging exactly the three quality axes this
project's own reward design already scopes Claude to.

Two hard invariants, not just conventions:

  1. Claude judges MEANING, NATURALNESS, and GRAMMATICALITY only.
     Phoneme-avoidance is never a Claude judgment call — it is a
     computable fact, checked deterministically by phonetic.py's
     ARPAbet/onset matching (the same logic behind Matter 1's
     guardrails), enforced upstream of this file entirely:
     generate_pairs.py's candidates are only ever "found" by re-running
     the real reformulate() pipeline, whose own gate stack (phoneme
     match against profile.sounds, `_word_onset_hits`-equivalent
     checks) already rejected anything that fails phoneme-avoidance
     before this module ever sees a candidate. This module has no
     phoneme-related field or prompt language at all, by design — not
     an oversight to fix later.

  2. Judgments are blind. The prompt never states or implies what the
     "right" answer is, never reveals a prior verdict on the same
     pair, and never lets the model see (sentence, profile) pairs
     alongside their own already-known original human/Claude rating
     from the historical corpora these pairs were sourced from.

Usage: build a list of pair dicts (id, original_sentence,
difficulty_profile, flagged_word, candidate_A, candidate_B), call
judge_pairs_via_claude(pairs) to get back {id: {"preferred": "A"|"B"|
"tie", "reason": str}}. Batches internally (BATCH_SIZE items per
Claude call) to keep individual calls a manageable size, same practice
as the human-agreement ceiling check (`DECISION_LOG.md` 2026-08-30-N).

This module does not itself call the Anthropic API or spawn an agent —
there is no tool in this harness for a script to do that
programmatically. It prepares the exact prompt text the calling
session should send via a general-purpose Claude call (the Agent tool,
in this environment) and parses the JSON response back. See
`stage_lr/generate_pairs.py`'s batch runner for the calling pattern.
"""
from __future__ import annotations

import json

BATCH_SIZE = 25

JUDGE_INSTRUCTIONS = """You are acting as an independent judge for a speech accessibility tool. Some background: this tool rewrites text to be easier for a specific speaker to say out loud, by substituting a "hard" word with an easier alternative. The speaker has declared a "difficulty profile" — specific sounds, words, or phrases they personally find hard to pronounce. For each item below, a system already picked two CANDIDATE replacement words for one flagged word in a sentence (both candidates already passed automatic phoneme-avoidance filters — neither one contains the speaker's declared difficult sounds; you do not need to and should not judge phonetics/pronunciation at all). Your job is to judge, as a careful proofreader would, which candidate is the better replacement, purely on:
1. Meaning preservation (does it keep the sentence's original meaning/claim intact, not distort or contradict it)
2. Naturalness (does the resulting sentence read naturally, in-register, idiomatic)
3. Grammaticality (is the resulting sentence grammatically correct)

For each item, decide: is candidate_A better, candidate_B better, or are they about equally good/bad (a tie)? Give a short 1-2 sentence reason.

IMPORTANT: This is a blind judgment task. Do not search the filesystem, do not look for any other files or context, do not try to find "the right answer" anywhere — judge each item purely on its own merits from the data given.

Return your answer as a JSON array, one object per item, in this exact format:
[{"id": <int>, "preferred": "A"|"B"|"tie", "reason": "<short reason>"}, ...]

Output ONLY the JSON array (a ```json code block is fine), nothing else."""


def build_judge_prompt(pairs: list[dict]) -> str:
    """pairs: list of {"id": int, "original_sentence": str,
    "difficulty_profile": dict, "flagged_word": str, "candidate_A": str,
    "candidate_B": str}. No 'preferred'/'reason' fields — those don't
    exist yet, that's what this prompt is for."""
    payload = [
        {
            "id": p["id"],
            "original_sentence": p["original_sentence"],
            "difficulty_profile": p["difficulty_profile"],
            "flagged_word": p["flagged_word"],
            "candidate_A": p["candidate_A"],
            "candidate_B": p["candidate_B"],
        }
        for p in pairs
    ]
    return JUDGE_INSTRUCTIONS + "\n\nHere is the data (" + str(len(pairs)) + " items):\n\n```json\n" + \
        json.dumps(payload, indent=2) + "\n```"


def parse_judge_response(text: str) -> dict[int, dict]:
    """Extracts the JSON array from a Claude response (handles a
    ```json ... ``` fence or a bare array) and returns {id: {preferred,
    reason}}."""
    t = text.strip()
    if "```" in t:
        start = t.index("```")
        t = t[start + 3:]
        if t.lstrip().startswith("json"):
            t = t.lstrip()[4:]
        end = t.index("```")
        t = t[:end]
    data = json.loads(t)
    return {int(item["id"]): {"preferred": item["preferred"], "reason": item["reason"]} for item in data}


def batches(pairs: list[dict], size: int = BATCH_SIZE):
    for i in range(0, len(pairs), size):
        yield pairs[i:i + size]
