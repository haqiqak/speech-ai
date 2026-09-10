"""
stage_lr/generate_pairs.py — Stage LR data path (a), phase 1: for each
substitution-tier record in eval/r50_dataset/labeled_dataset.json,
attempt to produce a genuine second candidate for the SAME (sentence,
profile, flagged word) — the pipeline's own real runner-up, not an
invented one.

Method (reuses production code, no candidate-generation logic
reimplemented): the record's real profile is reconstructed from the
raw harvest file behind it (r40_change_audit_data.json /
r47_fresh_sample_results.json / r48_v3_verification_results.json —
labeled_dataset.json itself drops the profile field, these don't).
reformulate._raw_candidates is then wrapped, for one call only, to
exclude the lemma of the already-rated replacement from the candidate
pool handed to the SAME unmodified reformulate.reformulate() call —
every gate (antonym/phoneme/duplicate/blocklist/etc.) still runs
exactly as it does in production; this only changes what's available
to choose from, so whatever survives is a real, pipeline-approved
runner-up, not a hand-picked one.

Read-only against the frozen pipeline: no file outside stage_lr/ is
modified; the monkeypatch is applied and reverted within one call.

    DISABLE_DATAMUSE=1 python stage_lr/generate_pairs.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("DISABLE_DATAMUSE", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval"))

import paths  # noqa: F401,E402
import reformulate  # noqa: E402
from difficulty_profile import DifficultyProfile  # noqa: E402
from grammar import lemmatize, pos_tag, word_tokenize  # noqa: E402
from ceiling_probe_r40 import PROFILES as R40_PROFILES  # noqa: E402

OUT_PATH = ROOT / "stage_lr" / "data" / "lr1_candidate_generation_log.json"

LABELED_DATASET = ROOT / "eval" / "r50_dataset" / "labeled_dataset.json"
R40_RAW = ROOT / "eval" / "r40_change_audit_data.json"
R47_RAW = ROOT / "eval" / "r47_fresh_sample_results.json"
R48_RAW = ROOT / "eval" / "r48_v3_verification_results.json"


def _build_r40_style_profile(profile_name: str) -> DifficultyProfile:
    spec = R40_PROFILES[profile_name]
    p = DifficultyProfile(profile_name=f"__lr1_{profile_name}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    for ph in spec.get("phrases", []):
        p.add_phrase(ph, source="user_typed")
    return p


def _build_r47_style_profile(item_id: str, sounds: list[str]) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__lr1_r47_{item_id}__")
    for s in sounds:
        p.add_sound(s, source="user_typed")
    return p


def load_profile_index() -> dict[str, list[dict]]:
    """sentence-text -> LIST of candidate profile entries (each carrying the
    original_word/replacement_word it actually produced), since R40's own
    harvest tests most sentences under multiple (up to 4) profiles — a
    plain one-per-text mapping silently picks the wrong profile for
    36 of 41 R40 sentences (confirmed by direct count, not assumed).
    Callers must pick the entry whose (original_word, replacement_word)
    matches the specific record being reconstructed, not just the first
    or last one for that sentence text."""
    index: dict[str, list[dict]] = {}

    r40 = json.loads(R40_RAW.read_text(encoding="utf-8"))
    for c in r40["changes"]:
        text = c["original_sentence"]
        pname = c["profile"]
        index.setdefault(text, []).append({
            "profile": _build_r40_style_profile(pname),
            "profile_spec": {"name": pname, **R40_PROFILES[pname]},
            "source": "r40_change_audit_data.json",
            "original_word": c["original_word"],
            "replacement_word": c["replacement_word"],
        })

    r47 = json.loads(R47_RAW.read_text(encoding="utf-8"))
    for r in r47["results"]:
        text = r["original_text"]
        sounds = r["sounds"]
        # R47 has no per-word original/replacement recorded at this level —
        # only one profile per sentence exists here (id-keyed, not
        # multi-profile like R40), so no ambiguity to resolve.
        index.setdefault(text, []).append({
            "profile": _build_r47_style_profile(r["id"], sounds),
            "profile_spec": {"name": r["id"], "sounds": sounds, "words": [], "phrases": []},
            "source": "r47_fresh_sample_results.json",
            "original_word": None,
            "replacement_word": None,
        })

    r48 = json.loads(R48_RAW.read_text(encoding="utf-8"))
    for r in r48["results"]:
        text = r["original_text"]
        pname = r["profile"]
        index.setdefault(text, []).append({
            "profile": _build_r40_style_profile(pname),
            "profile_spec": {"name": pname, **R40_PROFILES[pname]},
            "source": "r48_v3_verification_results.json",
            "original_word": None,
            "replacement_word": None,
        })

    return index


def resolve_profile_entry(record: dict, candidates: list[dict]) -> tuple[dict | None, str]:
    """Picks the candidate profile entry that actually produced this
    record's own changed_word_pair, verified, not assumed. Returns
    (entry_or_None, note)."""
    pair = record.get("changed_word_pair")
    if pair is None:
        pair = _reconstruct_changed_word_pair(record["original_text"], record["reformulated_text"])
    if pair is None:
        return None, "no changed_word_pair to verify against"
    orig_word, replacement = pair

    verified = [c for c in candidates
                if c["original_word"] and c["original_word"].lower() == orig_word.lower()
                and c["replacement_word"].lower() == replacement.lower()]
    if len(verified) == 1:
        return verified[0], "verified (unique match on original/replacement word)"
    if len(verified) > 1:
        return verified[0], f"verified but ambiguous ({len(verified)} identical matches — using first)"

    # No per-word info to verify against (R47/R48) — only safe when there's
    # exactly one candidate profile for this sentence text at all.
    unverifiable = [c for c in candidates if c["original_word"] is None]
    if unverifiable and len(candidates) == 1:
        return unverifiable[0], "unverified (R47/R48 source has no per-word record) but only one candidate profile exists for this sentence"
    if unverifiable:
        return None, f"unverifiable: {len(candidates)} candidate profiles exist for this sentence text and no per-word record to disambiguate"

    return None, f"changed_word_pair {pair!r} matches none of {len(candidates)} candidate profile entries for this sentence"


def _find_position(tokens: list[str], word: str) -> int | None:
    wl = word.lower()
    for i, t in enumerate(tokens):
        if t.lower() == wl:
            return i
    return None


def _reconstruct_changed_word_pair(original_text: str, reformulated_text: str) -> list[str] | None:
    """Some records (R47) don't store changed_word_pair explicitly, only
    the two full sentences. Reconstructed here by finding the first
    positional token mismatch — real reconstruction from the record's
    own data, not a guess, since these are known single-substitution
    cases (granularity == "substitution")."""
    orig_tokens = word_tokenize(original_text)
    new_tokens = word_tokenize(reformulated_text)
    if len(orig_tokens) != len(new_tokens):
        return None
    for a, b in zip(orig_tokens, new_tokens):
        if a.lower() != b.lower():
            return [a, b]
    return None


def attempt_second_candidate(record: dict, profile_entry: dict) -> dict:
    """Returns a result dict describing what happened for this record —
    always, whether or not a second candidate was actually found, so the
    running count is honest rather than only counting successes."""
    original_sentence = record["original_text"]
    pair = record.get("changed_word_pair")
    if pair is None:
        pair = _reconstruct_changed_word_pair(record["original_text"], record["reformulated_text"])
    if pair is None:
        return {"uid": record["uid"], "outcome": "no_second_candidate",
                "reason": "changed_word_pair not recorded and could not be reconstructed "
                          "(sentences differ in token count, not a single-word swap)"}
    original_word, used_replacement = pair
    profile = profile_entry["profile"]

    tokens = word_tokenize(original_sentence)
    tags = reformulate._correct_predicate_adjective_tags(tokens, pos_tag(tokens))
    pos = _find_position(tokens, original_word)
    if pos is None:
        return {"uid": record["uid"], "outcome": "skipped",
                "reason": f"could not locate '{original_word}' as a token in the reconstructed sentence"}

    tag = tags[pos][1]
    used_lemma = lemmatize(used_replacement, tag).lower()

    real_raw_candidates = reformulate._raw_candidates

    def _filtered_raw_candidates(engine, lemma, pos_tag_str, original_word_, top_k, context=None):
        cands = real_raw_candidates(engine, lemma, pos_tag_str, original_word_, top_k, context=context)
        return [c for c in cands if c.lower() != used_lemma]

    reformulate._raw_candidates = _filtered_raw_candidates
    try:
        result = reformulate.reformulate(original_sentence, profile)
    finally:
        reformulate._raw_candidates = real_raw_candidates

    match = None
    for ch in result.get("changes", []):
        if ch.get("source") == "substitution" and ch.get("original", "").lower() == original_word.lower():
            match = ch
            break

    if match is None:
        return {"uid": record["uid"], "outcome": "no_second_candidate",
                "reason": f"pipeline status={result.get('status')} — no substitution survived at that "
                          f"position once the original candidate was excluded (likely escalated, "
                          f"skipped, or the original was the only viable candidate)"}

    candidate_b = match["replacement"]
    if candidate_b.lower() == used_replacement.lower():
        return {"uid": record["uid"], "outcome": "no_second_candidate",
                "reason": "pipeline re-selected the same replacement even after exclusion "
                          "(inflection/case variant only, not a genuinely different word)"}

    candidate_b_sentence = original_sentence.replace(original_word, candidate_b, 1) \
        if original_word in original_sentence else None
    # Prefer the pipeline's own rebuilt sentence when the naive replace() above
    # wouldn't be reliable (case/inflection differences) — reformulate() already
    # rebuilds the full sentence correctly.
    candidate_b_sentence = result["reformulated_text"]

    return {
        "uid": record["uid"],
        "outcome": "second_candidate_found",
        "original_sentence": original_sentence,
        "original_word": original_word,
        "profile_spec": profile_entry["profile_spec"],
        "profile_source_file": profile_entry["source"],
        "candidate_a": used_replacement,
        "candidate_a_sentence": record["reformulated_text"],
        "candidate_b": candidate_b,
        "candidate_b_sentence": candidate_b_sentence,
    }


def main() -> None:
    data = json.loads(LABELED_DATASET.read_text(encoding="utf-8"))
    records = data["records"]
    profile_index = load_profile_index()

    results = []
    counts = {"total": len(records), "not_substitution": 0, "profile_unrecoverable": 0,
              "attempt_error": 0, "no_second_candidate": 0, "second_candidate_found": 0}

    for i, r in enumerate(records, 1):
        if r.get("granularity") != "substitution":
            counts["not_substitution"] += 1
            results.append({"uid": r["uid"], "outcome": "not_substitution",
                             "reason": f"granularity={r.get('granularity')!r}, not a word-level "
                                       f"substitution — no candidate pool to regenerate against"})
            print(f"[{i}/{len(records)}] {r['uid']:<40} not_substitution", flush=True)
            continue

        candidates = profile_index.get(r["original_text"], [])
        entry, note = resolve_profile_entry(r, candidates)
        if entry is None:
            counts["profile_unrecoverable"] += 1
            results.append({"uid": r["uid"], "outcome": "profile_unrecoverable", "reason": note})
            print(f"[{i}/{len(records)}] {r['uid']:<40} profile_unrecoverable: {note}", flush=True)
            continue

        try:
            res = attempt_second_candidate(r, entry)
        except Exception as e:
            counts["attempt_error"] += 1
            results.append({"uid": r["uid"], "outcome": "attempt_error", "reason": f"{type(e).__name__}: {e}"})
            print(f"[{i}/{len(records)}] {r['uid']:<40} attempt_error: {e}", flush=True)
            continue

        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
        results.append(res)
        print(f"[{i}/{len(records)}] {r['uid']:<40} {res['outcome']}", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({"counts": counts, "results": results}, indent=2), encoding="utf-8")

    print()
    print("=== FINAL COUNTS ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
