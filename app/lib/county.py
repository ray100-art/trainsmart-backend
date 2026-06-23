"""Normalize Kenya county names for consistent access-control matching."""


def normalize_county(county: str) -> str:
    """Title-case county for storage and comparison (e.g. 'nairobi' -> 'Nairobi')."""
    county = county.strip()
    if not county:
        return county
    # Handle special cases with apostrophe
    replacements = {
        "muranga": "Murang'a",
        "murang'a": "Murang'a",
        "elgeyo marakwet": "Elgeyo-Marakwet",
        "elgeyo-marakwet": "Elgeyo-Marakwet",
        "homa bay": "Homa Bay",
        "taita taveta": "Taita-Taveta",
        "taita-taveta": "Taita-Taveta",
        "tana river": "Tana River",
        "tharaka nithi": "Tharaka-Nithi",
        "tharaka-nithi": "Tharaka-Nithi",
        "trans nzoia": "Trans Nzoia",
        "uasin gishu": "Uasin Gishu",
        "west pokot": "West Pokot",
    }
    key = county.lower().replace("_", " ")
    if key in replacements:
        return replacements[key]
    return county.title()
