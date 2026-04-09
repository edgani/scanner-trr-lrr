from __future__ import annotations


def build_transmission_sections(shared_core: dict, native_features: dict) -> dict:
    regime = shared_core.get('regime_stack', {}) or {}
    resolved = regime.get('resolved', {}) or {}
    structural_quad = regime.get('structural', {}).get('quad', shared_core.get('regime', {}).get('current_quad', 'Q?'))
    structural_next = regime.get('structural', {}).get('next_quad', structural_quad)
    monthly_quad = regime.get('monthly', {}).get('quad', structural_quad)
    monthly_next = regime.get('monthly', {}).get('next_quad', monthly_quad)
    dominant_horizon = resolved.get('dominant_horizon', 'aligned')
    operating = resolved.get('operating_regime', f'Monthly {monthly_quad} inside Structural {structural_quad}')
    scenario_flags = set(shared_core.get('scenario_flags', []))
    petrodollar_score = float(shared_core.get('petrodollar', {}).get('score', 0.5))
    petrodollar_state = str(shared_core.get('petrodollar', {}).get('state', 'normal'))
    em_rotation = shared_core.get('em_rotation', {}) or {}
    next_path = shared_core.get('next_path', {}) or {}

    def packet(paths, dominant, confirm, conflict, market, monthly_trigger, structural_route):
        next_route = str((next_path.get('market_routes', {}) or {}).get(market, next_path.get('next_resolved_regime', '-')))
        return {
            'paths': paths,
            'dominant': dominant,
            'confirm': confirm,
            'conflict': conflict,
            'market': market,
            'structural_quad': structural_quad,
            'monthly_quad': monthly_quad,
            'operating_regime': operating,
            'dominant_horizon': dominant_horizon,
            'structural_route': structural_route,
            'monthly_trigger': monthly_trigger,
            'petrodollar_state': petrodollar_state,
            'petrodollar_score': petrodollar_score,
            'energy_dollar_feedback': petrodollar_score if 'petrodollar_shock' in scenario_flags else 0.45 * petrodollar_score,
            'resolved_em_rotation': em_rotation.get('resolved_state', em_rotation.get('state', 'selective')),
            'em_next_route': em_rotation.get('next_route', '-'),
            'petrodollar_chain': shared_core.get('petrodollar', {}).get('chain', []),
            'structural_paths': [f'Structural {structural_quad}: {structural_route}', 'backbone route / family preference'],
            'monthly_paths': [f'Monthly {monthly_quad}: {monthly_trigger}', 'tactical trigger / acceleration path'],
            'resolved_paths': [f'Operating regime: {operating}', f'dominant horizon: {dominant_horizon}'],
            'next_route': next_route,
            'next_structural_quad': structural_next,
            'next_monthly_quad': monthly_next,
        }

    us = packet(
        ['structural quad -> sector/style backbone', 'monthly quad -> tactical rotation speed', 'rates -> real yields -> style rotation', 'credit -> breadth -> equities', 'USD -> multinational earnings sensitivity'],
        ['structural regime', 'monthly overlay', 'rates', 'breadth', 'credit'],
        ['equal-weight', 'small caps', 'sector breadth', f'operating regime: {operating}'],
        ['narrow rally', 'credit worsening', 'monthly pulse fails'],
        'us',
        'monthly Q3 usually favors selective energy / hard-asset / defensive-growth mix before broader cyclicals.',
        'structural quad sets whether beta should be embraced or faded.',
    )
    ihsg = packet(
        ['structural quad -> EM / commodity backdrop', 'monthly quad -> exporter vs domestic pulse', 'DXY -> USD/IDR -> foreign flow -> IHSG', 'UST -> SBN -> valuation pressure', 'commodities -> resource complex -> index support'],
        ['USD/IDR', 'foreign flow', 'commodities', 'EM rotation'],
        ['heavyweights', 'banks', 'breadth', f'EM resolved: {em_rotation.get("resolved_state", em_rotation.get("state", "selective"))}'],
        ['EM stress', 'yield pressure', 'monthly commodity pulse fades'],
        'ihsg',
        'monthly pulse decides whether banks/resources can still lead tactically.',
        'structural route decides if IHSG should be treated as exporter/carry beneficiary or fragile EM beta.',
    )
    fx = packet(
        ['structural quad -> DXY / funding backdrop', 'monthly quad -> pair dispersion and carry unwind risk', 'rate diff -> pair direction', 'macro surprise -> rate repricing', 'intervention -> fragility'],
        ['rates', 'macro surprise', 'intervention', 'funding'],
        ['positioning', 'options', 'session liquidity', f'petrodollar {petrodollar_state}'],
        ['crowded carry', 'policy shock', 'funding squeeze'],
        'fx',
        'monthly quad identifies cleaner expression pairs; structural quad sets whether USD is backdrop headwind or relief.',
        'structural route decides carry vs funding winners.',
    )
    commodities = packet(
        ['structural quad -> family preference', 'monthly quad -> prompt inflation / squeeze pulse', 'USD/rates -> macro money pressure', 'inventory -> curve -> prompt tightness', 'oil/gold/silver -> equities and inflation chain'],
        ['USD', 'inventory', 'curve', 'petrodollar'],
        ['family breadth', 'prompt spreads', f'petrodollar {petrodollar_state}'],
        ['growth scare', 'fund unwind', 'oil rollback'],
        'commodities',
        'monthly trigger decides whether this is a broad commodity push or just energy/gold tactical burst.',
        'structural route decides family hierarchy: precious vs energy vs industrials.',
    )
    crypto = packet(
        ['structural quad -> liquidity / beta backdrop', 'monthly quad -> breadth and leverage pulse', 'liquidity -> beta -> crypto', 'stablecoin flow -> spot demand', 'unlock -> sell pressure -> fragility'],
        ['liquidity', 'flow', 'unlock', 'Nasdaq/growth beta'],
        ['majors breadth', 'sector breadth', f'operating regime: {operating}'],
        ['funding heat', 'fragile order books', 'structural risk-off dominates'],
        'crypto',
        'monthly quad decides if breadth can broaden beyond majors or stays tactical only.',
        'structural route decides if crypto should be treated as real risk-on beta or just selective tactical bounce.',
    )

    return {'us': us, 'ihsg': ihsg, 'fx': fx, 'commodities': commodities, 'crypto': crypto}
