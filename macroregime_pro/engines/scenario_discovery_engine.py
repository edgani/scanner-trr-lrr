from __future__ import annotations
from typing import Dict, List

from domain.types import ScenarioCase
from utils.math_utils import normalize_dict


class ScenarioDiscoveryEngine:
    def run(
        self,
        structural: Dict[str, float],
        tactical: Dict[str, float],
        shock: Dict[str, float],
        scenario_flags: Dict[str, float] | None,
        playbooks: List[Dict[str, object]],
        analogs: List[Dict[str, object]] | None = None,
        news_state: Dict[str, object] | None = None,
    ) -> Dict[str, ScenarioCase]:
        structural_quad = structural.get('structural_quad', structural.get('current_quad', 'Q?'))
        structural_next = structural.get('structural_next_quad', structural.get('next_quad', structural_quad))
        monthly_quad = structural.get('monthly_quad', structural_quad)
        monthly_next = structural.get('monthly_next_quad', monthly_quad)
        divergence = structural.get('divergence_state', 'aligned' if structural_quad == monthly_quad else 'divergent')
        operating = structural.get('operating_regime', f"Monthly {monthly_quad} inside Structural {structural_quad}" if divergence != 'aligned' else f"Aligned {structural_quad}")

        weather = tactical['weather_bias']
        hazard = float(structural.get('flip_hazard', 0.5))
        tactical_score = float(tactical.get('score', 0.5))
        confirm = float(tactical.get('cross_asset_confirm', 0.5))
        shock_strength = float(shock.get('override_strength', 0.0))
        shock_state = str(shock.get('state', 'normal'))
        news = news_state or {}
        flags = scenario_flags or {}
        war_h = float(news.get('war_oil_hazard', 0.0))
        pol_h = float(news.get('policy_pressure_hazard', 0.0))
        rel_h = float(news.get('relief_hazard', 0.0))

        raw: Dict[str, float] = {}
        if divergence == 'aligned':
            raw[f'Base: aligned {structural_quad} continuation'] = 0.34 + 0.18 * float(structural.get('structural_confidence', structural.get('confidence', 0.5)))
            raw[f'Alt: tactical move toward {structural_next}'] = 0.18 + 0.18 * hazard + 0.10 * confirm + 0.08 * rel_h
            raw['Family: shock branch'] = 0.12 + 0.22 * shock_strength + 0.08 * war_h
            raw['Family: broadening leadership'] = 0.12 + 0.15 * confirm + 0.06 * rel_h
            raw['Family: false relief'] = 0.10 + 0.12 * max(0.0, hazard - confirm)
        else:
            raw[f'Base: Monthly {monthly_quad} inside Structural {structural_quad}'] = 0.28 + 0.16 * tactical_score + 0.10 * confirm
            raw[f'Alt: Monthly {monthly_quad} fades back to Structural {structural_quad}'] = 0.18 + 0.16 * max(0.0, 0.55 - confirm) + 0.10 * hazard
            raw[f'Transition: Monthly {monthly_quad} broadens into Structural {monthly_next}'] = 0.12 + 0.14 * confirm + 0.10 * rel_h + 0.08 * max(0.0, tactical_score - 0.52)
            raw['Family: divergence resolves via signal confirmation'] = 0.10 + 0.14 * tactical_score + 0.08 * confirm
            raw['Family: policy / rates override branch'] = 0.08 + 0.12 * pol_h + 0.08 * hazard
            raw['Family: shock branch'] = 0.10 + 0.20 * shock_strength + 0.08 * war_h

        if float(flags.get('petrodollar_shock', 0.0)) >= 0.60:
            raw['Out-of-box: Petrodollar tightening shock'] = 0.12 + 0.20 * float(flags.get('petrodollar_shock', 0.0)) + 0.06 * float(flags.get('em_importer_pain', 0.0))
        if float(flags.get('em_importer_pain', 0.0)) >= 0.58:
            raw['Out-of-box: EM importer pain / exporter split'] = 0.10 + 0.16 * float(flags.get('em_importer_pain', 0.0))
        if float(flags.get('carry_unwind', 0.0)) >= 0.58:
            raw['Out-of-box: Carry unwind / dollar squeeze'] = 0.10 + 0.16 * float(flags.get('carry_unwind', 0.0))
        if float(flags.get('china_false_dawn', 0.0)) >= 0.56:
            raw['Out-of-box: China reflation false dawn'] = 0.08 + 0.14 * float(flags.get('china_false_dawn', 0.0))
        if float(flags.get('historical_repeat_score', 0.0)) >= 0.58:
            raw['Out-of-box: Historical repeat / stagflation echo'] = 0.08 + 0.16 * float(flags.get('historical_repeat_score', 0.0))

        if analogs:
            top_analog = max(analogs, key=lambda x: float(x.get('similarity', 0.0)))
            label = top_analog.get('label', 'Historical analog repeat')
            raw[f"Analog: {label}"] = max(raw.get(f"Analog: {label}", 0.0), 0.08 + 0.18 * float(top_analog.get('similarity', 0.0)))
        if playbooks:
            top_playbook = max(playbooks, key=lambda x: float(x.get('hypothesis_score', 0.0)))
            raw[f"Playbook: {top_playbook['name']}"] = max(raw.get(f"Playbook: {top_playbook['name']}", 0.0), 0.08 + 0.25 * float(top_playbook.get('hypothesis_score', 0.0)))

        probs = normalize_dict(raw)
        cases: Dict[str, ScenarioCase] = {}
        for name, p in probs.items():
            lower = name.lower()
            if 'petrodollar' in lower or 'war' in lower or 'oil' in lower:
                winners = ['Energy / hard assets', 'Gold / selective defensives', 'Petro-exporters / importer-stress FX']
                losers = ['Oil importers', 'Weak small caps', 'Broad cyclical beta']
                invalidators = ['Oil impulse fades quickly', 'USD and rates both calm materially', 'Importer pain does not spread']
            elif 'carry unwind' in lower or 'dollar squeeze' in lower:
                winners = ['USD cash', 'Funding-safe majors', 'JPY / CHF type hedges']
                losers = ['Crowded carry', 'Fragile EM FX', 'High beta crypto']
                invalidators = ['Dollar fails to extend', 'Rates calm and carry re-bid returns', 'Vol compresses fast']
            elif 'historical repeat' in lower or 'analog' in lower:
                winners = ['Names aligned with analog path', 'Selective hard assets / defensives']
                losers = ['Crowded late-cycle beta', 'Consensus laggards if analog fails']
                invalidators = ['Cross-asset path diverges from analog quickly', 'Breadth expands against analog script', 'Macro pulse changes sign']
            elif 'broadens' in lower or 'leadership' in lower or 'signal confirmation' in lower:
                winners = ['Equal-weight / selective beta', 'EM catch-up routes', 'Quality laggards if breadth confirms']
                losers = ['Consensus hedges', 'Ultra-defensive late trades']
                invalidators = ['Equal-weight and small caps fail to confirm', 'USD re-accelerates', 'Credit fails to improve']
            elif 'fades back' in lower or 'policy' in lower or 'playbook' in lower:
                winners = ['Second-order beneficiaries', 'Duration / relief beneficiaries if rates calm', 'Selective rotation winners']
                losers = ['Consensus late trades', 'Overcrowded trend-chasing']
                invalidators = ['Long-end pressure does not trigger relief', 'Policy response never broadens', 'Breadth remains narrow and defensive only']
            else:
                winners = ['Selective winners with scenario fit']
                losers = ['Crowded mismatched expressions']
                invalidators = ['Cross-asset confirmation flips materially', 'Shock state fades or intensifies against the branch', 'Breadth diverges from the expected path']
            if shock_state == 'shock':
                invalidators.append('Vol and credit calm faster than the branch assumes')
            desc = f"{name} under structural {structural_quad}, monthly {monthly_quad}, operating regime {operating}, weather {weather}, shock {shock_state}, and news-state {str(news.get('state','quiet'))}."
            cases[name] = ScenarioCase(name=name, probability=p, description=desc, invalidators=invalidators, winners=winners, losers=losers)
        return dict(sorted(cases.items(), key=lambda kv: kv[1].probability, reverse=True))
