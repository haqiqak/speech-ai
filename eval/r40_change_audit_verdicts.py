"""
eval/r40_change_audit_verdicts.py — R40: manual linguistic verdicts.

Direct, unaided linguistic judgment (Claude, not the pipeline's own
SBERT/MeaningBERT/contextual_fit scores) on every one of the 112
individual substitution changes in eval/r40_change_audit_data.json.
Three verdicts:
  CLEAN  - correct, natural, meaning fully preserved.
  MINOR  - meaning basically preserved, but a real quality loss:
           awkward collocation, register mismatch, lost precision.
  SEVERE - a real defect: ungrammatical, nonsensical, wrong word sense,
           duplicate/garbage token, or a factual/logical change.

Verdicts are index-matched (1-based) to eval/r40_change_audit_data.json's
"changes" list, in file order. Reasons are intentionally short — the
full before/after text and scores are already in that file; this file
adds only the judgment and why.

Run:
    python eval/r40_change_audit_verdicts.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "eval" / "r40_change_audit_data.json"
OUT_PATH = ROOT / "eval" / "r40_change_audit_verdicts.json"

# (verdict, reason) — index 0 = change #1, etc.
VERDICTS: list[tuple[str, str]] = [
    ("SEVERE", '"way games" is not a coherent compound; loses the meaning of "strategy".'),
    ("SEVERE", '"powerful than" is ungrammatical — comparative form lost ("more powerful than").'),
    ("MINOR", '"a way for managing" is a slightly awkward preposition choice; comprehensible.'),
    ("SEVERE", '"issue" breaks the parallel gerund/noun list and does not fit "problem-solving"\'s sense.'),
    ("SEVERE", '"places" (locations) for "properties" (attributes) — wrong sense in an ontology context.'),
    ("CLEAN", "valid, natural synonym, meaning fully preserved."),
    ("MINOR", '"options" (external choices) for "preferences" (internal wants) — real but survivable sense shift.'),
    ("SEVERE", '"softwares" is an ungrammatical plural of a mass noun.'),
    ("SEVERE", 'breaks the fixed technical term "natural language processing" into nonsense ("operation").'),
    ("SEVERE", "duplicate of #8's ungrammatical plural, same sentence."),
    ("MINOR", '"workings" is an unusual but attested collocation; comprehensible.'),
    ("MINOR", '"warming gases" for "greenhouse gases" loses the standard term but stays meaningful.'),
    ("MINOR", 'creates "warming impact of...warming gases" — awkward near-repetition, not nonsense.'),
    ("SEVERE", '"gas gas emissions" — literal word duplication, nonsense.'),
    ("SEVERE", '"palaeolithic" (Stone Age) for "pre-industrial" (~1850) — ~50,000-year factual error; reads fluently despite being wrong (contextual_fit=0.999, a false negative).'),
    ("SEVERE", '"gas gases" — literal word duplication, nonsense.'),
    ("SEVERE", "same palaeolithic/pre-industrial factual error, second occurrence."),
    ("MINOR", '"cooking food" replacing "grilling" inside a sentence about cooking techniques is circular/less specific but not wrong.'),
    ("MINOR", '"peptides" is a related but technically distinct concept from "proteins" — imprecise, not absurd.'),
    ("MINOR", '"avoid" for "prevent" is a slightly odd collocation ("cooking can avoid illnesses") but understandable.'),
    ("CLEAN", "valid synonym, idiomatic collocation preserved."),
    ("CLEAN", "clean simplification, meaning and grammar fully intact."),
    ("CLEAN", "valid, natural synonym."),
    ("CLEAN", '"welcome" is a reasonable near-synonym for "greeting" in this list context.'),
    ("SEVERE", '"the trouble of meaning" does not match the idiomatic "the problem of meaning" (a term-of-art in this essay title).'),
    ("SEVERE", '"natural languages" is a specific, different linguistics term from "primitive languages" (Malinowski\'s actual term) — wrong sense with real technical meaning change.'),
    ("SEVERE", '"web look engines" — nonsense compound.'),
    ("SEVERE", '"way games" — nonsense compound, duplicate of #1.'),
    ("SEVERE", '"the lot of objects" is not standard English for "the set of objects".'),
    ("SEVERE", '"objects, telling, concepts" — a verb/gerund inserted into a noun list, nonsense.'),
    ("SEVERE", '"the work of programs" changes the sentence\'s actual definitional claim (a field of study vs. an activity/output).'),
    ("SEVERE", '"programs to take" — wrong sense, and combines with #33 to duplicate "communicate...communicate".'),
    ("SEVERE", 'creates "take, communicate, and communicate" — duplicate token, nonsense list.'),
    ("MINOR", '"local quest" for "local search" (a technical optimization term) is a register clash but not nonsense.'),
    ("SEVERE", '"optimists a place of numerical parameters" — wrong sense, "place" does not fit a mathematical set.'),
    ("CLEAN", "valid, natural synonym."),
    ("SEVERE", 'combines with #38 into "average layer air heat" — nonsense compound.'),
    ("SEVERE", 'combines with #37 into "average layer air heat" — nonsense compound.'),
    ("SEVERE", '"practices device greenhouse gases" — "device" used as a verb; not grammatical English.'),
    ("MINOR", '"ocean" for "sea" is a fine synonym in isolation.'),
    ("SEVERE", 'combined with #40, replaces the precise term "sea surface temperature" with "ocean layer temperatures" — a different, stealth-plausible scientific claim (implies depth, not surface).'),
    ("SEVERE", "duplicate of #2's ungrammatical comparative."),
    ("SEVERE", '"18th half-century" does not correspond to any real time period — factual/logical corruption; contextual_fit=0.61 is a partial false negative.'),
    ("SEVERE", '"s dioxide emissions" — the letter "s" used as a word; contextual_fit correctly near-zero.'),
    ("SEVERE", '"the place of hundreds of...birds has shifted" — wrong sense ("range"=distribution, not location) and does not parse.'),
    ("SEVERE", '"an average place of 1.5 kilometers per year" — wrong sense, does not fit a unit-of-measurement context.'),
    ("SEVERE", '"electric fires" commonly means room heaters, not cooking appliances — a real sense confusion in a cooking-technique list.'),
    ("SEVERE", '"all human companies" for "all human societies" — wrong sense, factually absurd in context.'),
    ("SEVERE", '"humans went cooking" is not idiomatic (unlike "went fishing"); wrong verb choice.'),
    ("SEVERE", 'restructuring: "long-chain sugars like glucose" is scientifically backwards — glucose is the simple sugar starch breaks INTO, not an example of a long-chain sugar.'),
    ("SEVERE", '"if new food is consumed" loses the raw/cooked distinction the sentence is actually about (foodborne illness from raw food).'),
    ("SEVERE", '"pure fat" is not a coherent replacement for "saturated fat" — a specific, different nutritional term.'),
    ("SEVERE", '"na" — a chemical symbol used as a word for "sodium".'),
    ("MINOR", '"technical" for "scientific" is a mild register/precision shift, still comprehensible.'),
    ("SEVERE", '"the technical take of cooking" — wrong sense, "take" (opinion) does not fit "the study of cooking".'),
    ("SEVERE", '"buildings and other food establishments" implies buildings are not food establishments — contradicts the sentence and loses the specific meaning of "restaurants".'),
    ("SEVERE", '"Small talk" is a fixed term (the article\'s own subject); "Little talk" is not a substitute.'),
    ("SEVERE", "same fixed-term erosion, second occurrence."),
    ("SEVERE", "same fixed-term erosion, third occurrence."),
    ("SEVERE", '"was initially taken" for "was initially studied" — wrong sense, does not mean the same thing.'),
    ("SEVERE", '"It helps many functions" breaks the collocation "serves a function"; not idiomatic.'),
    ("MINOR", '"associations" for "relationships" is a real but survivable sense shift, still comprehensible.'),
    ("MINOR", '"esteem" (respect) for "reputation" (how one is perceived) — related but not identical; comprehensible.'),
    ("SEVERE", '"quiets" is a non-standard plural noun form of "quiet".'),
    ("SEVERE", '"Words patterns" should be singular attributive "word pattern" — ungrammatical.'),
    ("CLEAN", '"methods" for "systems" is acceptable in this AI-definition context.'),
    ("SEVERE", '"much as learning, reasoning..." changes the list-introducing logic of "such as" — a structural, not just lexical, change.'),
    ("SEVERE", 'breaks the fixed, well-known compound term "search engines" into "research engines".'),
    ("SEVERE", '"way games" — nonsense compound, duplicate.'),
    ("MINOR", '"detailed reasoning" for "step-by-step reasoning" loses the procedural connotation but is not wrong.'),
    ("MINOR", '"working puzzles" is attested in some English varieties ("work a puzzle"), non-standard but understandable.'),
    ("SEVERE", '"working large reasoning problems" is a less natural collocation than #71\'s case; reads as broken.'),
    ("SEVERE", 'a near-antonym substitution that inverts the sentence\'s logic: "become exponentially easier" contradicts "insufficient for solving" earlier in the same sentence — the single worst substitution found.'),
    ("SEVERE", "duplicate of #29's ungrammatical phrasing."),
    ("SEVERE", "duplicate of #31's definitional meaning change."),
    ("MINOR", "duplicate of #34's register clash."),
    ("SEVERE", "duplicate of #35's wrong-sense error."),
    ("CLEAN", "duplicate of #36's clean synonym."),
    ("MINOR", '"meaningful relationships" is a reasonable lay paraphrase of the technical term "semantic relationships".'),
    ("SEVERE", '"words in times" — wrong sense, "times" does not fit "sentences" at all.'),
    ("SEVERE", 'duplicate of #37\'s nonsense compound ("average layer air temperature").'),
    ("MINOR", "duplicate of #40's fine synonym."),
    ("SEVERE", "duplicate of #41's stealth-wrong scientific term."),
    ("SEVERE", "duplicate of #2/#42's ungrammatical comparative."),
    ("SEVERE", "duplicate of #43's factual/logical corruption."),
    ("SEVERE", "duplicate of #44's letter-as-word error."),
    ("SEVERE", '"near the Earth\'s open" — drops the noun, does not parse.'),
    ("SEVERE", '"radiating into place" — wrong sense, loses the astronomical meaning of "space".'),
    ("SEVERE", '"average rise temperature" — nonsense compound, not a real term.'),
    ("SEVERE", '"average open temperature" — nonsense compound.'),
    ("SEVERE", "duplicate of #47's appliance-type sense confusion."),
    ("SEVERE", "duplicate of #48's wrong-sense error."),
    ("SEVERE", "duplicate of #49's non-idiomatic verb choice."),
    ("SEVERE", "duplicate of #50's scientifically-backwards restructuring."),
    ("SEVERE", 'duplicate of the "such"->"much" structural break, different sentence.'),
    ("MINOR", '"cooking" for "sauteing" is a reasonable hypernym, mildly redundant given the sentence topic.'),
    ("SEVERE", "duplicate of #52's wrong nutritional term."),
    ("SEVERE", "duplicate of #53's chemical-symbol-as-word error."),
    ("MINOR", "duplicate of #54's mild register shift."),
    ("SEVERE", "duplicate of #55's wrong-sense error."),
    ("SEVERE", "duplicate of #57's fixed-term erosion."),
    ("SEVERE", "duplicate of #57's fixed-term erosion."),
    ("SEVERE", "duplicate of #59's fixed-term erosion."),
    ("SEVERE", "duplicate of #60's wrong-sense error."),
    ("SEVERE", "duplicate of #59's fixed-term erosion, different sentence."),
    ("SEVERE", "duplicate of #57's fixed-term erosion."),
    ("MINOR", "duplicate of #3's slightly awkward preposition."),
    ("SEVERE", "duplicate of #61's broken collocation."),
    ("SEVERE", "duplicate of #64's non-standard plural."),
    ("SEVERE", '"little talk" for "small talk" and "friendly" for "social" — the fixed term erodes again, and "social function" (a specific sociological sense) becomes "friendly function", a real meaning change.'),
    ("SEVERE", '"friendly function" for "social function" — wrong sense; "social function" is a specific term (the role something plays), not about friendliness.'),
    ("SEVERE", "duplicate of #65's ungrammatical plural."),
]

if __name__ == "__main__":
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))["changes"]
    assert len(VERDICTS) == len(data), f"{len(VERDICTS)} verdicts vs {len(data)} changes"

    out = []
    tally = {"CLEAN": 0, "MINOR": 0, "SEVERE": 0}
    for i, (c, (verdict, reason)) in enumerate(zip(data, VERDICTS), 1):
        tally[verdict] += 1
        out.append({
            "index": i,
            "original_word": c["original_word"],
            "replacement_word": c["replacement_word"],
            "contextual_fit": c["contextual_fit"],
            "sbert_sim": c["sbert_sim"],
            "verdict": verdict,
            "reason": reason,
        })

    OUT_PATH.write_text(json.dumps({"tally": tally, "n": len(out), "verdicts": out}, indent=2, ensure_ascii=False), encoding="utf-8")
    n = len(out)
    print(f"n={n}")
    for k, v in tally.items():
        print(f"  {k}: {v} ({v/n:.0%})")
