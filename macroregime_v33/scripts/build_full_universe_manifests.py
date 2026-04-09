from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
from datetime import datetime, timezone
import csv
import io
import json
import re
from typing import Any

from bs4 import BeautifulSoup
import requests

from config.settings import COINGECKO_API_BASE, COINGECKO_DEMO_API_KEY, COINGECKO_MARKETS_VS_CURRENCY
from data.universe_manifest_store import save_universe_manifest

NASDAQLISTED_URL = 'https://www.nasdaqtrader.com/dynamic/symdir/nasdaqlisted.txt'
OTHERLISTED_URL = 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt'
IDX_STOCK_LIST_URL = 'https://www.idx.co.id/en/market-data/stocks-data/stock-list'
COINGECKO_COINS_LIST_URL = f'{COINGECKO_API_BASE}/coins/list'
COINGECKO_COINS_MARKETS_URL = f'{COINGECKO_API_BASE}/coins/markets'


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'user-agent': 'MacroRegimePro/0.30', 'accept': 'application/json, text/plain, text/html'})
    if COINGECKO_DEMO_API_KEY:
        s.headers['x-cg-demo-api-key'] = COINGECKO_DEMO_API_KEY
    return s


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_text(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def _fetch_json(session: requests.Session, url: str, params: dict[str, Any] | None = None) -> Any:
    r = session.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def build_us_manifest(session: requests.Session) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for url, venue in ((NASDAQLISTED_URL, 'nasdaq'), (OTHERLISTED_URL, 'other')):
        text = _fetch_text(session, url)
        reader = csv.DictReader(io.StringIO(text), delimiter='|')
        for row in reader:
            if not row:
                continue
            symbol = str(row.get('Symbol') or row.get('NASDAQ Symbol') or row.get('CQS Symbol') or row.get('ACT Symbol') or '').strip()
            if not symbol or symbol.lower().startswith('file creation time'):
                continue
            test_issue = str(row.get('Test Issue', 'N')).strip().upper()
            if test_issue == 'Y':
                continue
            if symbol not in {r['symbol'] for r in records}:
                records.append({
                    'symbol': symbol,
                    'name': str(row.get('Security Name') or row.get('Company Name') or '').strip(),
                    'exchange_source': venue,
                    'exchange_code': str(row.get('Exchange') or row.get('Market Category') or '').strip(),
                    'is_etf': str(row.get('ETF', 'N')).strip().upper() == 'Y',
                    'round_lot_size': str(row.get('Round Lot Size') or '').strip(),
                })
    return {
        'market': 'us',
        'generated_at': _now(),
        'source': 'NasdaqTrader symbol directory',
        'sources': [NASDAQLISTED_URL, OTHERLISTED_URL],
        'symbols': [r['symbol'] for r in records],
        'records': records,
        'stats': {
            'count': len(records),
            'etf_count': sum(1 for r in records if r.get('is_etf')),
        },
    }


def build_ihsg_manifest(session: requests.Session) -> dict[str, Any]:
    html = _fetch_text(session, IDX_STOCK_LIST_URL)
    soup = BeautifulSoup(html, 'lxml')
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in soup.select('table tr'):
        cells = [c.get_text(' ', strip=True) for c in row.find_all(['td', 'th'])]
        if not cells:
            continue
        code = cells[0].strip().upper()
        if not re.fullmatch(r'[A-Z]{4,5}', code):
            continue
        symbol = f'{code}.JK'
        if symbol in seen:
            continue
        seen.add(symbol)
        records.append({
            'symbol': symbol,
            'code': code,
            'name': cells[1].strip() if len(cells) > 1 else code,
        })
    return {
        'market': 'ihsg',
        'generated_at': _now(),
        'source': 'IDX stock list',
        'sources': [IDX_STOCK_LIST_URL],
        'symbols': [r['symbol'] for r in records],
        'records': records,
        'stats': {'count': len(records)},
    }


def build_crypto_manifest(session: requests.Session, enrich_pages: int = 20) -> dict[str, Any]:
    base_list = _fetch_json(session, COINGECKO_COINS_LIST_URL, params={'include_platform': 'false'}) or []
    by_id: dict[str, dict[str, Any]] = {}
    for row in base_list:
        coin_id = str((row or {}).get('id', '')).strip()
        if not coin_id:
            continue
        by_id[coin_id] = {
            'symbol': f'CG:{coin_id}',
            'coin_id': coin_id,
            'raw_symbol': str((row or {}).get('symbol', '')).strip().upper(),
            'name': str((row or {}).get('name', '')).strip() or coin_id,
        }

    market_pages_loaded = 0
    for page in range(1, max(1, int(enrich_pages)) + 1):
        rows = _fetch_json(session, COINGECKO_COINS_MARKETS_URL, params={'vs_currency': COINGECKO_MARKETS_VS_CURRENCY, 'order': 'market_cap_desc', 'per_page': 250, 'page': page, 'sparkline': 'false'}) or []
        if not rows:
            break
        market_pages_loaded += 1
        for row in rows:
            coin_id = str((row or {}).get('id', '')).strip()
            if coin_id not in by_id:
                continue
            by_id[coin_id].update({
                'market_cap_rank': row.get('market_cap_rank'),
                'current_price': row.get('current_price'),
                'market_cap': row.get('market_cap'),
                'total_volume': row.get('total_volume'),
                'last_updated': row.get('last_updated'),
            })

    records = sorted(by_id.values(), key=lambda x: (x.get('market_cap_rank') is None, x.get('market_cap_rank') or 10**12, x.get('coin_id') or ''))
    return {
        'market': 'crypto',
        'generated_at': _now(),
        'source': 'CoinGecko coins list + coins markets',
        'sources': [COINGECKO_COINS_LIST_URL, COINGECKO_COINS_MARKETS_URL],
        'symbols': [r['symbol'] for r in records],
        'records': records,
        'stats': {
            'count': len(records),
            'market_pages_loaded': market_pages_loaded,
            'ranked_count': sum(1 for r in records if r.get('market_cap_rank') is not None),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Build full-universe manifests for US, IHSG, and crypto.')
    parser.add_argument('--markets', nargs='+', default=['us', 'ihsg', 'crypto'])
    parser.add_argument('--crypto-enrich-pages', type=int, default=20)
    args = parser.parse_args()

    session = _session()
    out: dict[str, Any] = {}
    for market in [m.lower().strip() for m in args.markets]:
        if market == 'us':
            payload = build_us_manifest(session)
        elif market == 'ihsg':
            payload = build_ihsg_manifest(session)
        elif market == 'crypto':
            payload = build_crypto_manifest(session, enrich_pages=args.crypto_enrich_pages)
        else:
            continue
        save_universe_manifest(market, payload)
        out[market] = {'count': len(payload.get('symbols', []) or []), 'generated_at': payload.get('generated_at'), 'source': payload.get('source')}
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
