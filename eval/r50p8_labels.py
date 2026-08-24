"""
eval/r50p8_labels.py -- R50 Phase 8: blind human labels for the 68 unique
cases harvested organically from the live pipeline (eval/r50p8_harvest.py
-> eval/r50_dataset/phase8_blind_candidates.json).

Labeling discipline: assigned by reading ONLY eval/r50p8_blind_sheet.txt
(original_word/replacement_word + original_sentence/reformulated_sentence
-- no automated scores, no NLI/grammar results, no knowledge of which
profile/experiment produced the change, no defect-class target in mind
going in). Rater: Claude (same epistemic status as R40's original audit
and R50's re-labeling pass -- not an independent human rater; see the
Phase 8 report's limitations section and the separate subagent
second-rater pass for a genuinely independent read on a subset).

Index below = 1-based position in phase8_blind_candidates.json /
r50p8_blind_sheet.txt.
"""

# index: (severity, [defect labels, primary first], rationale)
LABELS = {
    1: ("CLEAN", ["CLEAN"], "\"demanding\" is a valid, natural synonym for \"strenuous\" in this context."),
    2: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"gains in muscle property\" is nonsensical -- \"property\" does not fit as a substitute for \"strength\" in an anatomical/fitness context."),
    3: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"a system of biological works\" is an unusual, near-nonsensical plural; \"works\" does not naturally substitute for \"processes\" in this register."),
    4: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"a work that releases oxygen\" -- \"work\" (implying labor/output) does not fit \"process\" (a systematic mechanism) here."),
    5: ("CLEAN", ["CLEAN"], "\"creating\" is a valid, natural synonym for \"producing\"."),
    6: ("CLEAN", ["CLEAN"], "\"mostly\" is a valid, natural synonym for \"primarily\"."),
    7: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"light-green\" asserts a specific, different shade than \"green\" -- changes the actual color claim being made about the reflected spectrum and plant color."),
    8: ("SEVERE", ["WRONG_WORD_OR_SENSE", "GRAMMAR"], "\"an act called carbon fixation\" -- \"act\" implies a single deliberate action, not a scientific process; also introduces an article-agreement error (\"a act\")."),
    9: ("SEVERE", ["GRAMMAR"], "\"the thus bound system\" -- \"thus\" (a conjunctive adverb) is inserted where an adjective/participle is grammatically required; does not parse."),
    10: ("SEVERE", ["GRAMMAR"], "\"most widely its eight planets\" does not parse as a coherent phrase (co-occurs with case 9 in the same sentence)."),
    11: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"protoplanetary disc\" is the specific, fixed astronomical term for the pre-planet-formation disc; \"planetary disc\" is a different, vaguer term that changes the claim (implies a disc of/around already-formed planets)."),
    12: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"bound to it by extent\" -- \"extent\" does not fit the \"bound by [force]\" construction; nonsensical substitute for \"gravity\"."),
    13: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the heavy collapse of a region\" -- \"heavy\" describes weight, not the causal force (gravity) driving the collapse; loses the actual physical mechanism."),
    14: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"health troubles\" is a mild register shift (more informal) from \"health problems\" in an otherwise formal health-statistics sentence, but remains comprehensible."),
    15: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"large muscle classes\" breaks the fixed anatomical term \"muscle groups\"; \"classes\" reads as a categorization/course term, not an anatomical one."),
    16: ("SEVERE", ["OTHER_DEFECT", "GRAMMAR"], "Restructuring produces a circular self-reference (\"the transition included the transition from...\") and an odd adjectival form (\"hand-producing methods\"); reads as garbled rather than merely awkward."),
    17: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"modern making methods\" is an unusual collocation for \"modern production methods\" but roughly conveys the same idea."),
    18: ("SEVERE", ["GRAMMAR"], "\"Before to the Industrial Revolution\" is ungrammatical -- \"before\" does not take \"to\" the way \"prior\" does; the substitution didn't account for the required preposition change."),
    19: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"Internet convention suite\" breaks the fixed, well-known technical term \"protocol suite\" (e.g. the TCP/IP protocol suite)."),
    20: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "In a list of network-ownership categories, \"private\" is a specific technical/legal category distinct from \"public\"; \"personal\" refers to a different concept (e.g. personal-area networks), not the same category."),
    21: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"published a request\" -- a request and a proposal are different speech acts; the original historical proposal offered a design, it did not ask for one."),
    22: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "FACTUAL_OR_LOGICAL_REVERSAL"], "The actual historical document referenced is titled \"A Protocol for Packet Network Intercommunication\"; \"design\" for \"protocol\" changes the specific named subject of a real historical citation."),
    23: ("SEVERE", ["WRONG_WORD_OR_SENSE", "GRAMMAR"], "\"a organization of biological processes\" -- \"organization\" (implying an institution/structured group) is an odd substitute for \"system\" in this scientific-process sense; also an article-agreement error (\"a organization\")."),
    24: ("SEVERE", ["GRAMMAR"], "\"much as most plants\" breaks the \"such as\" listing construction (co-occurs with case 23 in the same sentence) -- a structural, not just lexical, change, matching the same bug class identified in R40 #67/#95."),
    25: ("CLEAN", ["CLEAN"], "\"critical part\" for \"critical role\" is a valid, natural near-synonym."),
    26: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"it gives most of the biological energy\" for \"it supplies\" is a looser, more casual synonym; meaning is preserved but precision/register is slightly reduced."),
    27: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"abundant in leaf cases\" -- \"cases\" (containers) is nonsensical as a substitute for \"cells\" (the correct biological term)."),
    28: ("CLEAN", ["CLEAN"], "\"two phases\" is a valid, natural synonym for \"two stages\"."),
    29: ("MINOR", ["WRONG_WORD_OR_SENSE"], "\"not just land and water\" -- \"land\" (territory/ground broadly) is a real but mild sense shift from \"soil\" (the specific growing substance); still roughly sensible in context."),
    30: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"The establishment formed about 4.6 billion years ago\" -- \"establishment\" (an institution being founded) is a category mismatch for the physical/astronomical formation of the Solar System."),
    31: ("CLEAN", ["CLEAN"], "\"a dense part of a molecular cloud\" for \"a dense region\" is a valid, natural near-synonym on its own (the co-occurring \"establishment\" substitution in case 30 is the actual defect in this shared sentence)."),
    32: ("SEVERE", ["OTHER_DEFECT"], "\"going energy that is emitted\" does not parse -- \"going\" cannot modify \"energy\" this way; a nonsense substitution similar in kind to R40's \"gas gas\" duplication artifacts."),
    33: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"daylight can keep surface water liquid\" -- \"daylight\" (a temporal concept, the lit period of the day) is substituted for \"sunlight\" (the physical energy/heat source); changes the actual causal agent from a physical process to a time-of-day concept."),
    34: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"open water\" is itself a specific, different hydrology/nautical term (water away from shore) from \"surface water\" (water at/near the surface) -- breaks a fixed technical term and substitutes a different one, co-occurring with case 33 in the same sentence."),
    35: ("CLEAN", ["CLEAN"], "\"turn\" for \"rotate\" is a valid, natural synonym here; incidentally also resolves a pre-existing grammar oddity in the original (\"to rotates\" -> \"to turn\")."),
    36: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"more oxygen than it would while placing\" is nonsensical -- \"placing\" requires an object and does not substitute for the intransitive \"resting\"."),
    37: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"upper lung tract infections\" breaks the fixed medical term \"respiratory tract\"; \"lung\" specifically denotes the LOWER respiratory tract, so this also introduces an anatomically incorrect claim, not just an awkward phrasing."),
    38: ("SEVERE", ["GRAMMAR"], "\"ability to better from intensive exercise\" -- \"better\" is used as a verb where none exists in standard English; does not parse."),
    39: ("CLEAN", ["CLEAN"], "\"intensive exercise\" for \"strenuous exercise\" is a valid, natural synonym on its own (case 38, in the same sentence, is the actual defect)."),
    40: ("SEVERE", ["FACTUAL_OR_LOGICAL_REVERSAL", "OTHER_DEFECT"], "Restructuring swaps cause and effect: the original states resistance training AND protein consumption (causes) promote hypertrophy and strength gains (effects); the reformulation moves \"muscle hypertrophy and muscle gains\" into subject position as if THEY are what promotes \"muscle training\" -- a genuine causal-relationship reversal, not just an awkward rewrite, produced by the live escalation mechanism on a real sentence."),
    41: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"cardiovascular administration\" breaks the fixed medical term \"cardiovascular system\"; \"administration\" (management/governance) is nonsensical applied to a bodily system."),
    42: ("SEVERE", ["GRAMMAR", "WRONG_WORD_OR_SENSE"], "\"had distributed to continental Europe\" -- \"distribute\" is not idiomatically used intransitively this way (unlike \"spread to\"); also implies active dissemination rather than organic diffusion, a real sense shift."),
    43: ("SEVERE", ["GRAMMAR"], "\"the most key event\" is a non-standard comparative construction -- \"key\" does not take \"most\" the way \"important\" does in standard usage."),
    44: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FACTUAL_OR_LOGICAL_REVERSAL"], "\"increasing use of machine power\" for \"steam power\" loses the specific, historically-accurate technology being credited (steam engines specifically, not machines generally) -- changes a factual/historical claim to a vaguer, different one."),
    45: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"the mid-18th period\" breaks the fixed calendar unit \"century\"; \"period\" loses the specific 100-year meaning and does not read as a standard time reference."),
    46: ("CLEAN", ["CLEAN"], "\"Fast adoption\" for \"Rapid adoption\" is a valid, natural synonym on its own (case 47, in the same sentence, is the actual defect)."),
    47: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"mechanized textile twisting\" breaks the specific historical/technical term \"textile spinning\" (turning fiber into thread) -- central to the actual Industrial Revolution narrative being described; \"twisting\" is a different, non-standard substitute in this industry context."),
    48: ("SEVERE", ["GRAMMAR"], "\"production open from Britain to...\" does not parse -- \"open\" cannot function as the main verb this construction requires."),
    49: ("MINOR", ["WRONG_WORD_OR_SENSE"], "\"the earliest shown use\" for \"the earliest recorded use\" -- \"shown\" (demonstrated) is a real but moderate sense shift from \"recorded\" (documented in writing), which fits the historical-citation context specifically; still roughly comprehensible."),
    50: ("CLEAN", ["CLEAN"], "\"entered the competition to industrialise\" for \"entered the race to industrialise\" is a valid, natural synonym (co-occurs with case 49's defect in the same sentence, but is fine on its own)."),
    51: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"Internet protocol collection\" breaks the specific fixed technical term \"protocol suite\" used in networking (e.g. TCP/IP suite); \"collection\" is not standard terminology."),
    52: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"local to global extent\" for \"local to global scope\" is a slightly less natural collocation but remains comprehensible and meaning-preserving."),
    53: ("SEVERE", ["GRAMMAR"], "\"no one concentrated governance\" is structurally ambiguous -- \"no one\" strongly reads as the pronoun \"nobody\" in standard English, risking a misparse (\"nobody has concentrated governance\") rather than the intended \"not a single, concentrated governance\"."),
    54: ("CLEAN", ["CLEAN"], "\"concentrated governance\" for \"centralized governance\" is a valid, natural near-synonym on its own (case 53, in the same sentence, is the actual defect)."),
    55: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"network puts its own policies\" breaks the fixed collocation \"sets policies\"; \"puts policies\" is not standard English (one \"puts a policy in place\" but does not simply \"put policies\")."),
    56: ("MINOR", ["WRONG_WORD_OR_SENSE"], "\"authors published a proposal\" for \"researchers published a proposal\" is a mild role-identity shift (a researcher is not necessarily just an author) but remains reasonable and comprehensible in this authorship context."),
    57: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "\"two finding institutions\" breaks the fixed term \"research institution\" and does not parse as a coherent category (\"finding institution\" is not a real classification)."),
    58: ("MINOR", ["WRONG_WORD_OR_SENSE"], "\"15 places were connected\" for \"15 sites\" loses \"site\"'s specific networking-technical meaning (a network location/node) in favor of a vaguer general term, but remains comprehensible."),
    59: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"water breaking\" for \"water splitting\" breaks the specific fixed scientific term for the photolysis process, and (notably) collides with a completely unrelated, very common fixed idiom -- \"water breaking\" as in going into labor -- producing an unintentionally jarring misreading."),
    60: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"differ between manners\" for \"differ between species\" is nonsensical -- \"manners\" (ways of behaving/etiquette) does not substitute for a biological classification term."),
    61: ("SEVERE", ["FIXED_TERM_OR_IDIOM"], "\"reaction places\" breaks the specific fixed scientific term \"reaction centers\" (the protein complexes where light-driven reactions occur in photosynthesis); \"places\" is vague, non-standard terminology."),
    62: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"light landscape\" breaks the fixed physics term \"light spectrum\"; \"landscape\" (terrain/scenery) is an unrelated concept, producing a nonsensical compound."),
    63: ("SEVERE", ["FIXED_TERM_OR_IDIOM", "WRONG_WORD_OR_SENSE"], "\"cell-like respiration\" breaks the specific, standard biological term \"cellular respiration\"; \"-like\" subtly changes the claim from \"is this process\" to \"resembles this process\", an ontological shift, not just a wording change."),
    64: ("SEVERE", ["WRONG_WORD_OR_SENSE"], "\"The regime formed about 4.6 billion years ago\" -- \"regime\" (a government or a mode of operation) carries strong, jarring political/administrative connotations that are a poor fit for the physical formation of the Solar System."),
    65: ("MINOR", ["NATURALNESS_OR_REGISTER"], "\"after consumption of a protein-rich meal\" for \"subsequent consumption\" reads slightly less smoothly as a noun-phrase modifier, but the meaning is preserved."),
    66: ("SEVERE", ["WRONG_WORD_OR_SENSE", "FIXED_TERM_OR_IDIOM"], "Restructuring changes \"spun and woven\" to \"twisted and woven\" -- \"spun\" is the specific, historically-accurate textile-industry term for turning raw cotton fiber into thread; \"twisted\" is a related but different, non-standard description of this specific historical process."),
    67: ("CLEAN", ["CLEAN"], "\"local to global range\" for \"local to global scope\" is a valid, natural synonym."),
    68: ("SEVERE", ["GRAMMAR", "WRONG_WORD_OR_SENSE"], "\"information helps and resources\" is ungrammatical -- \"help\" does not standardly pluralize as a countable noun (\"helps\"); also loses the technical meaning of \"services\" in this networking context."),
}

assert len(LABELS) == 68, len(LABELS)
