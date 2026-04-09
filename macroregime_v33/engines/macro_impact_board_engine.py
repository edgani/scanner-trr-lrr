from __future__ import annotations

def build_macro_impact_sections(shared_core: dict, native_features: dict) -> dict:
    checklists = shared_core.get('asset_checklists', {})
    next_macro = shared_core.get('next_macro_summary', {}) or {}
    return {
        'us': _board('US equities dibaca lewat growth/inflation ROC, real yields, breadth, credit, dan sector/style rotation.', 'Cari sector/style yang paling sinkron sama regime sekarang; jangan ngejar crowded leaders kalau breadth belum lebar.', 'Kalau breadth melebar dan vol/credit reda, second-line leaders bisa nyusul. Kalau yield naik lagi, rally balik sempit.', 'Yield spike + breadth makin sempit + credit stress naik.', ['real yields','breadth','credit','sector rotation'], ['crowded longs','narrow rally'], 'equal-weight + small caps mulai confirm', shared_core.get('status_ribbon', {}).get('confidence', 0.5), checklists.get('us', []), next_macro),
        'ihsg': _board('IHSG sensitif ke USD/IDR, SBN yield, foreign flow, breadth, heavyweights, dan EM rotation.', 'Fokus ke quality liquid leaders, banks kuat, sama selective resource/exporter names yang sinkron sama backdrop.', 'Kalau rupiah stabil dan foreign sell reda, domestic beta bisa ikut napas. Kalau USD/IDR naik lagi, market tetap sempit.', 'USD/IDR naik lanjut + yield lokal naik + foreign outflow membesar.', ['USD/IDR','foreign flow','yield','heavyweights'], ['EM stress','breadth jelek'], 'foreign flow stop sell + breadth mulai confirm', shared_core.get('status_ribbon', {}).get('confidence', 0.5), checklists.get('ihsg', []), next_macro),
        'fx': _board('FX banyak digerakkan rate differential, macro surprise differential, external balance, sama crowding/fragility.', 'Pilih pair dengan divergence bersih dan likuiditas bagus; hindari pair yang sudah terlalu crowded.', 'Kalau surprise tetap searah dan IV belum panas, trend bisa lanjut. Kalau intervention risk naik, rawan whipsaw.', 'Positioning terlalu panas + options skew ekstrem + intervention.', ['rate diff','macro surprise','positioning','liquidity'], ['whipsaw','intervention'], 'data makro berikutnya tetap confirm arah', shared_core.get('status_ribbon', {}).get('confidence', 0.5), checklists.get('fx', []), next_macro),
        'commodities': _board('Commodity ditarik dua arah: physical balance dan macro money pressure dari USD/rates.', 'Cari family yang tightness fisiknya paling nyata dan chain beneficiaries yang paling bersih.', 'Kalau inventories tipis dan curve makin ketat, trend bisa lanjut. Kalau USD naik dan funds unwind, rawan koreksi.', 'Inventory build + curve melemah + USD menguat.', ['physical balance','inventory','curve','USD/rates'], ['growth scare','position unwind'], 'prompt spread makin confirm', shared_core.get('status_ribbon', {}).get('confidence', 0.5), checklists.get('commodities', []), next_macro),
        'crypto': _board('Crypto paling sehat kalau flow masuk nyata, leverage waras, dan supply likuid nggak mendadak membengkak.', 'Mainin token yang flow-nya kuat tapi belum terlalu crowded; hindari pump yang cuma ditopang funding panas.', 'Kalau stablecoin flow, exchange outflow, dan usage tetap naik, expansion bisa lanjut. Kalau unlock/funding panas, rawan flush.', 'Funding ekstrem + exchange inflow naik + unlock besar mendekat.', ['flow','leverage','supply','usage'], ['fragile pump','unlock overhang'], 'OI sehat dan fees/revenue ikut naik', shared_core.get('status_ribbon', {}).get('confidence', 0.5), checklists.get('crypto', []), next_macro),
    }

def _board(now, expr, branch, invalidator, drivers, risks, trigger, confidence, checklist, next_macro):
    return {
        'now': now,
        'best_expression': expr,
        'forward_branch': branch,
        'invalidator': invalidator,
        'drivers': drivers,
        'risks': risks,
        'trigger': trigger,
        'confidence': confidence,
        'checklist': checklist,
        'next_macro_countdown': next_macro.get('countdown', '-'),
        'next_macro_family': next_macro.get('family', '-'),
        'next_macro_focus': next_macro.get('headline', '-'),
    }
