import random

PREFIXES = {
    "tech": ["Cyber", "Neon", "Quantum", "Digital", "Nano", "Hyper"],
    "dark": ["Shadow", "Void", "Obsidian", "Phantom", "Night", "Hex"],
    "metal": ["Iron", "Steel", "Chrome", "Titan", "Silver"],
    "sci_fi": ["Nova", "Orbit", "Stellar", "Cosmic", "Ion"]
}

SUFFIXES = {
    "systems": ["Core", "Protocol", "Matrix", "Node", "Engine"],
    "motion": ["Drift", "Flux", "Pulse", "Wave"],
    "entities": ["Raven", "Wolf", "Ghost", "Sentinel"],
    "forge": ["Forge", "Foundry", "Anvil"]
}

def generate_name(
    prefix_styles=("tech", "dark", "metal", "sci_fi"),
    suffix_styles=("systems", "motion", "entities", "forge"),
    number_range=(10, 99),
    separator="",
    uppercase=False
):
    # Build active pools
    prefixes = [p for style in prefix_styles for p in PREFIXES[style]]
    suffixes = [s for style in suffix_styles for s in SUFFIXES[style]]

    name = random.choice(prefixes) + separator + random.choice(suffixes)
    number = random.randint(*number_range)

    final_name = f"{name}{number}"

    return final_name.upper() if uppercase else final_name


# Examples
print(generate_name())
