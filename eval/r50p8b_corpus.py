"""
eval/r50p8b_corpus.py -- R50 Phase 8B, task 1: a second NEW corpus of 42
real sentences, verbatim from live Wikipedia articles on four topics not
used anywhere in R40-R50 or Phase 8 (Vaccine, Plate Tectonics,
Antimicrobial Resistance, Supply and Demand) -- chosen specifically to
maximize causal/directional/physical-relationship claim density (the
exact property that predicts FACTUAL_OR_LOGICAL_REVERSAL), to test
whether that defect class occurs organically often enough to matter.

Reuses R40's exact PROFILES for methodological consistency.
"""
from __future__ import annotations

SENTENCES: list[tuple[str, str]] = [
    # -- Vaccine (immunology, causal/temporal register) --
    ("vaccine", "A vaccine is a biological preparation that provides active acquired immunity to a particular infectious disease."),
    ("vaccine", "The agent stimulates the immune system to recognize the agent as a threat, destroy it, and recognize further and destroy any of the microorganisms associated with that agent that it may encounter in the future."),
    ("vaccine", "Vaccination is the most effective method of preventing infectious diseases."),
    ("vaccine", "Widespread immunity due to vaccination is largely responsible for the worldwide eradication of smallpox and the restriction of diseases such as polio, measles, and tetanus from much of the world."),
    ("vaccine", "The first recorded use of inoculation to prevent smallpox occurred in the 16th century in China, with the earliest hints of the practice in China coming during the 10th century."),
    ("vaccine", "It was also the first disease for which a vaccine was produced."),
    ("vaccine", "The folk practice of inoculation against smallpox was brought from Turkey to Britain in 1721 by Lady Mary Wortley Montagu."),
    ("vaccine", "He used the phrase in 1798 for the long title of his inquiry, in which he described the protective effect of cowpox against smallpox."),
    ("vaccine", "In 1881, to honor Jenner, Louis Pasteur proposed that the terms should be extended to cover the new protective inoculations then being developed."),
    ("vaccine", "The immune system recognizes vaccine agents as foreign, destroys them, and remembers them."),
    ("vaccine", "When the virulent version of an agent is encountered, the body recognizes the protein coat on the agent, and thus is prepared to respond."),
    ("vaccine", "Vaccines led to the eradication of smallpox, one of the most contagious and deadly diseases in humans."),
    # -- Plate Tectonics (geology, mechanism/causal register) --
    ("plate_tectonics", "Plate tectonics is the scientific theory that Earth's lithosphere comprises a number of large tectonic plates, which have been slowly moving since 3 to 4 billion years ago."),
    ("plate_tectonics", "The model builds on the concept of continental drift, an idea developed during the first decades of the 20th century."),
    ("plate_tectonics", "Plate tectonics came to be accepted by geoscientists after seafloor spreading was validated in the mid to late 1960s."),
    ("plate_tectonics", "The processes that result in plates and shape Earth's crust are called tectonics."),
    ("plate_tectonics", "Where the plates meet, their relative motion determines the type of plate boundary, convergent, divergent, or transform."),
    ("plate_tectonics", "The relative movement of the plates typically ranges from zero to 10 centimeters annually."),
    ("plate_tectonics", "Tectonic plates are relatively rigid and float across the ductile asthenosphere beneath."),
    ("plate_tectonics", "At a subduction zone, the relatively cold, dense oceanic crust sinks down into the mantle, forming the downward convecting limb of a mantle cell, which is the strongest driver of plate motion."),
    ("plate_tectonics", "The lithosphere is cooler and more rigid, while the asthenosphere is hotter and flows more easily."),
    ("plate_tectonics", "Oceanic crust is denser than continental crust because it has less silicon and more of the heavier elements than continental crust."),
    # -- Antimicrobial resistance (biology, causal/mechanism register) --
    ("antimicrobial_resistance", "Misuse and improper management of antimicrobials are primary drivers of this resistance, though it can also occur naturally through genetic mutations."),
    ("antimicrobial_resistance", "Resistance arises through spontaneous mutation, horizontal gene transfer, and increased selective pressure from antibiotic overuse, which accelerates resistance development."),
    ("antimicrobial_resistance", "Antimicrobial resistance is driven largely by the misuse and overuse of antimicrobials."),
    ("antimicrobial_resistance", "Microbes may naturally develop resistance through genetic mutations that occur during cell division."),
    ("antimicrobial_resistance", "With the increased use of antimicrobial agents, there is a speeding up of this natural process."),
    ("antimicrobial_resistance", "These inappropriate uses of antimicrobial agents promote the evolution of antimicrobial resistance by supporting the bacteria in developing genetic alterations that lead to resistance."),
    ("antimicrobial_resistance", "Overuse of disinfectants can lead to mutations that induce antimicrobial resistance."),
    ("antimicrobial_resistance", "This process, known as horizontal gene transfer, allows resistance genes to spread rapidly between different bacterial species."),
    ("antimicrobial_resistance", "Natural selection means that organisms that are able to adapt to their environment survive and continue to produce offspring."),
    ("antimicrobial_resistance", "Drug inactivation or modification occurs through enzymatic deactivation of penicillin in some penicillin-resistant bacteria."),
    # -- Supply and demand (economics, directional/causal register) --
    ("supply_and_demand", "It postulates that, holding all else equal, the unit price for a particular good in a perfectly competitive market will vary until it settles at the market-clearing price."),
    ("supply_and_demand", "A rise in the cost of raw materials would decrease supply, shifting the supply curve to the left because at each possible price a smaller quantity would be supplied."),
    ("supply_and_demand", "A fall in production costs would increase supply, shifting the supply curve to the right or down."),
    ("supply_and_demand", "Generally, consumers will buy an additional unit as long as the marginal value of the extra unit is more than the market price they pay."),
    ("supply_and_demand", "According to the law of demand, the demand curve is always downward-sloping, meaning that as the price decreases, consumers will buy more of the good."),
    ("supply_and_demand", "When consumers increase the quantity demanded at a given price, it is referred to as an increase in demand."),
    ("supply_and_demand", "As a result of a supply curve shift, the price and the quantity move in opposite directions."),
    ("supply_and_demand", "If the quantity supplied decreases, the opposite happens."),
    ("supply_and_demand", "The demand for money intersects with the money supply to determine the interest rate."),
    ("supply_and_demand", "If desire for goods increases while its availability decreases, its price rises."),
]

assert len(SENTENCES) == 42, len(SENTENCES)

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
