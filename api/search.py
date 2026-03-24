from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import os
import difflib
import unicodedata
import re

# ── 한국 주식 데이터 로드 ────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KR_JSON = os.path.join(_BASE, 'data', 'kr_stocks.json')

_kr_stocks: list[dict] = []
_kr_names:  list[str]  = []   # 정규화된 이름 (검색용)

def _normalize(s: str) -> str:
    """공백·특수문자 제거, 소문자 변환"""
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'[\s\-_·&()\[\]]', '', s).lower()
    return s

def _load():
    global _kr_stocks, _kr_names
    if _kr_stocks:
        return
    try:
        with open(_KR_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        _kr_stocks = data.get('stocks', [])
        _kr_names  = [_normalize(s['name']) for s in _kr_stocks]
    except FileNotFoundError:
        pass

def _search_kr(q: str, n: int = 10) -> list[dict]:
    _load()
    if not _kr_stocks:
        return []

    key = _normalize(q)
    seen: set[str] = set()
    results: list[dict] = []

    def add(stock: dict):
        if stock['symbol'] not in seen:
            seen.add(stock['symbol'])
            results.append(stock)

    # 1순위: 완전 일치
    for i, nname in enumerate(_kr_names):
        if nname == key:
            add(_kr_stocks[i])

    # 2순위: 앞부분 일치
    for i, nname in enumerate(_kr_names):
        if nname.startswith(key):
            add(_kr_stocks[i])

    # 3순위: 부분 포함
    for i, nname in enumerate(_kr_names):
        if key in nname:
            add(_kr_stocks[i])

    # 4순위: 오타 허용 퍼지 매칭 (cutoff 조절로 민감도 설정)
    if len(results) < n:
        cutoff = max(0.55, 1.0 - len(key) * 0.08)  # 짧을수록 엄격하게
        close = difflib.get_close_matches(key, _kr_names, n=n * 2, cutoff=cutoff)
        for match in close:
            for i, nname in enumerate(_kr_names):
                if nname == match:
                    add(_kr_stocks[i])
                    break

    return results[:n]


# ── Yahoo Finance 검색 (영문/티커) ───────────────────────────
_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer':    'https://finance.yahoo.com/',
}

def _search_yahoo(q: str) -> list[dict]:
    url = (
        'https://query1.finance.yahoo.com/v1/finance/search'
        f'?q={urllib.parse.quote(q)}&quotesCount=10&newsCount=0&enableFuzzyQuery=true'
    )
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data.get('quotes', [])


def _has_korean(s: str) -> bool:
    return bool(re.search(r'[\uac00-\ud7a3]', s))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query).get('q', [''])[0].strip()

        if not q:
            self._ok([])
            return

        try:
            if _has_korean(q):
                # 한글 → 로컬 JSON + 퍼지 매칭
                stocks = _search_kr(q)
                quotes = [
                    {
                        'symbol':    s['symbol'],
                        'longname':  s['name'],
                        'shortname': s['name'],
                        'quoteType': 'EQUITY',
                        'exchange':  s['market'],
                    }
                    for s in stocks
                ]
                self._ok(quotes)
            else:
                # 영문 → Yahoo Finance
                quotes = _search_yahoo(q)
                self._ok(quotes)
        except Exception as e:
            self._ok([], error=str(e))

    def _ok(self, quotes: list, error: str = ''):
        body = json.dumps({'quotes': quotes, 'error': error}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
