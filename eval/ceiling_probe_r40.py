"""
eval/ceiling_probe_r40.py — R40: large-scale substitution/restructuring
failure-mode probe.

Direct response to the user's question: "if a sentence isn't being
reformulated at all, that's no use — have we hit a ceiling?" This script
answers that with evidence rather than argument: 48 real sentences pulled
verbatim from four different public web sources (Wikipedia articles on
Artificial intelligence, Climate change, Cooking, and Small talk — chosen
for register diversity: technical, scientific, procedural, conversational)
are run through TODAY's live engine (reformulate.reformulate(), live
Datamuse, no DISABLE_DATAMUSE=1, matching R31/R39's precedent that the
flag changes the candidate pool materially) against four difficulty
profiles spanning light to heavy density.

This is NOT the same discipline as eval/pilot_select_pairs_v4.py's
curated human-rating corpus:
  - Failing items are KEPT and reported, not swapped out — the entire
    point here is to see and count the failures, not hide them.
  - No subprocess-per-item restructuring-stability recheck (VALIDATION.md
    SS8.4) is performed — this is a single live run per (sentence, profile)
    pair, one sample of T5's non-deterministic output, not a stability-
    verified one. Treat any single restructuring failure as a data point,
    not proof that sentence can NEVER be restructured — T5 is sampled,
    not deterministic (a documented, standing limitation).

Run:
    python eval/ceiling_probe_r40.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import paths  # noqa: F401
import semantic
from grammar import sanitize_input
from difficulty_profile import DifficultyProfile
import reformulate

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "eval" / "ceiling_probe_r40_results.json"

# ── Corpus: 48 real sentences, verbatim from live Wikipedia articles ───────
# (source, text)
SENTENCES: list[tuple[str, str]] = [
    # -- Artificial intelligence (technical/formal register) --
    ("ai", "Artificial intelligence (AI) is the capability of computational systems to perform tasks typically associated with human intelligence, such as learning, reasoning, problem-solving, perception, and decision-making."),
    ("ai", "High-profile applications of AI include advanced web search engines, chatbots, virtual assistants, autonomous vehicles, play and analysis in strategy games, and content generation."),
    ("ai", "Early researchers developed algorithms that imitated step-by-step reasoning that humans use when solving puzzles or making logical deductions."),
    ("ai", "Many of these algorithms were insufficient for solving large reasoning problems because they experienced a combinatorial explosion, meaning they become exponentially slower as the problems grow."),
    ("ai", "An ontology is the set of objects, relations, concepts, and properties used by a particular domain of knowledge."),
    ("ai", "A rational agent has goals or preferences and takes actions to make them happen."),
    ("ai", "Machine learning is the study of programs that can improve their performance on a given task automatically."),
    ("ai", "Natural language processing allows programs to read, write, and communicate in human languages."),
    ("ai", "State space search searches through a tree of possible states to try to find a goal state."),
    ("ai", "Gradient descent is a type of local search that optimises a set of numerical parameters by incrementally adjusting them to minimise a loss function."),
    ("ai", "Deep learning uses several layers of neurons between the network's inputs and outputs."),
    ("ai", "Generative pre-trained transformers are large language models that generate text based on the semantic relationships between words in sentences."),
    # -- Climate change (scientific/narrative register) --
    ("climate", "Earth's average surface air temperature has increased about 1.5 degrees Celsius since the Industrial Revolution."),
    ("climate", "Fossil fuel use, deforestation, and some agricultural and industrial practices release greenhouse gases."),
    ("climate", "The Arctic has warmed the most, and temperatures on land have generally increased more than sea surface temperatures."),
    ("climate", "Heat waves and wildfires are becoming more common."),
    ("climate", "Before the 1980s, it was unclear whether the warming effect of increased greenhouse gases was stronger than the cooling effect of airborne particulates in air pollution."),
    ("climate", "Between the 18th century and 1970 there was little net warming, as the warming impact of greenhouse gas emissions was offset by cooling from sulfur dioxide emissions."),
    ("climate", "The 2016 to 2025 decade warmed to an average of 1.26 degrees compared to the pre-industrial baseline."),
    ("climate", "The upper atmosphere is cooling, because greenhouse gases are trapping heat near the Earth's surface, and so less heat is radiating into space."),
    ("climate", "Since the pre-industrial period, the average surface temperature over land regions has increased almost twice as fast as the global average surface temperature."),
    ("climate", "Deforestation is the main land use change contributor to global warming, as the destroyed trees release carbon dioxide, and are not replaced by new trees."),
    ("climate", "Volcanic carbon dioxide emissions are more persistent, but they are equivalent to less than 1% of current human-caused emissions."),
    ("climate", "The range of hundreds of North American birds has shifted northward at an average rate of 1.5 kilometers per year over the past 55 years."),
    # -- Cooking (procedural register) --
    ("cooking", "Cooking techniques and ingredients vary widely, from grilling food over an open fire, to using electric stoves, to baking in various types of ovens, to boiling and blanching in water."),
    ("cooking", "Cooking is an aspect of all human societies and a cultural universal."),
    ("cooking", "Archaeological evidence of cooking fires dates to at least 300,000 years ago, but some estimate that humans started cooking as early as 2 million years ago."),
    ("cooking", "Long-chain sugars such as starch tend to break down into more digestible simpler sugars."),
    ("cooking", "Fats can reach temperatures above the boiling point of water and are often used to transfer high heat to other ingredients, such as in frying or sauteing."),
    ("cooking", "When proteins are heated they become denatured and change texture."),
    ("cooking", "Steaming works by continuously boiling water, which vaporizes into steam; the steam then transfers heat to the food, cooking it."),
    ("cooking", "Cooking can prevent many foodborne illnesses that would otherwise occur if raw food is consumed."),
    ("cooking", "Vitamin C is especially prone to oxidation during cooking and may be destroyed by protracted cooking."),
    ("cooking", "Home-cooked meals tend to be healthier with fewer calories, and less saturated fat, cholesterol and sodium on a per calorie basis."),
    ("cooking", "The scientific study of cooking has become known as molecular gastronomy."),
    ("cooking", "Cooking is done both by people in their own dwellings and by professional cooks and chefs in restaurants and other food establishments."),
    # -- Small talk (conversational/social register) --
    ("smalltalk", "Small talk is an informal type of discourse that does not cover any functional topics of conversation or any transactions that need to be addressed."),
    ("smalltalk", "Small talk consists of three main parts: a greeting, conversation, and a closing."),
    ("smalltalk", "The phenomenon of small talk was initially studied in 1923 by Bronislaw Malinowski in his essay on the problem of meaning in primitive languages."),
    ("smalltalk", "Phatic communication, or small talk, is not used to exchange important information; instead it is used to build and maintain interpersonal relationships."),
    ("smalltalk", "Small talk is a bonding ritual and a strategy for managing interpersonal distance."),
    ("smalltalk", "It serves many functions in helping to define the relationships between friends, colleagues, and new acquaintances."),
    ("smalltalk", "In a business meeting, it enables people to establish each other's reputation and level of expertise."),
    ("smalltalk", "In many cultures, silences between two people are usually considered uncomfortable and awkward."),
    ("smalltalk", "The topics of small talk conversations are generally less important than their social function."),
    ("smalltalk", "The first move is usually phrased so that it is easy for the other person to agree."),
    ("smalltalk", "Speech patterns between women tend to be more collaborative than those of men."),
    ("smalltalk", "Finland and Sweden have been cited as countries where there is little culture of small talk and people are more comfortable with silence."),
]

# ── Profiles: light -> heavy density, spanning common real declared-difficulty shapes ──
PROFILES: dict[str, dict] = {
    "light_single_sound": {"sounds": ["str"], "words": [], "phrases": []},
    "moderate_mixed": {"sounds": ["pr", "gr"], "words": ["particular", "significant"], "phrases": []},
    "heavy_dense": {
        "sounds": ["s", "th", "r"],
        "words": ["temperature", "technology", "important"],
        "phrases": ["as well as"],
    },
    "single_common_sound": {"sounds": ["s"], "words": [], "phrases": []},
}


def _build_profile(tag: str, spec: dict) -> DifficultyProfile:
    p = DifficultyProfile(profile_name=f"__ceiling_r40_{tag}__")
    for s in spec.get("sounds", []):
        p.add_sound(s, source="user_typed")
    for w in spec.get("words", []):
        p.add_word(w, source="user_typed")
    return p


def run_one(source: str, text: str, profile_name: str, spec: dict) -> dict:
    semantic.load_sbert()
    profile = _build_profile(profile_name, spec)
    corrected_text, grammar_fixes = sanitize_input(text)
    result = reformulate.reformulate(corrected_text, profile)

    sources = sorted({c["source"] for c in result["changes"]})
    triggers = set()
    for c in result["changes"]:
        triggers.update(c.get("triggered_by", []))

    return {
        "source": source,
        "profile": profile_name,
        "original_text": text,
        "reformulated_text": result["reformulated_text"],
        "status": result["status"],
        "n_changes": len(result["changes"]),
        "change_sources": sources,
        "triggered_by": sorted(triggers),
        "skipped": result["skipped"],
        "metrics": result["metrics"],
        "final_verification": result["final_verification"],
    }


def main() -> int:
    total = len(SENTENCES) * len(PROFILES)
    print(f"Running {len(SENTENCES)} sentences x {len(PROFILES)} profiles = {total} pairs "
          f"(live Datamuse)...", flush=True)

    results: list[dict] = []
    done = 0
    for profile_name, spec in PROFILES.items():
        for source, text in SENTENCES:
            r = run_one(source, text, profile_name, spec)
            results.append(r)
            done += 1
            print(f"  [{done}/{total}] {profile_name:<22} {source:<10} status={r['status']:<28} "
                  f"changes={r['n_changes']} sources={r['change_sources']}", flush=True)

    OUT_PATH.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {len(results)} results to {OUT_PATH}")

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n=== SUMMARY BY PROFILE ===")
    for profile_name in PROFILES:
        subset = [r for r in results if r["profile"] == profile_name]
        n = len(subset)
        by_status: dict[str, int] = {}
        for r in subset:
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        n_restructured = sum(1 for r in subset if "restructuring" in r["change_sources"])
        n_phrase = sum(1 for r in subset if "phrase" in r["change_sources"])
        n_substitution_only = sum(
            1 for r in subset
            if r["change_sources"] and set(r["change_sources"]) <= {"substitution"}
        )
        print(f"\n{profile_name} (n={n}):")
        for status, count in sorted(by_status.items()):
            print(f"  {status}: {count} ({count/n:.0%})")
        print(f"  substitution-only: {n_substitution_only}, phrase-tier used: {n_phrase}, "
              f"restructuring used: {n_restructured}")

    print("\n=== FAILURES (could_not_safely_reformulate) ===")
    failures = [r for r in results if r["status"] == "could_not_safely_reformulate"]
    print(f"{len(failures)}/{total} pairs total ({len(failures)/total:.0%})")
    for r in failures:
        reasons = sorted({s["reason"] for s in r["skipped"] if s.get("reason")})
        print(f"  [{r['profile']}][{r['source']}] \"{r['original_text'][:70]}...\" "
              f"reasons={reasons}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
