"""
eval/step3_gencheck_corpus.py -- Architecture Go/No-Go Step 3, generalization
check: a small (18-sentence), frozen, contamination-checked corpus of
GENUINELY NEW material -- every prior evaluation since Phase 10 (Phase
11/11B/11C, Architecture Gate 1, Step 2) re-verified the SAME frozen R10
corpus, so none of it is evidence about unseen input. This is not a
Phase-10-scale stress test; it is a targeted, honest check for one
specific named criterion in the formal architecture assessment.

Technical half (10 sentences, Wikipedia, fetched live for this check):
5 topics never used in any prior R-phase (checked against R10's own
topic list -- digestive system, nutrition, chemical reaction, Newton's
laws, star, volcano, renewable energy, algorithm, probability,
inflation, civil engineering, Alexander Fleming -- and Phase 8/8B's
topics -- photosynthesis, vaccine, plate tectonics, antimicrobial
resistance, supply and demand): Immune system, Electrical network,
Cellular respiration, Machine learning, Interest rate.

[LIMITATION, disclosed per Practice.md's evidence-tagging discipline]
6 of the 10 (G1, G4, G6, G8, G9, G10) are exactly verbatim. The other 4
(G2, G3, G5, G7) had a parenthetical example list or abbreviation (e.g.
"(ATP)", "(ML)", "(e.g., batteries, resistors...)") dropped from the
live-fetched sentence for brevity before use here -- the surrounding
wording is otherwise unedited. This was not disclosed when the corpus
was first built; recorded now, before any results are reported on it.

General half (8 sentences, hand-authored, disclosed as such -- same
methodology R10 used for its own general half): everyday scenarios,
freshly written for this check, not reused from any test fixture or
prior corpus in this repository.
"""

CORPUS = [
    # -- technical: Immune system (verbatim Wikipedia, fetched 2026-08-27) --
    {"id": "G1", "domain": "technical", "topic": "Immune system",
     "text": "The immune system is a network of biological systems that protects an organism from diseases."},
    {"id": "G2", "domain": "technical", "topic": "Immune system",
     "text": "It detects and responds to a wide variety of pathogens, such as viruses, bacteria, and parasites, as well as cancer cells and foreign objects, such as wood splinters, distinguishing them from the organism's own healthy tissue."},

    # -- technical: Electrical network (verbatim Wikipedia) --
    {"id": "G3", "domain": "technical", "topic": "Electrical network",
     "text": "An electrical network is an interconnection of electrical components or a model of such an interconnection, consisting of electrical elements such as voltage sources, current sources, resistances, inductances, and capacitances."},
    {"id": "G4", "domain": "technical", "topic": "Electrical network",
     "text": "An electrical circuit is a network consisting of a closed loop, giving a return path for the current."},

    # -- technical: Cellular respiration (verbatim Wikipedia) --
    {"id": "G5", "domain": "technical", "topic": "Cellular respiration",
     "text": "Cellular respiration is the process of oxidizing biological fuels using an inorganic electron acceptor, such as oxygen, to drive production of adenosine triphosphate, which stores chemical energy in a biologically accessible form."},
    {"id": "G6", "domain": "technical", "topic": "Cellular respiration",
     "text": "Cellular respiration may be described as a set of metabolic reactions and processes that take place in the cells to transfer chemical energy from nutrients to ATP, with the flow of electrons to an electron acceptor, and then release waste products."},

    # -- technical: Machine learning (verbatim Wikipedia) --
    {"id": "G7", "domain": "technical", "topic": "Machine learning",
     "text": "Machine learning is a field of study in artificial intelligence concerned with the development and study of statistical algorithms that can learn from data and generalize to unseen data, and thus perform tasks without being explicitly programmed."},
    {"id": "G8", "domain": "technical", "topic": "Machine learning",
     "text": "Advances in the field of deep learning have allowed neural networks, a class of statistical algorithms, to surpass many previous machine learning approaches in performance."},

    # -- technical: Interest rate (verbatim Wikipedia) --
    {"id": "G9", "domain": "technical", "topic": "Interest rate",
     "text": "An interest rate is the amount of interest due per period, as a proportion of the amount lent, deposited, or borrowed."},
    {"id": "G10", "domain": "technical", "topic": "Interest rate",
     "text": "Alongside interest rates, three other variables determine total interest: principal sum, compounding frequency, and length of time."},

    # -- general (hand-authored, disclosed, freshly written for this check) --
    {"id": "G11", "domain": "general", "topic": "community",
     "text": "Our neighbor volunteered to organize the community garden project this summer."},
    {"id": "G12", "domain": "general", "topic": "travel",
     "text": "The airline announced that all flights would be delayed because of the storm."},
    {"id": "G13", "domain": "general", "topic": "hobby",
     "text": "She practiced the piano every evening after finishing her homework."},
    {"id": "G14", "domain": "general", "topic": "work",
     "text": "The committee postponed its decision until they could review the budget more carefully."},
    {"id": "G15", "domain": "general", "topic": "daily_life",
     "text": "He accidentally locked his keys inside the car while running errands downtown."},
    {"id": "G16", "domain": "general", "topic": "food",
     "text": "The restaurant introduced a new seasonal menu featuring locally grown vegetables."},
    {"id": "G17", "domain": "general", "topic": "home",
     "text": "They spent the weekend repainting the fence and trimming the overgrown hedges."},
    {"id": "G18", "domain": "general", "topic": "sports",
     "text": "The coach reminded the team to stay hydrated during the long practice session."},
]

# Two profiles per sentence: a typical single/double-declared-word case,
# and a denser mixed profile (matches the focus of Steps 1-2, where
# dense profiles are where recent changes concentrated).
RUN_PLAN = [
    {"id": "G1",  "profile_type": "core_word",   "words": ["network"]},
    {"id": "G1",  "profile_type": "dense_mixed", "words": ["organism"], "sounds": ["pr"]},
    {"id": "G2",  "profile_type": "core_word",   "words": ["pathogens"]},
    {"id": "G2",  "profile_type": "dense_mixed", "words": ["distinguishing", "parasites"], "sounds": ["s"]},
    {"id": "G3",  "profile_type": "core_word",   "words": ["interconnection"]},
    {"id": "G3",  "profile_type": "dense_mixed", "words": ["components", "elements"], "sounds": ["k"]},
    {"id": "G4",  "profile_type": "core_word",   "words": ["circuit"]},
    {"id": "G4",  "profile_type": "dense_mixed", "words": ["consisting"], "sounds": ["r"]},
    {"id": "G5",  "profile_type": "core_word",   "words": ["oxidizing"]},
    {"id": "G5",  "profile_type": "dense_mixed", "words": ["accessible", "production"], "sounds": ["pr"]},
    {"id": "G6",  "profile_type": "core_word",   "words": ["metabolic"]},
    {"id": "G6",  "profile_type": "dense_mixed", "words": ["transfer", "release"], "sounds": ["r"]},
    {"id": "G7",  "profile_type": "core_word",   "words": ["algorithms"]},
    {"id": "G7",  "profile_type": "dense_mixed", "words": ["generalize", "explicitly"], "sounds": ["g"]},
    {"id": "G8",  "profile_type": "core_word",   "words": ["approaches"]},
    {"id": "G8",  "profile_type": "dense_mixed", "words": ["advances", "surpass"], "sounds": ["s"]},
    {"id": "G9",  "profile_type": "core_word",   "words": ["proportion"]},
    {"id": "G9",  "profile_type": "dense_mixed", "words": ["deposited", "borrowed"], "sounds": ["d"]},
    {"id": "G10", "profile_type": "core_word",   "words": ["frequency"]},
    {"id": "G10", "profile_type": "dense_mixed", "words": ["variables", "determine"], "sounds": ["d"]},
    {"id": "G11", "profile_type": "core_word",   "words": ["volunteered"]},
    {"id": "G11", "profile_type": "dense_mixed", "words": ["organize", "community"], "sounds": ["g"]},
    {"id": "G12", "profile_type": "core_word",   "words": ["announced"]},
    {"id": "G12", "profile_type": "dense_mixed", "words": ["delayed"], "sounds": ["s"]},
    {"id": "G13", "profile_type": "core_word",   "words": ["practiced"]},
    {"id": "G13", "profile_type": "dense_mixed", "words": ["finishing"], "sounds": ["pr"]},
    {"id": "G14", "profile_type": "core_word",   "words": ["postponed"]},
    {"id": "G14", "profile_type": "dense_mixed", "words": ["carefully", "committee"], "sounds": ["k"]},
    {"id": "G15", "profile_type": "core_word",   "words": ["accidentally"]},
    {"id": "G15", "profile_type": "dense_mixed", "words": ["errands"], "sounds": ["r"]},
    {"id": "G16", "profile_type": "core_word",   "words": ["introduced"]},
    {"id": "G16", "profile_type": "dense_mixed", "words": ["seasonal", "locally"], "sounds": ["l"]},
    {"id": "G17", "profile_type": "core_word",   "words": ["overgrown"]},
    {"id": "G17", "profile_type": "dense_mixed", "words": ["repainting", "trimming"], "sounds": ["r"]},
    {"id": "G18", "profile_type": "core_word",   "words": ["hydrated"]},
    {"id": "G18", "profile_type": "dense_mixed", "words": ["reminded", "practice"], "sounds": ["r"]},
]
