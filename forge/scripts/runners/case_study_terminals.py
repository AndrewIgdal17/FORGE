"""Accepted terminal table for the bundled case studies, 2026-11-12.

Each runner copies one row onto project technical details. Do not look up
substations. ``sending_source`` stays ``margin``.
"""

SUNZIA = {
    "sending": {
        "gea": "WestConnect_South",
        "egrid_subregion": "AZNM",
        "state": "NM",
    },
    "receiving": {
        "gea": "WestConnect_South",
        "egrid_subregion": "AZNM",
        "state": "AZ",
    },
}

ERCOT = {
    "sending": {"gea": "ERCOT", "egrid_subregion": "ERCT", "state": "TX"},
    "receiving": {"gea": "ERCOT", "egrid_subregion": "ERCT", "state": "TX"},
}


def apply_terminals(inputs: dict, table: dict) -> None:
    """Copy a terminal row onto ``01_project_technical_details``."""
    technical = inputs["01_project_technical_details"]
    technical["terminals"] = {
        "sending": dict(table["sending"]),
        "receiving": dict(table["receiving"]),
    }
