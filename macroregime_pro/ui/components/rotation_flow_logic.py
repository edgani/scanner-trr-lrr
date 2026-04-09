from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.display_names import DISPLAY_NAME_MAP


def _disp(sym: str) -> str:
    txt = DISPLAY_NAME_MAP.get(sym, sym)
    return str(txt).replace('.JK', '')


_MARKET_CFG = {
    'US Stocks': {
        'buckets': US_BUCKETS,
        'family_alias': {
            'Growth': 'growth / crowded leaders',
            'Quality': 'quality / real-yield survivors',
            'Defensives': 'defensives / shelter',
            'Semis': 'semis / AI beta',
            'Software/Cyber': 'software / cyber',
            'Energy': 'energy / value / oil beta',
            'Industrials': 'industrials / cyclicals',
            'Brokers/Alt': 'brokers / alt-beta finance',
        },
        'long_summary': 'US flow dibaca dari family yang paling kuat dulu, lalu spillover ke family kedua, baru ke breadth follower. Kalau breadth gagal, arus cepat lari ke defensives / TLT.',
        'short_summary': 'US short flow dibaca dari family yang paling rapuh dulu. Kalau yields naik dan breadth sempit, weakness biasa spillover ke beta kedua lalu seluruh cyclical breadth.',
        'long_spill': 'Spillover long US dibaca sebagai transmisi sebab-akibat: trigger makro -> receiver pertama -> receiver kedua -> escape route.',
        'short_spill': 'Spillover short US dibaca sebagai stress transmission: trigger makro -> first crack -> contagion -> shelter winner.',
        'long_roles': ['leader awal', 'spillover kedua', 'breadth follower', 'hedge / shelter'],
        'short_roles': ['sumber lemah awal', 'spillover short', 'late weakness', 'pemenang defensif'],
        'shelter_long': ('defensives / TLT', ['XLU', 'XLV', 'XLP', 'TLT'], 'kalau yields naik lagi atau breadth gagal confirm'),
        'shelter_short': ('USD / defensives winners', ['TLT', 'XLU', 'XLV', 'XLP'], 'penerima flow kalau short chain makin luas'),
        'trigger_proxies': {
            'long': {
                'default': ('macro trigger · real yields / breadth', ['QQQ', 'SPY', 'TLT', 'DXY'], 'real yields dan breadth menentukan apakah leadership bisa melebar.'),
                'Energy': ('macro trigger · oil / inflation impulse', ['WTI/USD', 'Brent/USD', 'XLE', 'XOM'], 'shock energi dan inflasi biasanya nyalain family energy dulu.'),
                'Semis': ('macro trigger · AI capex / duration relief', ['QQQ', 'NVDA', 'AVGO', 'TLT'], 'duration relief dan AI capex biasanya nyalain semis lebih awal.'),
                'Growth': ('macro trigger · duration relief / growth beta', ['QQQ', 'AAPL', 'MSFT', 'TLT'], 'growth beta biasanya jalan kalau duration relief dan breadth belum rusak.'),
                'Quality': ('macro trigger · yields tinggi / survivorship', ['QUAL', 'WMT', 'COST', 'TLT'], 'quality menang saat pasar cari ketahanan earnings di tengah yields tinggi.'),
            },
            'short': {
                'default': ('stress trigger · yields up / breadth narrow', ['DXY', 'QQQ', 'TLT', 'XLP'], 'yields naik dan breadth sempit biasanya memicu weak family pecah duluan.'),
                'Brokers/Alt': ('stress trigger · credit / alt-beta crack', ['HOOD', 'COIN', 'SCHW', 'MS'], 'beta finansial dan alt-flow biasanya retak lebih dulu saat risk appetite pecah.'),
                'Semis': ('stress trigger · duration squeeze / AI unwind', ['QQQ', 'NVDA', 'AMD', 'AVGO'], 'real yields naik dan AI crowding unwind biasanya merusak semis lebih dulu.'),
                'Growth': ('stress trigger · crowded growth unwind', ['QQQ', 'AAPL', 'MSFT', 'SNOW'], 'crowded growth unwind biasanya menyebar dari nama pertumbuhan besar ke software beta.'),
                'Energy': ('stress trigger · oil break / cyclicals hit', ['WTI/USD', 'Brent/USD', 'XLE', 'OXY'], 'kalau oil pecah, cyclical/value leadership bisa cepat kehilangan dukungan.'),
            },
        },
        'spill_templates': {
            'long': {
                'default': ['__LEAD__', '__SECOND__', 'Quality', '__SHELTER__'],
                'Energy': ['Energy', 'Industrials', 'Quality', '__SHELTER__'],
                'Semis': ['Semis', 'Software/Cyber', 'Quality', '__SHELTER__'],
                'Growth': ['Growth', 'Software/Cyber', 'Quality', '__SHELTER__'],
                'Quality': ['Quality', 'Defensives', 'Industrials', '__SHELTER__'],
                'Brokers/Alt': ['Brokers/Alt', 'Industrials', 'Quality', '__SHELTER__'],
            },
            'short': {
                'default': ['__LEAD__', '__SECOND__', 'Growth', '__SHELTER__'],
                'Brokers/Alt': ['Brokers/Alt', 'Software/Cyber', 'Growth', '__SHELTER__'],
                'Semis': ['Semis', 'Growth', 'Software/Cyber', '__SHELTER__'],
                'Growth': ['Growth', 'Software/Cyber', 'Brokers/Alt', '__SHELTER__'],
                'Energy': ['Energy', 'Industrials', 'Brokers/Alt', '__SHELTER__'],
            },
        },
    },
    'IHSG': {
        'buckets': IHSG_BUCKETS,
        'family_alias': {
            'Banks': 'big banks / liquid leaders',
            'Coal/Energy': 'coal / energy / exporters',
            'Metals': 'metals / nickel / gold beta',
            'Telco/Infra': 'telco / infra defensif',
            'Consumer Def': 'consumer defensive',
            'Consumer Cyc': 'consumer cyclical / domestic beta',
            'Property/Health': 'property / healthcare',
        },
        'long_summary': 'IHSG paling make sense dibaca dari resource/exporter atau banks dulu, lalu spillover ke domestic beta kalau rupiah dan foreign flow membaik. Kalau USD/IDR menekan, arus balik ke defensif.',
        'short_summary': 'IHSG short flow dimulai dari domestic / rupiah-sensitive yang rapuh dulu. Kalau foreign outflow lanjut, weakness menular ke cyclicals lalu ke breadth yang lebih luas.',
        'long_spill': 'Spillover long IHSG dibaca sebagai chain: trigger rupiah/komoditas/foreign flow -> receiver awal -> beneficiary kedua -> defensif / USD proxy.',
        'short_spill': 'Spillover short IHSG dibaca sebagai chain: trigger USD/IDR atau outflow -> family rapuh pertama -> contagion domestik -> pemenang defensif.',
        'long_roles': ['leader awal', 'beneficiary kedua', 'breadth follower', 'hedge / defensif'],
        'short_roles': ['lemah awal', 'spillover short', 'late weakness', 'pemenang defensif'],
        'shelter_long': ('USD / defensives', ['USD/IDR', 'TLKM', 'ICBP', 'KLBF'], 'kalau foreign flow belum benar-benar sehat'),
        'shelter_short': ('banks / defensives relative winners', ['BBCA', 'TLKM', 'ICBP', 'KLBF'], 'nama yang biasanya paling tahan saat breadth rusak'),
        'trigger_proxies': {
            'long': {
                'default': ('macro trigger · rupiah / foreign flow', ['USD/IDR', 'BBCA', 'BBRI', 'TLKM'], 'rupiah dan foreign flow menentukan apakah breadth lokal bisa ikut sehat.'),
                'Coal/Energy': ('macro trigger · commodity / exporter support', ['AADI', 'ADRO', 'PTBA', 'ITMG'], 'dukungan komoditas biasanya nyalain exporter/energy lebih dulu.'),
                'Banks': ('macro trigger · rupiah stabil / bank leadership', ['BBCA', 'BBRI', 'BMRI', 'USD/IDR'], 'bank besar paling cepat terima flow kalau rupiah stabil dan outflow reda.'),
                'Metals': ('macro trigger · nickel / gold beta', ['ANTM', 'INCO', 'MDKA', 'BRMS'], 'tema nickel/gold bisa nyalain metals dulu sebelum breadth melebar.'),
            },
            'short': {
                'default': ('stress trigger · USD/IDR up / foreign outflow', ['USD/IDR', 'BBCA', 'AMRT', 'CTRA'], 'USD/IDR naik dan outflow asing biasanya tekan beta domestik lebih dulu.'),
                'Consumer Cyc': ('stress trigger · domestic beta crack', ['AMRT', 'ACES', 'MAPI', 'ERAA'], 'domestic beta sering retak dulu saat rupiah dan demand outlook memburuk.'),
                'Property/Health': ('stress trigger · property / yield pressure', ['CTRA', 'BSDE', 'PWON', 'HEAL'], 'yield dan rupiah pressure sering mulai kelihatan di property lebih dulu.'),
                'Coal/Energy': ('stress trigger · commodity break', ['AADI', 'ADRO', 'PTBA', 'MEDC'], 'kalau komoditas pecah, leader resource bisa kehilangan dukungan cepat.'),
            },
        },
        'spill_templates': {
            'long': {
                'default': ['__LEAD__', '__SECOND__', 'Consumer Cyc', '__SHELTER__'],
                'Coal/Energy': ['Coal/Energy', 'Banks', 'Consumer Cyc', '__SHELTER__'],
                'Banks': ['Banks', 'Consumer Cyc', 'Property/Health', '__SHELTER__'],
                'Metals': ['Metals', 'Coal/Energy', 'Banks', '__SHELTER__'],
            },
            'short': {
                'default': ['__LEAD__', '__SECOND__', 'Banks', '__SHELTER__'],
                'Consumer Cyc': ['Consumer Cyc', 'Property/Health', 'Banks', '__SHELTER__'],
                'Property/Health': ['Property/Health', 'Consumer Cyc', 'Banks', '__SHELTER__'],
                'Coal/Energy': ['Coal/Energy', 'Metals', 'Consumer Cyc', '__SHELTER__'],
            },
        },
    },
    'Forex': {
        'buckets': FX_BUCKETS,
        'family_alias': {
            'Majors': 'majors / rate-diff winner',
            'JPY Crosses': 'JPY crosses / risk proxy',
            'Core Crosses': 'core crosses / cleaner branch',
            'Asia Overlay': 'asia / EM overlay',
        },
        'long_summary': 'FX long flow biasanya mulai dari pair rate-diff paling bersih, lalu spillover ke pair linked assets, baru ke hedge pair kalau macro surprise bergeser.',
        'short_summary': 'FX short flow biasanya muncul duluan di pair paling rapuh atau pair yang kena intervention / macro repricing. Setelah itu weakness menular ke carry dan EM-linked pair.',
        'long_spill': 'Spillover long FX dibaca sebagai chain: trigger rate-diff / surprise -> pair utama -> cross pair terkait -> hedge pair / cash.',
        'short_spill': 'Spillover short FX dibaca sebagai chain: trigger policy/intervention -> weakest pair -> carry unwind -> hedge winner.',
        'long_roles': ['pair utama', 'spillover kedua', 'hedge branch', 'flat / cash'],
        'short_roles': ['weakest pair', 'carry unwind', 'beta kedua', 'hedge winner'],
        'shelter_long': ('gold / USD hedge', ['XAU/USD', 'USD/JPY', 'USD/CHF'], 'kalau surprise macro pecah dan perlu hedge cepat'),
        'shelter_short': ('JPY / CHF / flat', ['USD/JPY', 'USD/CHF', 'USD/SGD'], 'tujuan akhir saat carry unwind / intervention risk naik'),
        'trigger_proxies': {
            'long': {
                'default': ('macro trigger · rate diff / macro surprise', ['EUR/USD', 'USD/JPY', 'USD/CHF', 'XAU/USD'], 'pair dengan rate differential paling bersih biasanya nyala dulu.'),
                'Majors': ('macro trigger · majors / clean carry', ['EUR/USD', 'GBP/USD', 'AUD/USD', 'USD/JPY'], 'majors biasanya gerak duluan kalau rate differential dan macro surprise searah.'),
                'JPY Crosses': ('macro trigger · risk appetite / JPY crosses', ['EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'NZD/JPY'], 'JPY crosses biasanya paling sensitif ke perubahan risk appetite.'),
                'Asia Overlay': ('macro trigger · Asia / EM overlay', ['USD/IDR', 'USD/CNH', 'USD/SGD', 'AUD/USD'], 'Asia overlay jalan saat commodity dan EM flow ikut bergerak.'),
            },
            'short': {
                'default': ('stress trigger · intervention / carry unwind', ['USD/JPY', 'USD/CHF', 'XAU/USD', 'USD/SGD'], 'intervention risk dan carry unwind biasanya bikin pair rapuh pecah duluan.'),
                'JPY Crosses': ('stress trigger · JPY carry unwind', ['EUR/JPY', 'GBP/JPY', 'AUD/JPY', 'NZD/JPY'], 'JPY carry unwind sering jadi sumber weakness paling cepat.'),
                'Asia Overlay': ('stress trigger · EM / Asia pressure', ['USD/IDR', 'USD/CNH', 'USD/SGD', 'AUD/USD'], 'EM dan Asia pairs paling sensitif saat USD menguat tajam.'),
                'Majors': ('stress trigger · majors repricing', ['EUR/USD', 'GBP/USD', 'AUD/USD', 'USD/CHF'], 'majors juga bisa jadi sumber crack kalau macro repricing tajam.'),
            },
        },
        'spill_templates': {
            'long': {
                'default': ['Majors', 'JPY Crosses', 'Asia Overlay', '__SHELTER__'],
                'Majors': ['Majors', 'JPY Crosses', 'Asia Overlay', '__SHELTER__'],
                'JPY Crosses': ['JPY Crosses', 'Majors', 'Core Crosses', '__SHELTER__'],
                'Asia Overlay': ['Asia Overlay', 'Majors', 'Core Crosses', '__SHELTER__'],
            },
            'short': {
                'default': ['Asia Overlay', 'JPY Crosses', 'Majors', '__SHELTER__'],
                'JPY Crosses': ['JPY Crosses', 'Asia Overlay', 'Majors', '__SHELTER__'],
                'Asia Overlay': ['Asia Overlay', 'JPY Crosses', 'Majors', '__SHELTER__'],
                'Majors': ['Majors', 'JPY Crosses', 'Asia Overlay', '__SHELTER__'],
            },
        },
    },
    'Commodities': {
        'buckets': COMMODITY_BUCKETS,
        'family_alias': {
            'Precious': 'precious metals / hedge',
            'Energy': 'energy / prompt-tight leader',
            'Industrial': 'industrial metals / growth beta',
            'Agri/Softs': 'agri / softs',
            'Livestock': 'livestock',
            'Broad Proxies': 'broad commodity proxies',
        },
        'long_summary': 'Commodity long flow normalnya dimulai dari family fisik paling ketat, lalu spillover ke second-line beneficiary, baru ke hedge metals kalau growth scare masuk.',
        'short_summary': 'Commodity short flow dimulai dari family yang inventory / curve-nya paling rusak. Kalau USD menguat, weakness biasanya melebar ke family lain dan broad proxies.',
        'long_spill': 'Spillover long commodity dibaca sebagai chain: physical trigger -> first receiver -> second-order proxy -> hedge / USD.',
        'short_spill': 'Spillover short commodity dibaca sebagai chain: stress trigger -> weakest family -> broad unwind -> hedge winner.',
        'long_roles': ['leader awal', 'beneficiary kedua', 'hedge branch', 'USD / shelter'],
        'short_roles': ['weakest family', 'spillover short', 'late weakness', 'winner hedge'],
        'shelter_long': ('USD / hedge', ['USD', 'XAU/USD', 'XAG/USD'], 'kalau curve gagal confirm atau growth scare masuk'),
        'shelter_short': ('USD / gold winners', ['USD', 'XAU/USD', 'TLT'], 'akhir chain kalau fund unwind makin kuat'),
        'trigger_proxies': {
            'long': {
                'default': ('macro trigger · physical tightness / USD', ['WTI/USD', 'Copper/USD', 'DBC', 'DXY'], 'family fisik paling ketat biasanya nyala dulu sebelum broad proxies ikut.'),
                'Energy': ('macro trigger · prompt tight / geopolitik', ['WTI/USD', 'Brent/USD', 'Natural Gas/USD', 'Heating Oil/USD'], 'tight prompt spreads dan geopolitik biasanya menghidupkan energy paling dulu.'),
                'Precious': ('macro trigger · real yield / hedge demand', ['XAU/USD', 'XAG/USD', 'TLT', 'DXY'], 'precious biasanya hidup dulu saat pasar cari hedge terhadap growth scare atau yield real turun.'),
                'Industrial': ('macro trigger · China / growth beta', ['Copper/USD', 'DBC', 'GSG', 'WTI/USD'], 'industrial beta jalan saat growth impulse dan reflation masih hidup.'),
            },
            'short': {
                'default': ('stress trigger · USD up / fund unwind', ['DXY', 'DBC', 'GSG', 'XAU/USD'], 'USD menguat dan fund unwind biasanya menekan family paling lemah lebih dulu.'),
                'Energy': ('stress trigger · oil break / curve soften', ['WTI/USD', 'Brent/USD', 'DBC', 'GSG'], 'kalau oil break dan curve melemah, seluruh commodity beta bisa ikut turun.'),
                'Industrial': ('stress trigger · growth scare / China miss', ['Copper/USD', 'DBC', 'GSG', 'DXY'], 'industrial paling sensitif saat pertumbuhan dan demand outlook memburuk.'),
                'Agri/Softs': ('stress trigger · inventory/weather reversal', ['Corn/USD', 'Wheat/USD', 'Coffee/USD', 'Sugar/USD'], 'agri/softs bisa jadi sumber weakness awal saat panic pricing mereda.'),
            },
        },
        'spill_templates': {
            'long': {
                'default': ['__LEAD__', 'Broad Proxies', 'Precious', '__SHELTER__'],
                'Energy': ['Energy', 'Broad Proxies', 'Precious', '__SHELTER__'],
                'Industrial': ['Industrial', 'Broad Proxies', 'Energy', '__SHELTER__'],
                'Precious': ['Precious', 'Broad Proxies', 'Energy', '__SHELTER__'],
            },
            'short': {
                'default': ['__LEAD__', 'Broad Proxies', 'Precious', '__SHELTER__'],
                'Energy': ['Energy', 'Broad Proxies', 'Precious', '__SHELTER__'],
                'Industrial': ['Industrial', 'Broad Proxies', 'Precious', '__SHELTER__'],
                'Agri/Softs': ['Agri/Softs', 'Broad Proxies', 'Precious', '__SHELTER__'],
            },
        },
    },
    'Crypto': {
        'buckets': CRYPTO_BUCKETS,
        'family_alias': {
            'Majors': 'majors / BTC-ETH leadership',
            'L1/L2': 'L1/L2 beta',
            'DeFi': 'DeFi / fee beta',
            'AI/Data': 'AI / data beta',
            'RWA': 'RWA / policy beta',
            'Infra': 'infra / exchange beta',
            'High Beta': 'high beta / meme / retail heat',
        },
        'long_summary': 'Crypto long flow paling sehat biasanya dimulai dari majors dulu, lalu spillover ke infra / second-line beta, baru ke selective alts kalau breadth ikut sehat.',
        'short_summary': 'Crypto short flow biasanya mulai dari high-beta / meme / weakest alts dulu. Kalau funding panas pecah, weakness menular ke infra dan beta kedua sebelum semua balik ke stables.',
        'long_spill': 'Spillover long crypto dibaca sebagai chain: liquidity trigger -> first receiver -> second-order beta -> stables kalau breadth gagal.',
        'short_spill': 'Spillover short crypto dibaca sebagai chain: funding/unlock stress -> weakest beta -> contagion -> stables/cash.',
        'long_roles': ['leader awal', 'branch kedua', 'late beta', 'stables / hedge'],
        'short_roles': ['sumber rapuh', 'spillover short', 'late weakness', 'cash winner'],
        'shelter_long': ('stables / cash', ['USDT', 'USDC', 'BTC/USD'], 'kalau breadth alt belum benar-benar sehat'),
        'shelter_short': ('stables / cash winners', ['USDT', 'USDC', 'BTC/USD'], 'tujuan akhir saat flush / unlock stress'),
        'trigger_proxies': {
            'long': {
                'default': ('macro trigger · liquidity / majors', ['BTC/USD', 'ETH/USD', 'USDT', 'USDC'], 'likuiditas dan majors breadth biasanya jalan duluan sebelum alt ikut sehat.'),
                'Majors': ('macro trigger · majors breadth / ETF flow', ['BTC/USD', 'ETH/USD', 'SOL/USD', 'BNB/USD'], 'majors biasanya membuka jalan untuk beta crypto lain.'),
                'AI/Data': ('macro trigger · narrative / beta demand', ['TAO/USD', 'FET/USD', 'RENDER/USD', 'BTC/USD'], 'narrative AI/data bisa menarik beta lebih cepat, tapi tetap butuh majors sehat.'),
                'Infra': ('macro trigger · infra / exchange beta', ['LINK/USD', 'TON/USD', 'INJ-USD', 'BTC/USD'], 'infra biasanya menerima flow lebih awal setelah majors sehat.'),
            },
            'short': {
                'default': ('stress trigger · funding / unlock heat', ['BTC/USD', 'ETH/USD', 'USDT', 'USDC'], 'funding panas dan unlock stress biasanya merusak beta rapuh lebih dulu.'),
                'High Beta': ('stress trigger · meme / high-beta flush', ['WIF/USD', 'DOGE/USD', 'PEPE24478-USD', 'BONK-USD'], 'high beta dan meme biasanya jebol paling awal saat leverage dibersihkan.'),
                'AI/Data': ('stress trigger · narrative unwind', ['TAO/USD', 'FET/USD', 'RENDER/USD', 'BTC/USD'], 'narrative-driven tokens bisa menjadi sumber contagion saat momentum patah.'),
                'DeFi': ('stress trigger · DeFi fee beta unwind', ['AAVE/USD', 'UNI7083-USD', 'MKR/USD', 'LDO-USD'], 'DeFi fee beta sering ikut tertekan saat majors gagal menjaga breadth.'),
            },
        },
        'spill_templates': {
            'long': {
                'default': ['Majors', 'Infra', 'L1/L2', '__SHELTER__'],
                'Majors': ['Majors', 'Infra', 'L1/L2', '__SHELTER__'],
                'AI/Data': ['AI/Data', 'Majors', 'Infra', '__SHELTER__'],
                'Infra': ['Infra', 'L1/L2', 'AI/Data', '__SHELTER__'],
                'RWA': ['RWA', 'Majors', 'L1/L2', '__SHELTER__'],
            },
            'short': {
                'default': ['High Beta', 'L1/L2', 'Majors', '__SHELTER__'],
                'High Beta': ['High Beta', 'L1/L2', 'Majors', '__SHELTER__'],
                'AI/Data': ['AI/Data', 'High Beta', 'Majors', '__SHELTER__'],
                'DeFi': ['DeFi', 'L1/L2', 'Majors', '__SHELTER__'],
                'Majors': ['Majors', 'L1/L2', 'High Beta', '__SHELTER__'],
            },
        },
    },
}




def _section_meta(section: dict) -> dict:
    macro = section.get('macro_vs_market', {}) or {}
    hub = section.get('market_hub', {}) or {}
    structural = str(hub.get('structural_quad', macro.get('structural_quad', '-')))
    monthly = str(hub.get('monthly_quad', macro.get('monthly_quad', structural)))
    operating = str(hub.get('operating_regime', macro.get('operating_regime', f'Monthly {monthly} inside Structural {structural}' if monthly != structural else f'Aligned {structural}')))
    dominant = str(hub.get('dominant_horizon', 'aligned'))
    return {
        'structural': structural,
        'monthly': monthly,
        'operating': operating,
        'dominant': dominant,
    }

def _norm_key(txt: str) -> str:
    return str(txt).replace('.JK', '').replace('/USD', '').replace('/IDR', '').replace('/JPY', '').strip().upper()


def _family_lookup(market_title: str) -> dict[str, str]:
    cfg = _MARKET_CFG[market_title]
    lookup: dict[str, str] = {}
    for family, syms in cfg['buckets'].items():
        for sym in syms:
            display = _disp(sym)
            for key in {sym, display, display.replace('.JK', ''), str(sym).replace('.JK', '')}:
                lookup[_norm_key(key)] = family
    if market_title == 'Forex':
        extra = {
            'XAU/USD': 'Majors',
            'XAG/USD': 'Majors',
            'USD': 'Majors',
            'USD/JPY': 'Majors',
            'USD/CHF': 'Majors',
            'USD/SGD': 'Asia Overlay',
        }
        for k, v in extra.items():
            lookup[_norm_key(k)] = v
    return lookup


def _family_title(market_title: str, family: str) -> str:
    cfg = _MARKET_CFG[market_title]
    return cfg['family_alias'].get(family, family)


def _bucket_display_list(market_title: str, family: str) -> list[str]:
    cfg = _MARKET_CFG[market_title]
    return [_disp(sym) for sym in cfg['buckets'].get(family, [])]


def _dedupe(seq: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for item in seq:
        txt = str(item).strip()
        key = txt.upper()
        if not txt or key in seen:
            continue
        seen.add(key)
        out.append(txt)
    return out


def _extract_metric(text: str, key: str) -> float | None:
    m = re.search(rf"{re.escape(key)}\s*(-?\d+(?:\.\d+)?)%", str(text))
    if not m:
        return None
    try:
        return float(m.group(1)) / 100.0
    except Exception:
        return None


def _parse_countdown_hours(text: str) -> float | None:
    txt = str(text or '').strip()
    if not txt or txt == '-':
        return None
    day_m = re.search(r"T-(\d+)d(?:\s*(\d+)h)?", txt)
    if day_m:
        days = int(day_m.group(1))
        hours = int(day_m.group(2) or 0)
        return float(days * 24 + hours)
    hour_m = re.search(r"T-(\d+)h(?:\s*(\d+)m)?", txt)
    if hour_m:
        hours = int(hour_m.group(1))
        mins = int(hour_m.group(2) or 0)
        return float(hours + mins / 60.0)
    min_m = re.search(r"T-(\d+)m", txt)
    if min_m:
        return float(int(min_m.group(1)) / 60.0)
    return None


def _cap_horizon(base: str, countdown: str) -> str:
    hrs = _parse_countdown_hours(countdown)
    if hrs is None:
        return base
    if hrs <= 24:
        return f"sisa kira-kira sampai next macro {countdown}"
    if hrs <= 72:
        return f"estimasi 1-3 hari · paling lambat diuji lagi {countdown}"
    if hrs <= 24 * 7:
        return f"estimasi beberapa hari s/d {countdown}"
    return f"{base} · event besar berikutnya {countdown}"


def _rotation_stage(groups: list[dict], side: str, countdown: str) -> dict:
    scores = [float(g.get('avg_score', 0.0)) for g in groups[:3]] + [0.0, 0.0, 0.0]
    s0, s1, s2 = scores[:3]
    if side == 'long':
        if s0 >= 0.16 and s1 < 0.09:
            stage = 'Stage 1 · leader awal masih dominan'
            note = 'rotasi masih dipimpin family pertama; breadth belum benar-benar ikut.'
            remain = _cap_horizon('estimasi 1-3 minggu', countdown)
        elif s1 >= 0.09 and s2 < 0.06:
            stage = 'Stage 2 · spillover ke beneficiary kedua'
            note = 'leader awal sudah hidup dan flow mulai pindah ke cabang kedua.'
            remain = _cap_horizon('estimasi 4-10 hari', countdown)
        elif s2 >= 0.06:
            stage = 'Stage 3 · breadth follow-through'
            note = 'rotasi sudah menyebar; fase ini kuat tapi biasanya lebih matang.'
            remain = _cap_horizon('estimasi 2-7 hari', countdown)
        else:
            stage = 'Stage 4 · late / shelter-sensitive'
            note = 'rotasi mulai matang; kalau trigger goyah arus gampang pindah ke shelter.'
            remain = _cap_horizon('estimasi 1-5 hari', countdown)
    else:
        if s0 <= -0.14 and s1 > -0.08:
            stage = 'Stage 1 · source crack baru mulai'
            note = 'weakness baru pecah di family paling rapuh; contagion belum luas.'
            remain = _cap_horizon('estimasi 3-10 hari', countdown)
        elif s1 <= -0.10 and s2 > -0.06:
            stage = 'Stage 2 · contagion ke family kedua'
            note = 'stress sudah menular ke family kedua; weakness mulai lebih jelas.'
            remain = _cap_horizon('estimasi 2-7 hari', countdown)
        elif s2 <= -0.08:
            stage = 'Stage 3 · broad weakness'
            note = 'weakness sudah cukup luas; fase ini cenderung lebih matang.'
            remain = _cap_horizon('estimasi 1-5 hari', countdown)
        else:
            stage = 'Stage 4 · late defensive bid'
            note = 'fase short sudah dekat shelter/defensive winner; risiko squeeze naik.'
            remain = _cap_horizon('estimasi pendek 1-3 hari', countdown)
    return {'stage_now': stage, 'stage_note': note, 'stage_remaining': remain}


def _spill_stage(section: dict, groups: list[dict], side: str, countdown: str) -> dict:
    tx = section.get('transmission', {}) or {}
    confirm_n = len(tx.get('confirm', []) or [])
    conflict_n = len(tx.get('conflict', []) or [])
    scores = [float(g.get('avg_score', 0.0)) for g in groups[:3]] + [0.0, 0.0, 0.0]
    s0, s1, s2 = scores[:3]
    if side == 'long':
        if s0 >= 0.12 and s1 < 0.07:
            stage = 'Stage 1 · trigger → first receiver'
            note = 'trigger makro sudah jelas, tapi spillover masih di receiver pertama.'
            remain = _cap_horizon('estimasi 3-10 hari', countdown)
        elif s1 >= 0.07 and (s2 < 0.05 or confirm_n < 2):
            stage = 'Stage 2 · second-order spread'
            note = 'spillover sudah pindah ke beneficiary lapis kedua, tapi breadth belum luas.'
            remain = _cap_horizon('estimasi 2-7 hari', countdown)
        elif s2 >= 0.05 and conflict_n <= 1:
            stage = 'Stage 3 · broad spillover'
            note = 'transmisi sudah menyebar cukup luas dan konfirmasi masih lumayan sehat.'
            remain = _cap_horizon('estimasi 2-5 hari', countdown)
        else:
            stage = 'Stage 4 · escape-route watch'
            note = 'spillover mulai matang atau konflik naik; shelter perlu dipantau dekat.'
            remain = _cap_horizon('estimasi 1-4 hari', countdown)
    else:
        if s0 <= -0.12 and s1 > -0.08:
            stage = 'Stage 1 · first crack'
            note = 'stress baru pecah di receiver pertama; contagion belum luas.'
            remain = _cap_horizon('estimasi 2-7 hari', countdown)
        elif s1 <= -0.08 and (s2 > -0.05 or conflict_n < 2):
            stage = 'Stage 2 · contagion spreading'
            note = 'kelemahan sudah menular ke lapis kedua dan mulai masuk breadth lain.'
            remain = _cap_horizon('estimasi 1-5 hari', countdown)
        elif s2 <= -0.05:
            stage = 'Stage 3 · broad stress / shelter bid'
            note = 'stress sudah cukup luas; defensive winners biasanya makin terlihat.'
            remain = _cap_horizon('estimasi 1-4 hari', countdown)
        else:
            stage = 'Stage 4 · late shelter phase'
            note = 'contagion sudah matang; risiko relief/squeeze ikut naik.'
            remain = _cap_horizon('estimasi pendek 1-3 hari', countdown)
    return {'stage_now': stage, 'stage_note': note, 'stage_remaining': remain}


def _attach_stage_meta(flow: dict, meta: dict) -> dict:
    out = dict(flow)
    out.update(meta)
    return out


def _group_rows_by_family(market_title: str, section: dict, side: str) -> list[dict]:
    lookup = _family_lookup(market_title)
    rows = [r for r in (section.get('setups_now', []) or []) if str(r.get('side', '')).lower() == side]
    rows.sort(key=lambda r: float(r.get('score', 0.0)), reverse=(side == 'long'))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        name = str(row.get('name', '')).strip()
        family = lookup.get(_norm_key(name), str(row.get('bucket', 'Other')))
        grouped[family].append(row)

    out = []
    for family, fam_rows in grouped.items():
        scores = [float(r.get('score', 0.0)) for r in fam_rows]
        avg_score = sum(scores) / max(1, len(scores))
        ticker_candidates = [str(r.get('name', '-')) for r in fam_rows]
        ticker_candidates.extend(_bucket_display_list(market_title, family))
        out.append({
            'family': family,
            'title': _family_title(market_title, family),
            'avg_score': avg_score,
            'rows': fam_rows,
            'tickers': _dedupe(ticker_candidates)[:6],
        })
    out.sort(key=lambda x: x['avg_score'], reverse=(side == 'long'))
    return out


def _group_map(groups: list[dict]) -> dict[str, dict]:
    return {str(g.get('family')): g for g in groups}


def _pick_next_family(groups: list[dict], used: set[str]) -> str | None:
    for g in groups:
        fam = str(g.get('family'))
        if fam not in used:
            return fam
    return None


def _step_tone(side: str, idx: int, final: bool = False) -> str:
    if side == 'long':
        if final:
            return 'bad'
        return 'good' if idx == 0 else ('blue' if idx in {1, 2} else 'warn')
    if final:
        return 'good'
    return 'bad' if idx == 0 else ('warn' if idx in {1, 2} else 'blue')


def _flow_steps(market_title: str, section: dict, side: str) -> list[dict]:
    cfg = _MARKET_CFG[market_title]
    families = _group_rows_by_family(market_title, section, side)
    core = families[:3]
    roles = cfg['long_roles'] if side == 'long' else cfg['short_roles']
    steps: list[dict] = []
    for idx, fam in enumerate(core):
        lead_row = fam['rows'][0] if fam['rows'] else {}
        why = str(lead_row.get('why_now', '') or '').strip()
        steps.append({
            'title': fam['title'],
            'rank': roles[min(idx, len(roles) - 1)],
            'note': why or ('keluarga yang paling sinkron sekarang' if side == 'long' else 'keluarga yang paling rapuh sekarang'),
            'tickers': fam['tickers'],
            'tone': _step_tone(side, idx, final=False),
        })
    shelter_key = 'shelter_long' if side == 'long' else 'shelter_short'
    shelter_title, shelter_tickers, shelter_note = cfg[shelter_key]
    steps.append({
        'title': shelter_title,
        'rank': roles[min(len(core), len(roles) - 1)],
        'note': shelter_note,
        'tickers': list(shelter_tickers),
        'tone': _step_tone(side, len(core), final=True),
    })
    return steps


def _flow_summary(market_title: str, side: str) -> str:
    cfg = _MARKET_CFG[market_title]
    return cfg['long_summary'] if side == 'long' else cfg['short_summary']


def _spillover_summary(market_title: str, side: str) -> str:
    cfg = _MARKET_CFG[market_title]
    return cfg['long_spill'] if side == 'long' else cfg['short_spill']


def _trigger_step(market_title: str, section: dict, side: str, lead_family: str | None) -> dict:
    cfg = _MARKET_CFG[market_title]
    title, tickers, base_note = cfg['trigger_proxies'][side].get(lead_family, cfg['trigger_proxies'][side]['default'])
    tx = section.get('transmission', {}) or {}
    dom = ', '.join(str(x) for x in (tx.get('dominant', []) or [])[:2])
    path = str((tx.get('paths', []) or [''])[0]).strip()
    extra_bits = [base_note]
    if dom:
        extra_bits.append(f"dominant: {dom}")
    if path:
        extra_bits.append(path)
    rank = 'macro trigger' if side == 'long' else 'stress trigger'
    return {
        'title': title,
        'rank': rank,
        'note': ' · '.join(x for x in extra_bits if x),
        'tickers': list(tickers),
        'tone': 'blue' if side == 'long' else 'bad',
    }


def _resolve_chain_families(market_title: str, side: str, lead_family: str | None, groups: list[dict]) -> list[str]:
    cfg = _MARKET_CFG[market_title]
    templates = cfg['spill_templates'][side]
    raw_template = templates.get(lead_family, templates['default'])
    used: set[str] = set()
    resolved: list[str] = []
    for token in raw_template:
        if token == '__SHELTER__':
            resolved.append(token)
            continue
        if token == '__LEAD__':
            fam = lead_family or _pick_next_family(groups, used)
        elif token == '__SECOND__':
            fam = _pick_next_family(groups, used | ({lead_family} if lead_family else set()))
        elif token == '__THIRD__':
            fam = _pick_next_family(groups, used)
        else:
            fam = token
        if fam and fam != '__SHELTER__':
            used.add(fam)
            resolved.append(fam)
    return resolved


def _family_chain_step(market_title: str, side: str, family: str, groups: list[dict], idx: int) -> dict:
    cfg = _MARKET_CFG[market_title]
    gm = _group_map(groups)
    shelter_key = 'shelter_long' if side == 'long' else 'shelter_short'
    if family == '__SHELTER__':
        title, tickers, note = cfg[shelter_key]
        rank = 'escape route' if side == 'long' else 'shelter winner'
        return {'title': title, 'rank': rank, 'note': note, 'tickers': list(tickers), 'tone': 'bad' if side == 'long' else 'good'}

    fam_group = gm.get(family)
    title = _family_title(market_title, family)
    tickers = []
    why = ''
    if fam_group:
        tickers = list(fam_group.get('tickers', []))
        lead_row = (fam_group.get('rows') or [{}])[0]
        why = str(lead_row.get('why_now', '') or '').strip()
    if not tickers:
        tickers = _bucket_display_list(market_title, family)[:6]
    if side == 'long':
        ranks = ['first receiver', 'second-order', 'late beneficiary']
        default_notes = [
            'family pertama yang biasanya menerima arus dari trigger awal.',
            'beneficiary lapis kedua kalau flow benar-benar menyebar.',
            'late branch yang ikut kalau breadth masih sehat.',
        ]
        tone = ['good', 'blue', 'warn'][min(idx, 2)]
    else:
        ranks = ['first crack', 'contagion', 'late weakness']
        default_notes = [
            'family pertama yang biasanya retak saat stress muncul.',
            'weakness menular ke family kedua kalau pressure berlanjut.',
            'late weakness yang ikut rusak kalau breadth sudah benar-benar patah.',
        ]
        tone = ['bad', 'warn', 'blue'][min(idx, 2)]
    return {
        'title': title,
        'rank': ranks[min(idx, len(ranks) - 1)],
        'note': why or default_notes[min(idx, len(default_notes) - 1)],
        'tickers': tickers,
        'tone': tone,
    }


def _spillover_steps(market_title: str, section: dict, side: str) -> list[dict]:
    groups = _group_rows_by_family(market_title, section, side)
    lead_family = str(groups[0].get('family')) if groups else None
    sequence = _resolve_chain_families(market_title, side, lead_family, groups)
    steps = [_trigger_step(market_title, section, side, lead_family)]
    family_tokens = [token for token in sequence if token != '__SHELTER__'][:2]
    for idx, family in enumerate(family_tokens):
        steps.append(_family_chain_step(market_title, side, family, groups, idx))
    steps.append(_family_chain_step(market_title, side, '__SHELTER__', groups, 3))
    return steps[:4]


def build_market_rotation_flows(market_title: str, section: dict) -> list[dict]:
    countdown = str(((section.get('macro_vs_market', {}) or {}).get('next_macro_countdown', '-')) or '-')
    long_groups = _group_rows_by_family(market_title, section, 'long')
    short_groups = _group_rows_by_family(market_title, section, 'short')
    long_steps = _flow_steps(market_title, section, 'long')
    short_steps = _flow_steps(market_title, section, 'short')
    long_spill = _spillover_steps(market_title, section, 'long')
    short_spill = _spillover_steps(market_title, section, 'short')
    meta = _section_meta(section)

    structural_rotation = [
        _attach_stage_meta({
            'label': f'Structural Long Rotation · backbone {meta["structural"]}',
            'summary': f'Backbone 1–3 bulan ditentukan structural {meta["structural"]}. Ini route family yang paling konsisten kalau regime besar bertahan.',
            'tone': 'blue',
            'steps': long_steps,
            'kind': 'rotation_structural',
        }, _rotation_stage(long_groups, 'long', countdown)),
        _attach_stage_meta({
            'label': f'Structural Short Rotation · weak route {meta["structural"]}',
            'summary': f'Weak route 1–3 bulan saat structural {meta["structural"]} yang dominan.',
            'tone': 'warn',
            'steps': short_steps,
            'kind': 'rotation_structural',
        }, _rotation_stage(short_groups, 'short', countdown)),
    ]
    monthly_rotation = [
        _attach_stage_meta({
            'label': f'Monthly Long Rotation · weather {meta["monthly"]}',
            'summary': f'Tactical overlay bulan ini dibaca dari monthly {meta["monthly"]}. Ini flow yang biasanya jalan lebih dulu secara taktis.',
            'tone': 'good',
            'steps': long_steps,
            'kind': 'rotation_monthly',
        }, _rotation_stage(long_groups, 'long', countdown)),
        _attach_stage_meta({
            'label': f'Monthly Short Rotation · tactical failure {meta["monthly"]}',
            'summary': f'Kalau monthly pulse gagal, weakness biasanya menyebar seperti ini.',
            'tone': 'warn',
            'steps': short_steps,
            'kind': 'rotation_monthly',
        }, _rotation_stage(short_groups, 'short', countdown)),
    ]
    resolved_rotation = [
        _attach_stage_meta({
            'label': f'Resolved Long Flow · {meta["operating"]}',
            'summary': f'Execution now memakai resolved operating regime: {meta["operating"]} (dominant {meta["dominant"]}).',
            'tone': 'blue',
            'steps': long_steps,
            'kind': 'rotation_resolved',
        }, _rotation_stage(long_groups, 'long', countdown)),
        _attach_stage_meta({
            'label': f'Resolved Short Flow · {meta["operating"]}',
            'summary': f'Kalau branch gagal confirm, short/hedge flow yang paling relevan dibaca dari resolved regime.',
            'tone': 'bad',
            'steps': short_steps,
            'kind': 'rotation_resolved',
        }, _rotation_stage(short_groups, 'short', countdown)),
    ]
    structural_spill = [
        _attach_stage_meta({
            'label': f'Structural Spillover · route {meta["structural"]}',
            'summary': f'Structural spillover route untuk 1–3 bulan. Trigger makro -> first receiver -> second receiver -> shelter.',
            'tone': 'good',
            'steps': long_spill,
            'kind': 'spillover_structural',
        }, _spill_stage(section, long_groups, 'long', countdown)),
    ]
    monthly_spill = [
        _attach_stage_meta({
            'label': f'Monthly Trigger Chain · {meta["monthly"]}',
            'summary': f'Chain taktis bulan ini. Berguna untuk tahu siapa yang bergerak duluan dan siapa yang masih terlalu dini.',
            'tone': 'warn',
            'steps': long_spill,
            'kind': 'spillover_monthly',
        }, _spill_stage(section, long_groups, 'long', countdown)),
    ]
    resolved_spill = [
        _attach_stage_meta({
            'label': f'Resolved Spillover Chain · {meta["operating"]}',
            'summary': f'Chain yang dipakai untuk execution now, termasuk jalur stress -> contagion -> shelter winner.',
            'tone': 'bad',
            'steps': short_spill if meta['dominant'] == 'structural' else long_spill,
            'kind': 'spillover_resolved',
        }, _spill_stage(section, short_groups if meta['dominant'] == 'structural' else long_groups, 'short' if meta['dominant'] == 'structural' else 'long', countdown)),
    ]

    return structural_rotation + monthly_rotation + resolved_rotation + structural_spill + monthly_spill + resolved_spill


def build_dashboard_global_flows(snapshot: dict) -> list[dict]:
    market_order = [('commodities', 'Commodities'), ('us', 'US'), ('ihsg', 'IHSG'), ('fx', 'FX'), ('crypto', 'Crypto')]
    long_rows = []
    short_rows = []
    for key, market_label in market_order:
        sec = snapshot.get(key, {}) or {}
        for row in sec.get('setups_now', []) or []:
            side = str(row.get('side', '')).lower()
            if side == 'long':
                long_rows.append((market_label, row))
            elif side == 'short':
                short_rows.append((market_label, row))
    long_rows.sort(key=lambda x: float(x[1].get('score', 0.0)), reverse=True)
    short_rows.sort(key=lambda x: float(x[1].get('score', 0.0)))

    def _mk_steps(items: list[tuple[str, dict]], side: str) -> list[dict]:
        out = []
        labels = ['leader awal', 'spillover kedua', 'masih ikut', 'biasa aja'] if side == 'long' else ['paling lemah', 'spillover short', 'masih rapuh', 'biasa aja']
        for idx, (market_label, row) in enumerate(items[:4]):
            out.append({
                'title': f"{market_label} · {row.get('name', '-')}",
                'rank': labels[min(idx, 3)],
                'note': str(row.get('why_now', '') or row.get('action', '') or ''),
                'tickers': [str(row.get('name', '-'))],
                'tone': _step_tone(side, idx, final=False),
            })
        return out

    shared = snapshot.get('shared_core', {}) or {}
    next_macro = shared.get('next_macro_summary', {}) or {}
    best = str(shared.get('best_beneficiary', 'XAU/USD'))
    safe = str(shared.get('safe_harbor', 'USD'))
    macro_note = str(next_macro.get('countdown', '-'))

    return [
        {
            'label': 'Global Long Rotation Flow with Tickers',
            'summary': 'Cross-market long flow dari market / asset yang paling kuat dulu, lalu turun ke yang masih layak kalau leadership melebar.',
            'tone': 'blue',
            'steps': _mk_steps(long_rows, 'long'),
        },
        {
            'label': 'Global Short Rotation Flow with Tickers',
            'summary': 'Cross-market short flow dari asset paling rapuh dulu, lalu ke spillover weakness berikutnya.',
            'tone': 'warn',
            'steps': _mk_steps(short_rows, 'short'),
        },
        {
            'label': 'Global Spillover / Escape Route',
            'summary': 'Kalau leader sekarang capek atau catalyst makro berlawanan, arus biasanya pindah ke hedge lalu safe harbor.',
            'tone': 'good',
            'steps': [
                {'title': f"macro trigger · {next_macro.get('family', 'macro')}", 'rank': 'macro trigger', 'note': str(next_macro.get('headline', '-') or '-'), 'tickers': [str(next_macro.get('family', 'macro')).upper()], 'tone': 'blue'},
                {'title': best, 'rank': 'first receiver', 'note': 'beneficiary paling sinkron saat ini', 'tickers': [best], 'tone': 'good'},
                {'title': 'second-line beneficiaries', 'rank': 'second-order', 'note': macro_note, 'tickers': ['XLE', 'XOM', 'XAU/USD', 'TLT'] if best in {'WTI', 'WTI/USD', 'Brent/USD'} else ['QQQ', 'NVDA', 'XAU/USD', 'TLT'], 'tone': 'warn'},
                {'title': safe, 'rank': 'escape route', 'note': 'tujuan akhir kalau breadth dan risk appetite gagal', 'tickers': [safe], 'tone': 'bad'},
            ],
        },
    ]
