from __future__ import annotations

"""Manual IHSG structural-risk registry.

This is intentionally conservative and confidence-aware because some public
article-level inputs can be directionally useful while still containing
conflicting numbers. The registry is therefore treated as an override layer,
not a hard source of truth.
"""

IHSG_STRUCTURAL_REGISTRY: dict[str, dict[str, float | str | bool]] = {
    # High-concentration / low-float names explicitly discussed in the article set.
    "BREN.JK": {
        "hsc": 0.9731,
        "free_float": 0.1229,
        "msci_fragility": 0.85,
        "ownership_opacity": 0.65,
        "manual_flag": "High HSC / low float / MSCI fragile",
        "data_confidence": 0.70,
        "source_conflict": True,
        "as_of": "2026-03-31",
    },
    "DSSA.JK": {
        "hsc": 0.9576,
        "free_float": 0.0424,
        "msci_fragility": 0.95,
        "ownership_opacity": 0.70,
        "manual_flag": "Very high HSC / very low float / MSCI fragile",
        "data_confidence": 0.85,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "ROCK.JK": {
        "hsc": 0.9985,
        "free_float": 0.0015,
        "msci_fragility": 0.90,
        "ownership_opacity": 0.75,
        "manual_flag": "Extreme HSC / ultra-low float",
        "data_confidence": 0.80,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "IFSH.JK": {
        "hsc": 0.9977,
        "free_float": 0.0023,
        "msci_fragility": 0.88,
        "ownership_opacity": 0.72,
        "manual_flag": "Extreme HSC / ultra-low float",
        "data_confidence": 0.78,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "SOTS.JK": {
        "hsc": 0.9835,
        "free_float": 0.0165,
        "msci_fragility": 0.82,
        "ownership_opacity": 0.68,
        "manual_flag": "Very high HSC / thin float",
        "data_confidence": 0.78,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "AGII.JK": {
        "hsc": 0.9775,
        "free_float": 0.0225,
        "msci_fragility": 0.80,
        "ownership_opacity": 0.64,
        "manual_flag": "High HSC / low float",
        "data_confidence": 0.76,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "MGLV.JK": {
        "hsc": 0.9594,
        "free_float": 0.0406,
        "msci_fragility": 0.78,
        "ownership_opacity": 0.62,
        "manual_flag": "High HSC / low float",
        "data_confidence": 0.75,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "LUCY.JK": {
        "hsc": 0.9574,
        "free_float": 0.0426,
        "msci_fragility": 0.74,
        "ownership_opacity": 0.60,
        "manual_flag": "High HSC / low float",
        "data_confidence": 0.74,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
    "RLCO.JK": {
        "hsc": 0.9535,
        "free_float": 0.0465,
        "msci_fragility": 0.74,
        "ownership_opacity": 0.60,
        "manual_flag": "High HSC / low float",
        "data_confidence": 0.74,
        "source_conflict": False,
        "as_of": "2026-03-31",
    },
}

# Institution-friendly candidates used only for a small rotation boost when the
# broader IHSG backdrop is supportive and foreign/clean-float rotation is likely.
IHSG_CLEAN_FLOAT_BENEFICIARIES: list[str] = [
    "BBCA.JK",
    "BBRI.JK",
    "BMRI.JK",
    "BBNI.JK",
    "TLKM.JK",
    "ASII.JK",
    "ICBP.JK",
    "INDF.JK",
    "AMRT.JK",
    "KLBF.JK",
    "CPIN.JK",
    "JSMR.JK",
    "PGAS.JK",
    "EXCL.JK",
    "ISAT.JK",
    "UNTR.JK",
    "AKRA.JK",
]
