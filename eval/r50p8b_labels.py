"""
eval/r50p8b_labels.py -- R50 Phase 8B, task 1: blind, WHOLE-SENTENCE
labels for the 58 unique delivered-sentence groups harvested from the
second organic harvest (eval/r50p8b_harvest.py -> phase8b_raw_harvest.json
-> eval/r50p8b_sentence_groups.txt). Every group is judged as a complete
original->reformulated pair (the resolved Phase 8B convention), not as
isolated word changes -- so a single verdict applies to every word-pair
record that produced that exact delivered sentence.

1-based index below = position in r50p8b_sentence_groups.txt.
"""

# index: (severity, [defect labels, primary first], rationale)
LABELS = {
    1: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the heaviest driver of plate motion\" changes the specific claim from force/dominance (\"strongest\") to mass (\"heaviest\") -- a different physical property."),
    2: ("MINOR", ["WRONG_WORD_OR_SENSE"], "\"treatment\" for \"preparation\" is a mild, defensible sense shift; \"gives\"/\"specific\" are fine."),
    3: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"], "\"the most effective method of keeping infectious diseases\" (missing \"away\"/\"at bay\") reads as maintaining diseases, near-opposite of preventing them."),
    4: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"avoid smallpox\" is fine; \"hints of the use\" is a bit vaguer than \"hints of the practice\" but still comprehensible."),
    5: ("CLEAN", ["CLEAN"], "\"created\" is a valid, natural synonym for \"produced\"."),
    6: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"the folk use of inoculation\" is a slightly less natural collocation than \"the folk practice of inoculation\" but remains comprehensible."),
    7: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the careful effect of cowpox\" -- \"careful\" (cautious) does not substitute for \"protective\" (immunizing); loses the entire immunological claim."),
    8: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the new careful inoculations\" -- same protective->careful defect as case 7, independently occurring in a different sentence."),
    9: ("SEVERE", ["GRAMMAR", "WRONG_WORD_OR_SENSE"], "\"thus is up to respond\" does not parse as standard English (missing \"for\"/\"to\"); \"peptide coat\" is also a real scientific imprecision for the correct term \"protein coat\"."),
    10: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"acts\" (discrete actions) for \"processes\" (systematic/continuous mechanisms) is a real precision loss in a technical/definitional sentence."),
    11: ("CLEAN", ["CLEAN"], "\"main drivers\" is a valid, natural synonym for \"primary drivers\"."),
    12: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"selective pressure\" is a specific, fixed term in evolutionary biology; \"selective force\" is a non-standard substitute that breaks it."),
    13: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"a speeding up of this natural work\" -- \"work\" does not fit as a substitute for a biological/evolutionary mechanism (\"process\")."),
    14: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"support the evolution... by supporting the bacteria\" is an awkward near-repetition, though \"support\"/\"promote\" are reasonably close synonyms."),
    15: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"This act, known as horizontal gene transfer\" -- \"act\" does not fit a systematic biological mechanism (\"process\"); same recurring pattern as case 13."),
    16: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"continue to create offspring\" is a slightly unusual collocation vs. the standard \"produce offspring\", but understandable."),
    17: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "\"unit rate\"/\"market-clearing rate\" for \"unit price\"/\"market-clearing price\" -- \"rate\" is not the correct economic term (implies exchange rate/frequency), breaking the specific fixed term \"market-clearing price\"."),
    18: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"at each possible cost a smaller quantity would be supplied\" -- \"price\" and \"cost\" are distinct economic concepts (what buyers pay vs. what it costs to produce); substituting changes the actual economic claim, especially confusing alongside the sentence's own separate \"cost of raw materials\"."),
    19: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"a fall in making costs\" breaks the specific fixed economic term \"production costs\"."),
    20: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "\"more than the market cost they pay\" -- breaks the fixed term \"market price\" and the collocation \"pay a price\"; same price/cost conflation as case 18."),
    21: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"], "\"as the terms decreases\" garbles the specific named economic law (\"law of demand\", about PRICE) into an ungrammatical, economically meaningless substitute (\"terms\" does not decrease in this sense; also introduces a subject-verb mismatch)."),
    22: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"at a given cost\" for \"at a given price\" -- same price/cost conflation, in one of the law-of-demand defining sentences."),
    23: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"], "\"the cost and the quantity move in opposite directions\" -- changes which specific variable (price, not cost) the law of demand describes."),
    24: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"its cost rises\" for \"its price rises\" -- same price/cost conflation."),
    25: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], "\"inoculation against vaccination\" is self-contradictory -- inoculation IS a vaccination method, so being \"against\" it while performing it is a logical inversion."),
    26: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], "\"the protective effect of cowpox against vaccination\" -- cowpox's protective effect is against SMALLPOX; vaccination is the protective mechanism itself, not the threat -- backwards."),
    27: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"knows the protein coat\" and \"prepared to answer\" are both non-standard for immunological recognition/response -- \"answer\" especially sounds like answering a question, not mounting a biological response."),
    28: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], "\"Vaccines led to the eradication of vaccination, one of the most contagious and deadly diseases in humans\" -- calls the cure a disease and claims the treatment itself was eradicated; a complete logical inversion of the actual, well-known historical claim (smallpox was eradicated)."),
    29: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the first decades of the 20th period\" breaks the fixed calendar unit \"century\"."),
    30: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"deep-sea dissemination\" completely breaks the specific, named geological mechanism \"seafloor spreading\" (the core evidence for plate tectonics) into an unrelated and incorrect substitute."),
    31: ("SEVERE", ["GRAMMAR"], "\"The processes that produce in plates\" does not parse -- \"produce\" is transitive and needs a direct object; \"result in\" does not substitute this way."),
    32: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "\"their corresponding motion\" for \"their relative motion\" loses the specific geophysical meaning (motion measured relative to a reference frame/other plate)."),
    33: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], "\"the absolute movement of the plates\" for \"the relative movement\" changes the actual measurement paradigm being described -- plate motion is conventionally described relative to other plates/reference frames, not in absolute terms; a real technical/factual claim change, not just a register shift."),
    34: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "GRAMMAR"], "\"Tectonic plates are about fixed\" -- \"fixed\" (stationary) contradicts the basic premise of the article it appears in (plate TECTONICS is specifically that plates move); \"rigid\" (stiff/non-deforming) and \"fixed\" (immobile) are different properties, and this substitution asserts the wrong one. \"about fixed\" also does not parse naturally."),
    35: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "WRONG_WORD_OR_SENSE"], "\"the lithosphere is cooler and more fixed\" -- same rigid->fixed defect as case 34, independently occurring; asserts plates are immobile in an article whose entire subject is that they move."),
    36: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "\"primary drivers of this opposition\" -- \"opposition\" loses the specific scientific/medical meaning of \"antimicrobial resistance\" (a defined term), reading instead as political/social resistance."),
    37: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"Antimicrobial condition is driven largely by...\" breaks the article's own core named subject term (\"antimicrobial resistance\") entirely."),
    38: ("SEVERE", ["GRAMMAR", "FIXED_TERM_OR_IDIOM"], "\"a accelerating up of this natural process\" has an article-agreement error (\"a\" before a vowel sound) and breaks the fixed phrasal verb \"speeding up\"."),
    39: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"induce antimicrobial condition\" -- same resistance->condition fixed-term erosion as case 37, independently occurring."),
    40: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"Natural choice\" breaks one of the most well-known fixed scientific terms in biology (\"natural selection\"); \"survive\"->\"last\" is also a real sense shift (duration vs. overcoming a threat)."),
    41: ("SEVERE", ["GRAMMAR", "FIXED_TERM_OR_IDIOM"], "\"it places at the market-clearing price\" does not parse (\"place\" is transitive, needs an object) and breaks the fixed equilibrium phrase \"settles at [price]\"."),
    42: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL"], "\"A fall in production costs would increase demand, shifting the demand curve to the left\" -- production costs are a SUPPLY-side factor, not a demand-side one; swapping supply->demand is a substantive economic-logic error, compounded by an internally inconsistent direction (an increase in demand should shift the demand curve right, not left)."),
    43: ("SEVERE", ["GRAMMAR", "FIXED_TERM_OR_IDIOM"], "\"it is mentioned to as an increase in demand\" is not standard English and breaks the fixed phrasal verb \"referred to as\"."),
    44: ("SEVERE", ["GRAMMAR", "FIXED_TERM_OR_IDIOM"], "\"a add curve shift\" has an article-agreement error and breaks the fixed economic term \"supply curve\" into nonsense."),
    45: ("SEVERE", ["GRAMMAR", "FIXED_TERM_OR_IDIOM"], "\"the quantity providing decreases\" does not parse and breaks the specific fixed economic term \"quantity supplied\"."),
    46: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"the money issue\" breaks the specific macroeconomic term \"money supply\"; \"the interest charge\" is a different, non-equivalent concept from \"the interest rate\"."),
    47: ("CLEAN", ["CLEAN"], "\"its price increases\" is a valid, natural synonym for \"its price rises\"."),
    48: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"the immune organization\" breaks the standard biological/medical term \"immune system\" into a nonsensical substitute (an organization is a social structure, not a body system)."),
    49: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "GRAMMAR"], "\"the worldwide eradication of vaccination\" -- same self-contradictory eradication claim as case 28, independently occurring; also breaks the \"such as\" listing construction (\"much as polio...\")."),
    50: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"The immune organization recognizes vaccine agents\" -- same immune-system->immune-organization defect as case 48, independently occurring."),
    51: ("SEVERE", ["WRONG_WORD_OR_SENSE", "GRAMMAR"], "\"have been late moving\" -- \"late\" (tardiness/timing) does not substitute for \"slowly\" (rate of movement); a category confusion that also does not parse naturally."),
    52: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"10 cms annually\" uses a nonstandard abbreviation (\"cm\" is the correct SI form) -- an informal/imprecise rendering, not a meaning change."),
    53: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"increased exclusive pressure\" breaks the specific fixed evolutionary-biology term \"selective pressure\" (same class of error as case 12); \"spontaneous\"->\"natural\" is comparatively minor."),
    54: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"occur during case division\" breaks the fundamental, extremely well-known fixed biological term \"cell division\"."),
    55: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"backing the bacteria\" is a valid but slightly more informal near-synonym for \"supporting the bacteria\"."),
    56: ("SEVERE", ["WRONG_WORD_OR_SENSE", "GRAMMAR"], "\"allows resistance genes to continue rapidly between different bacterial manners\" -- \"continue\" (persisting) does not mean the same as \"spread\" (transmitting/expanding) and reads ungrammatically here; \"manners\" (ways of behaving) is nonsensical for \"species\" (a biological classification)."),
    57: ("SEVERE", ["OTHER_DEFECT", "GRAMMAR"], "\"increase add, shifting the issue curve\" -- the same original word (\"supply\") was replaced with two DIFFERENT wrong substitutes within one reformulation pass, producing a doubly-garbled, non-parsing sentence distinct from case 42's cleaner supply->demand swap."),
    58: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"the money issue to determine the interest rate\" -- breaks the fixed macroeconomic term \"money supply\", independently of case 46's combined defect."),
}

assert len(LABELS) == 58, len(LABELS)

# Records whose PRIMARY defect is FACTUAL_OR_LOGICAL_REVERSAL and were
# organically observed (not constructed) -- for the evidence-quality /
# provenance breakdown required by task 4.
ORGANIC_FACTUAL_REVERSAL_GROUP_INDICES = [25, 26, 28, 33, 34, 35, 42, 49]
