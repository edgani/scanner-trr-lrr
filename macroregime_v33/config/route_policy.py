from __future__ import annotations

# Route overlays sit on top of the quad policy.
ROUTE_POLICY: dict[str, dict[str, dict[str, list[str]]]] = {
    'quality_disinflation': {
        'us': {'boost': ['quality', 'quality_growth', 'duration_quality', 'defensives'], 'short': ['junk_structure', 'small_beta']},
        'ihsg': {'boost': ['banks', 'consumer_def', 'telco_infra'], 'short': ['special_board']},
        'fx': {'boost': ['majors', 'defensive_usd'], 'short': ['carry_beta']},
        'commodities': {'boost': ['precious'], 'short': ['energy']},
        'crypto': {'boost': ['btc_quality', 'majors'], 'short': ['micro_alt', 'meme_beta']},
    },
    'reflation_reaccel': {
        'us': {'boost': ['growth', 'semis', 'industrials', 'energy', 'cyclical_beta', 'brokers_alt'], 'short': ['defensives']},
        'ihsg': {'boost': ['banks', 'coal_energy', 'metals', 'consumer_cyc'], 'short': ['consumer_def']},
        'fx': {'boost': ['commodity_fx', 'carry_beta'], 'short': ['defensive_usd']},
        'commodities': {'boost': ['energy', 'industrial', 'agri_softs'], 'short': ['precious']},
        'crypto': {'boost': ['majors', 'l1l2', 'ai_data', 'infra', 'high_beta'], 'short': ['btc_quality']},
    },
    'stagflation_persist': {
        'us': {'boost': ['energy', 'materials', 'defensives', 'quality'], 'short': ['consumer_cyc', 'small_beta', 'junk_structure']},
        'ihsg': {'boost': ['coal_energy', 'metals', 'exporter', 'consumer_def'], 'short': ['import_sensitive', 'consumer_cyc', 'special_board']},
        'fx': {'boost': ['defensive_usd', 'commodity_fx'], 'short': ['asia_beta', 'carry_beta']},
        'commodities': {'boost': ['energy', 'precious'], 'short': ['industrial']},
        'crypto': {'boost': ['btc_quality', 'majors'], 'short': ['high_beta', 'meme_beta', 'micro_alt']},
    },
    'growth_scare': {
        'us': {'boost': ['defensives', 'quality', 'duration_quality'], 'short': ['consumer_cyc', 'industrials', 'small_beta', 'cyclical_beta']},
        'ihsg': {'boost': ['consumer_def', 'telco_infra', 'quality_largecap'], 'short': ['consumer_cyc', 'coal_energy', 'metals', 'special_board']},
        'fx': {'boost': ['defensive_usd', 'majors'], 'short': ['carry_beta', 'asia_beta']},
        'commodities': {'boost': ['precious'], 'short': ['energy', 'industrial']},
        'crypto': {'boost': ['btc_quality'], 'short': ['high_beta', 'meme_beta', 'micro_alt', 'l1l2', 'defi']},
    },
    'deflationary_riskoff': {
        'us': {'boost': ['defensives', 'quality', 'duration_quality'], 'short': ['energy', 'industrials', 'consumer_cyc', 'small_beta', 'junk_structure']},
        'ihsg': {'boost': ['consumer_def', 'telco_infra'], 'short': ['special_board', 'consumer_cyc']},
        'fx': {'boost': ['defensive_usd', 'majors'], 'short': ['carry_beta', 'commodity_fx', 'asia_beta']},
        'commodities': {'boost': ['precious'], 'short': ['energy', 'industrial', 'agri_softs']},
        'crypto': {'boost': ['btc_quality'], 'short': ['high_beta', 'meme_beta', 'micro_alt']},
    },
    'panic_crash': {
        'us': {'boost': ['defensives', 'quality'], 'short': ['consumer_cyc', 'small_beta', 'cyclical_beta', 'junk_structure']},
        'ihsg': {'boost': ['consumer_def', 'quality_largecap'], 'short': ['special_board', 'consumer_cyc', 'import_sensitive']},
        'fx': {'boost': ['defensive_usd'], 'short': ['carry_beta', 'asia_beta', 'commodity_fx']},
        'commodities': {'boost': ['precious'], 'short': ['energy', 'industrial']},
        'crypto': {'boost': ['btc_quality'], 'short': ['high_beta', 'meme_beta', 'micro_alt', 'l1l2', 'defi', 'ai_data']},
    },
    'vshape_rebound': {
        'us': {'boost': ['growth', 'semis', 'software_cyber', 'cyclical_beta'], 'short': ['defensives']},
        'ihsg': {'boost': ['banks', 'consumer_cyc', 'quality_largecap'], 'short': ['special_board']},
        'fx': {'boost': ['carry_beta', 'commodity_fx'], 'short': ['defensive_usd']},
        'commodities': {'boost': ['energy', 'industrial'], 'short': ['precious']},
        'crypto': {'boost': ['majors', 'l1l2', 'ai_data', 'high_beta'], 'short': ['btc_quality']},
    },
}
