from __future__ import annotations

# Family-level routing policy for the coarse regime-aware shortlist engine.
# These tables are intentionally simple and editable so a quad / route change
# only requires policy updates rather than scanner rewrites.

QUAD_POLICY: dict[str, dict[str, dict[str, list[str]]]] = {
    'Q1': {
        'us': {
            'boost': ['quality', 'quality_growth', 'growth', 'software_cyber', 'semis', 'defensives'],
            'cut': ['energy', 'materials', 'junk_structure', 'small_beta'],
            'short': ['junk_structure', 'small_beta'],
            'safe_harbor': ['quality', 'defensives'],
        },
        'ihsg': {
            'boost': ['banks', 'consumer_def', 'telco_infra', 'quality_largecap'],
            'cut': ['coal_energy', 'metals', 'special_board'],
            'short': ['special_board'],
            'safe_harbor': ['banks', 'consumer_def', 'telco_infra'],
        },
        'fx': {
            'boost': ['majors', 'defensive_usd'],
            'cut': ['commodity_fx', 'carry_beta'],
            'short': ['carry_beta'],
            'safe_harbor': ['majors', 'defensive_usd'],
        },
        'commodities': {
            'boost': ['precious', 'broad_proxy'],
            'cut': ['energy', 'industrial', 'agri_softs'],
            'short': ['industrial'],
            'safe_harbor': ['precious'],
        },
        'crypto': {
            'boost': ['btc_quality', 'majors', 'infra'],
            'cut': ['high_beta', 'meme_beta', 'micro_alt'],
            'short': ['high_beta', 'meme_beta', 'micro_alt'],
            'safe_harbor': ['btc_quality', 'majors'],
        },
    },
    'Q2': {
        'us': {
            'boost': ['growth', 'semis', 'software_cyber', 'industrials', 'brokers_alt', 'energy', 'cyclical_beta'],
            'cut': ['defensives'],
            'short': ['defensives'],
            'safe_harbor': ['quality'],
        },
        'ihsg': {
            'boost': ['banks', 'coal_energy', 'metals', 'consumer_cyc', 'quality_largecap'],
            'cut': ['consumer_def'],
            'short': ['special_board'],
            'safe_harbor': ['banks'],
        },
        'fx': {
            'boost': ['commodity_fx', 'carry_beta', 'majors'],
            'cut': ['defensive_usd'],
            'short': ['defensive_usd'],
            'safe_harbor': ['majors'],
        },
        'commodities': {
            'boost': ['energy', 'industrial', 'agri_softs'],
            'cut': ['precious'],
            'short': ['precious'],
            'safe_harbor': ['broad_proxy'],
        },
        'crypto': {
            'boost': ['majors', 'l1l2', 'defi', 'ai_data', 'infra', 'high_beta'],
            'cut': ['btc_quality'],
            'short': ['micro_alt'],
            'safe_harbor': ['btc_quality', 'majors'],
        },
    },
    'Q3': {
        'us': {
            'boost': ['defensives', 'quality', 'energy', 'materials'],
            'cut': ['consumer_cyc', 'small_beta', 'cyclical_beta', 'junk_structure'],
            'short': ['consumer_cyc', 'small_beta', 'cyclical_beta', 'junk_structure'],
            'safe_harbor': ['defensives', 'quality', 'energy'],
        },
        'ihsg': {
            'boost': ['coal_energy', 'metals', 'exporter', 'consumer_def', 'telco_infra'],
            'cut': ['consumer_cyc', 'import_sensitive', 'special_board'],
            'short': ['consumer_cyc', 'import_sensitive', 'special_board'],
            'safe_harbor': ['consumer_def', 'telco_infra', 'coal_energy'],
        },
        'fx': {
            'boost': ['defensive_usd', 'majors', 'commodity_fx'],
            'cut': ['carry_beta', 'asia_beta'],
            'short': ['carry_beta', 'asia_beta'],
            'safe_harbor': ['defensive_usd', 'majors'],
        },
        'commodities': {
            'boost': ['precious', 'energy'],
            'cut': ['industrial'],
            'short': ['industrial'],
            'safe_harbor': ['precious', 'energy'],
        },
        'crypto': {
            'boost': ['btc_quality', 'majors', 'infra'],
            'cut': ['high_beta', 'meme_beta', 'micro_alt'],
            'short': ['high_beta', 'meme_beta', 'micro_alt'],
            'safe_harbor': ['btc_quality', 'majors'],
        },
    },
    'Q4': {
        'us': {
            'boost': ['defensives', 'quality', 'duration_quality'],
            'cut': ['energy', 'industrials', 'consumer_cyc', 'small_beta', 'cyclical_beta', 'junk_structure'],
            'short': ['consumer_cyc', 'small_beta', 'cyclical_beta', 'junk_structure'],
            'safe_harbor': ['defensives', 'quality', 'duration_quality'],
        },
        'ihsg': {
            'boost': ['consumer_def', 'telco_infra', 'quality_largecap'],
            'cut': ['consumer_cyc', 'coal_energy', 'metals', 'special_board'],
            'short': ['consumer_cyc', 'special_board'],
            'safe_harbor': ['consumer_def', 'telco_infra', 'quality_largecap'],
        },
        'fx': {
            'boost': ['defensive_usd', 'majors'],
            'cut': ['carry_beta', 'commodity_fx', 'asia_beta'],
            'short': ['carry_beta', 'asia_beta'],
            'safe_harbor': ['defensive_usd', 'majors'],
        },
        'commodities': {
            'boost': ['precious'],
            'cut': ['energy', 'industrial', 'agri_softs'],
            'short': ['energy', 'industrial'],
            'safe_harbor': ['precious'],
        },
        'crypto': {
            'boost': ['btc_quality'],
            'cut': ['high_beta', 'meme_beta', 'micro_alt', 'l1l2', 'defi', 'ai_data'],
            'short': ['high_beta', 'meme_beta', 'micro_alt'],
            'safe_harbor': ['btc_quality', 'majors'],
        },
    },
}

SHORTLIST_POLICY: dict[str, dict[str, int]] = {
    'us': {'best_now': 80, 'safe_harbor': 55, 'next_route': 40, 'shorts': 55, 'alt_route': 20},
    'ihsg': {'best_now': 40, 'safe_harbor': 30, 'next_route': 20, 'shorts': 40, 'alt_route': 20},
    'fx': {'best_now': 6, 'safe_harbor': 4, 'next_route': 2, 'shorts': 2, 'alt_route': 2},
    'commodities': {'best_now': 10, 'safe_harbor': 6, 'next_route': 3, 'shorts': 3, 'alt_route': 2},
    'crypto': {'best_now': 70, 'safe_harbor': 35, 'next_route': 35, 'shorts': 40, 'alt_route': 20},
}

# Fallback diversification caps per family while selecting shortlist labels.
FAMILY_CAPS: dict[str, int] = {
    'us': 18,
    'ihsg': 16,
    'fx': 4,
    'commodities': 6,
    'crypto': 18,
}
