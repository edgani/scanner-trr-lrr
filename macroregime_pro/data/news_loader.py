from __future__ import annotations
from typing import Dict, List
from xml.etree import ElementTree as ET
from urllib.parse import quote_plus
from datetime import datetime, timezone
import requests
from config.settings import LIVE_FETCH_ENABLED, NEWS_CACHE_TTL_SECONDS
from utils.streamlit_compat import st

_NEWS_QUERIES = [
    ("war_oil", "Iran OR Hormuz OR oil shock OR Middle East war site:reuters.com"),
    ("trade_policy", "tariff OR trade war OR sanctions site:reuters.com"),
    ("rates_treasury", "Treasury yields OR refunding OR long-end pressure site:reuters.com"),
    ("fed_inflation", "Fed OR inflation OR CPI OR PCE site:reuters.com"),
]


def _parse_rss(xml_text: str) -> List[Dict[str, str]]:
    root = ET.fromstring(xml_text)
    out: List[Dict[str, str]] = []
    for item in root.findall('.//item')[:8]:
        title = (item.findtext('title') or '').strip()
        link = (item.findtext('link') or '').strip()
        pub = (item.findtext('pubDate') or '').strip()
        if title:
            out.append({'title': title, 'link': link, 'published': pub})
    return out


@st.cache_data(ttl=NEWS_CACHE_TTL_SECONDS, show_spinner=False)
def load_news_signals(*, force_refresh: bool = False) -> Dict[str, object]:
    if not LIVE_FETCH_ENABLED or not force_refresh:
        return {'state': 'quiet', 'counts': {'escalation': 0, 'relief': 0, 'oil': 0, 'rates': 0, 'usd': 0}, 'groups': {k: [] for k, _ in _NEWS_QUERIES}, 'top_headlines': [], 'generated_at': datetime.now(timezone.utc).isoformat()}
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    grouped: Dict[str, List[Dict[str, str]]] = {k: [] for k, _ in _NEWS_QUERIES}
    for key, query in _NEWS_QUERIES:
        url = f'https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en'
        try:
            resp = session.get(url, timeout=5)
            resp.raise_for_status()
            grouped[key] = _parse_rss(resp.text)
        except Exception:
            grouped[key] = []

    all_items = [x for items in grouped.values() for x in items]
    text_blob = ' || '.join(x['title'].lower() for x in all_items)
    escalation_words = ['strike', 'attack', 'war', 'escalat', 'threat', 'retaliat', 'sanction', 'tariff', 'surge', 'spike']
    relief_words = ['ceasefire', 'de-escalat', 'talk', 'truce', 'pause', 'withdraw', 'moderat', 'deal']
    oil_words = ['oil', 'hormuz', 'energy', 'opec']
    rates_words = ['yield', 'treasury', 'refunding', 'long-end', 'bond selloff']
    dollar_words = ['dollar', 'usd']

    esc = sum(w in text_blob for w in escalation_words)
    rel = sum(w in text_blob for w in relief_words)
    oil = sum(w in text_blob for w in oil_words)
    rates = sum(w in text_blob for w in rates_words)
    usd = sum(w in text_blob for w in dollar_words)

    if esc >= 3 and esc > rel:
        state = 'escalating'
    elif rel >= 2 and rel >= esc:
        state = 'de_escalating'
    elif all_items:
        state = 'active'
    else:
        state = 'quiet'

    return {
        'state': state,
        'counts': {
            'escalation': esc,
            'relief': rel,
            'oil': oil,
            'rates': rates,
            'usd': usd,
        },
        'groups': grouped,
        'top_headlines': all_items[:8],
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }
