from random import shuffle
from typing import List

ADJECTIVES = [
    "Zingoid",
    "Quantum",
    "Double Quantum",
    "Electronic",
    "Fermion",
    "Solenoid",
    "Laser",
    "Giga",
    "Terra",
    "Mega",
    "Kilo",
    "Ferrite",
    "Golden",
    "Particle",
    "Deflection"
]

NOUNS = [
    "Reflux",
    "Valve",
    "Adjustor",
    "Laser",
    "Key",
    "Starter",
    "Stabilizer",
    "Accelerator",
    "Dish",
    "Visualizer",
    "Detector",
    "Coil",
    "Dynamo",
    "Generator"
]

def generate_names(n: int) -> List[str]:
    adj_idx = list(range(n))
    shuffle(adj_idx)
    noun_idx = list(range(n))
    shuffle(noun_idx)
    pairs = zip(adj_idx, noun_idx)

    return [f"{ADJECTIVES[adj]} {NOUNS[noun]}" for adj, noun in pairs]
