from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import os
import difflib
import unicodedata
import re
import threading

# ── 한국 주식 데이터 로드 ────────────────────────────────────
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KR_JSON = os.path.join(_BASE, 'data', 'kr_stocks.json')

_kr_stocks: list[dict] = []
_kr_names:  list[str]  = []
_kr_name_to_idx: dict[str, int] = {}   # [I-1] 역방향 인덱스 — O(n²) → O(n)
_load_lock = threading.Lock()           # [W-3] Thread-safety


def _normalize(s: str) -> str:
    """공백·특수문자 제거, 소문자 변환"""
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'[\s\-_·&()\[\]]', '', s).lower()
    return s


def _load():
    """[W-3] 모듈 레벨 전역 데이터 로드 — Lock으로 경쟁 조건 방지"""
    global _kr_stocks, _kr_names, _kr_name_to_idx
    with _load_lock:
        if _kr_stocks:
            return
        try:
            with open(_KR_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
            stocks = data.get('stocks', [])
            names = [_normalize(s['name']) for s in stocks]
            # [I-1] 역방향 인덱스 구축 (동일 이름은 첫 번째 항목 우선)
            idx_map: dict[str, int] = {}
            for i, name in enumerate(names):
                if name not in idx_map:
                    idx_map[name] = i
            _kr_stocks = stocks
            _kr_names = names
            _kr_name_to_idx = idx_map
        # [F-3] JSONDecodeError도 함께 처리 — 손상된 파일로 인한 크래시 방지
        except (FileNotFoundError, json.JSONDecodeError):
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

    # 4순위: 오타 허용 퍼지 매칭 — [I-1] O(n²) → O(n) 역방향 인덱스 활용
    if len(results) < n:
        cutoff = max(0.55, 1.0 - len(key) * 0.08)
        close = difflib.get_close_matches(key, _kr_names, n=n * 2, cutoff=cutoff)
        for match in close:
            idx = _kr_name_to_idx.get(match)
            if idx is not None:
                add(_kr_stocks[idx])

    return results[:n]


# ── Yahoo Finance 검색 (영문/티커) ───────────────────────────
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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

        # [F-4] 검색어 길이 제한 — 과도하게 긴 입력 차단
        if len(q) > 100:
            self._ok([])
            return

        try:
            if _has_korean(q):
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
                quotes = _search_yahoo(q)
                self._ok(quotes)
        except Exception:
            # [W-4] 내부 에러 메시지 숨김
            self._ok([], error='검색 중 오류가 발생했습니다.')

    def _ok(self, quotes: list, error: str = ''):
        body = json.dumps({'quotes': quotes, 'error': error}).encode()
        # [F-7] 에러 응답 형식 통일 — error가 있으면 500, 없으면 200
        status = 500 if error else 200
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
