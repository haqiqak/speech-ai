"""
eval/r50p8_corpus.py -- R50 Phase 8: a NEW corpus of 54 real sentences,
verbatim from live Wikipedia articles on five topics NOT used anywhere in
R40-R49 (Photosynthesis, Solar System, Exercise, Industrial Revolution,
Internet) -- chosen specifically for causal/temporal/directional claim
density (a known source of FACTUAL_OR_LOGICAL_REVERSAL defects) and
register diversity, distinct from R40's ai/climate/cooking/smalltalk set.

Reuses R40's exact PROFILES (eval/ceiling_probe_r40.py) so results are
methodologically comparable to the R50 baseline, while guaranteeing zero
sentence-level overlap with any prior R-phase corpus.
"""
from __future__ import annotations

SENTENCES: list[tuple[str, str]] = [
    # -- Photosynthesis (biology, mechanism/causal register) --
    ("photosynthesis", "Photosynthesis is a system of biological processes by which photopigment-bearing autotrophic organisms, such as most plants, algae and cyanobacteria, convert light energy into the chemical energy necessary to fuel their metabolism."),
    ("photosynthesis", "The term photosynthesis usually refers to oxygenic photosynthesis, a process that releases oxygen as a byproduct of water splitting."),
    ("photosynthesis", "Photosynthesis plays a critical role in producing and maintaining the oxygen content of the Earth's atmosphere, and it supplies most of the biological energy necessary for complex life on Earth."),
    ("photosynthesis", "While the details may differ between species, the process always begins when light energy is absorbed by the reaction centers, proteins that contain photosynthetic pigments or chromophores."),
    ("photosynthesis", "In plants, these pigments are chlorophylls held inside chloroplasts, abundant in leaf cells."),
    ("photosynthesis", "Photosynthesis occurs in two stages."),
    ("photosynthesis", "In plants and algae, photosynthesis takes place in organelles called chloroplasts."),
    ("photosynthesis", "Plants absorb light primarily using the pigment chlorophyll."),
    ("photosynthesis", "The green part of the light spectrum is not absorbed but is reflected, which is the reason that most plants have a green color."),
    ("photosynthesis", "Carbon dioxide is converted into sugars in a process called carbon fixation."),
    ("photosynthesis", "In general outline, photosynthesis is the opposite of cellular respiration, while cellular respiration is the oxidation of carbohydrates to carbon dioxide."),
    ("photosynthesis", "Photosynthesis was discovered in 1779 by Jan Ingenhousz who showed that plants need light, not just soil and water."),
    # -- Solar System (astronomy, formal/technical register) --
    ("solar_system", "The Solar System is the gravitationally bound system of the Sun and the masses that orbit it, most prominently its eight planets, of which Earth is one."),
    ("solar_system", "The Solar System is an isolated single-star planetary system within the Milky Way Galaxy."),
    ("solar_system", "The system formed about 4.6 billion years ago when a dense region of a molecular cloud collapsed, creating the Sun and a protoplanetary disc from which the orbiting bodies assembled."),
    ("solar_system", "The Sun accounts for 99.86% of the Solar System's total mass."),
    ("solar_system", "Inside the Sun's core, hydrogen is fused into helium, releasing energy that is emitted through the Sun's photosphere."),
    ("solar_system", "Closest to the Sun in order of increasing distance are the terrestrial planets, Mercury, Venus, Earth and Mars."),
    ("solar_system", "Earth and Mars are the only planets that orbit within the Sun's habitable zone, in which sunlight can keep surface water liquid."),
    ("solar_system", "Jupiter and Saturn possess nearly 90% of the non-stellar mass of the Solar System."),
    ("solar_system", "The Solar System includes the Sun and all objects that are bound to it by gravity and orbit it."),
    ("solar_system", "As the pre-solar nebula collapsed, conservation of angular momentum caused it to rotate faster."),
    ("solar_system", "Hundreds of protoplanets may have existed in the early Solar System, but they either merged or were destroyed or ejected."),
    ("solar_system", "The Solar System formed at least 4.568 billion years ago from the gravitational collapse of a region within a large molecular cloud."),
    # -- Exercise (health, causal/statistical register) --
    ("exercise", "Exercise or working out is physical activity that enhances or maintains fitness and overall health."),
    ("exercise", "In terms of health benefits, usually, 150 minutes of moderate-intensity exercise per week is recommended for reducing the risk of health problems."),
    ("exercise", "Aerobic exercise is any physical activity that uses large muscle groups and causes the body to use more oxygen than it would while resting."),
    ("exercise", "A lack of physical activity causes approximately 6% of the burden of disease from coronary heart disease worldwide."),
    ("exercise", "Moderate exercise has been associated with a 29% decreased incidence of upper respiratory tract infections."),
    ("exercise", "Overtraining occurs when a person exceeds their body's ability to recover from strenuous exercise."),
    ("exercise", "Resistance training and subsequent consumption of a protein-rich meal promotes muscle hypertrophy and gains in muscle strength."),
    ("exercise", "The beneficial effect of exercise on the cardiovascular system is well documented."),
    ("exercise", "Aerobic exercise may affect both self-esteem and overall well-being with consistent, long term participation."),
    ("exercise", "Studies have shown that strenuous stress for long durations can suppress the immune system by decreasing the concentration of lymphocytes."),
    # -- Industrial Revolution (history, temporal/causal register) --
    ("industrial_revolution", "Beginning in Great Britain around 1760, the Industrial Revolution had spread to continental Europe and the United States by about 1840."),
    ("industrial_revolution", "Economic historians agree that the onset of the Industrial Revolution is the most important event in human history."),
    ("industrial_revolution", "This transition included going from hand production methods to machines, new chemical manufacturing and iron production processes, and the increasing use of steam power."),
    ("industrial_revolution", "By the mid-18th century, Britain was the leading commercial nation, with GDP per capita considerably over the world average."),
    ("industrial_revolution", "The textile industry was the first to use modern production methods, and textiles became the dominant industry in terms of employment."),
    ("industrial_revolution", "Rapid adoption of mechanized textile spinning occurred in Britain in the 1780s."),
    ("industrial_revolution", "Mechanised textile production spread from Britain to continental Europe and the US in the early 19th century."),
    ("industrial_revolution", "Prior to the Industrial Revolution, most manufacturing occurred in China and India; after the Industrial Revolution, most manufacturing took place in North America and Western Europe."),
    ("industrial_revolution", "The earliest recorded use of the phrase Industrial Revolution was in 1799 by a French envoy announcing that France had entered the race to industrialise."),
    ("industrial_revolution", "In 1750, Britain imported 2.5 million pounds of raw cotton, most of which was spun and woven by the cottage industry in Lancashire."),
    # -- Internet (technology, formal register) --
    ("internet", "The Internet is the global system of interconnected computer networks that uses the Internet protocol suite to communicate between networks and devices."),
    ("internet", "It is a network of networks that comprises private, public, academic, business, and government networks of local to global scope."),
    ("internet", "The Internet carries a vast range of information services and resources, such as the interlinked hypertext documents of the World Wide Web, electronic mail, and file sharing."),
    ("internet", "The Internet has no single centralized governance in either technological implementation or policies for access and usage."),
    ("internet", "Each constituent network sets its own policies."),
    ("internet", "The word internetted was used as early as 1849, meaning interconnected or interwoven."),
    ("internet", "In 1974, researchers published a proposal for a protocol for packet network intercommunication."),
    ("internet", "ARPANET development began with two network nodes which were interconnected between two research institutions on 29 October 1969."),
    ("internet", "By the end of 1971, 15 sites were connected to the young ARPANET, mainly in metropolitan areas of Los Angeles, San Francisco, and Boston."),
    ("internet", "The ARPANET was decommissioned in 1990."),
]

assert len(SENTENCES) == 54, len(SENTENCES)

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
