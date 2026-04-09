from __future__ import annotations

from typing import Dict, List


class AssetTranslationEngine:
    def run(self, current_quad: str, tactical_bias: str, shock_state: str) -> Dict[str, List[Dict[str, str]]]:
        stress = shock_state in {"stress", "shock"}
        mixed = tactical_bias == "mixed"

        if current_quad == "Q3":
            return {
                "US": [
                    {
                        "bias": "LONG",
                        "setup": "Energy & cash-flow leaders",
                        "why": "Kalau Q3 aktif, cash-flow producers dan hard-asset linked equities biasanya lebih tahan daripada broad beta.",
                        "invalidator": "Oil dan hard-asset leadership cepat luntur sambil breadth benar-benar melebar.",
                    },
                    {
                        "bias": "WATCH LONG" if mixed else "LONG",
                        "setup": "Selective defensives / quality",
                        "why": "Dipakai saat growth melemah tapi broad relief belum benar-benar confirm.",
                        "invalidator": "Small caps, equal-weight, dan credit membaik bareng-bareng.",
                    },
                    {
                        "bias": "SHORT" if stress else "AVOID",
                        "setup": "Weak small-cap & long-duration laggards",
                        "why": "Saat breadth rusak, small caps dan long-duration beta sering jadi yang paling rapuh.",
                        "invalidator": "USD/yields adem dan breadth membaik jelas.",
                    },
                ],
                "IHSG": [
                    {
                        "bias": "LONG",
                        "setup": "Exporters & resource-linked leaders",
                        "why": "IHSG biasanya lebih sehat lewat exporter dan resource leaders saat shock inflasi/global commodity masih hidup.",
                        "invalidator": "Commodity chain dan USD pressure sama-sama luntur.",
                    },
                    {
                        "bias": "WATCH LONG",
                        "setup": "Selective quality banks",
                        "why": "Bank besar yang kualitasnya tinggi bisa ikut tahan, tapi jangan pukul rata semua domestic beta.",
                        "invalidator": "Funding stress atau USD pressure makin besar.",
                    },
                    {
                        "bias": "AVOID",
                        "setup": "Import-sensitive laggards",
                        "why": "Importer sensitif dua kali: ke FX dan ke biaya input/energi.",
                        "invalidator": "USD betulan melemah dan energy pressure reda.",
                    },
                ],
                "FX": [
                    {
                        "bias": "LONG",
                        "setup": "USD strength vs fragile importers",
                        "why": "Q3 + stress biasanya masih bikin dolar relatif kuat melawan importer yang rapuh.",
                        "invalidator": "Breadth global membaik dan dollar berhenti naik.",
                    },
                    {
                        "bias": "WATCH",
                        "setup": "Selective commodity FX",
                        "why": "Kalau rotasi mulai keluar dari US sempit, commodity FX tertentu bisa bangun lebih cepat dari broad risk-on.",
                        "invalidator": "Commodity impulse luntur.",
                    },
                ],
                "Commodities": [
                    {
                        "bias": "LONG",
                        "setup": "Oil / hard-asset first-order expressions",
                        "why": "Kalau shock supply / inflation masih hidup, instrumen komoditas langsung biasanya paling bersih.",
                        "invalidator": "De-escalation cepat atau demand collapse.",
                    },
                    {
                        "bias": "WATCH LONG",
                        "setup": "Gold on stress spikes",
                        "why": "Gold dipakai kalau fear/stress naik lebih cepat dari harapan growth.",
                        "invalidator": "Real yields dan dollar sama-sama naik keras.",
                    },
                ],
                "Crypto": [
                    {
                        "bias": "WATCH LONG" if not stress else "AVOID",
                        "setup": "Quality / liquidity leaders only",
                        "why": "Kalau stress tinggi, fokus ke quality/liquidity leaders, jangan lompat ke weak beta.",
                        "invalidator": "Dollar dan vol naik bareng lebih lama.",
                    },
                ],
            }

        return {
            "US": [
                {
                    "bias": "LONG",
                    "setup": "Selective cyclicals if breadth confirms",
                    "why": "Kalau relief benar, cyclicals dan equal-weight harus ikut confirm, bukan index doang.",
                    "invalidator": "Broadening gagal dan credit/small caps tidak confirm.",
                },
                {
                    "bias": "WATCH LONG",
                    "setup": "Quality growth if rates help",
                    "why": "Kalau rates bantu, quality compounders bisa dapat relief lebih bersih daripada broad beta.",
                    "invalidator": "Rates back up lagi.",
                },
            ],
            "IHSG": [
                {
                    "bias": "WATCH LONG",
                    "setup": "Domestic beta if USD eases",
                    "why": "Domestic beta lebih enak hanya kalau USD dan energy pressure benar-benar reda.",
                    "invalidator": "USD pressure balik naik.",
                },
            ],
            "FX": [
                {
                    "bias": "WATCH",
                    "setup": "Softer dollar only if relief broadens",
                    "why": "Jangan percaya soft USD kalau breadth dan cross-asset belum confirm.",
                    "invalidator": "Shock state balik intensif.",
                },
            ],
            "Commodities": [
                {
                    "bias": "WATCH LONG",
                    "setup": "Broader reflation basket",
                    "why": "Metals/energy yang lebih luas baru enak kalau growth stress benar-benar mereda.",
                    "invalidator": "Growth stall lagi.",
                },
            ],
            "Crypto": [
                {
                    "bias": "WATCH LONG",
                    "setup": "Liquidity beta if weather turns cleaner",
                    "why": "Alt broadening baru dipercaya kalau dollar dan vol benar-benar membantu.",
                    "invalidator": "Dollar dan vol naik bersama.",
                },
            ],
        }
