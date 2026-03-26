#!/usr/bin/env python3
"""주가 검색 앱 로컬 서버 - Yahoo Finance 프록시"""
import http.server
import urllib.request
import urllib.parse
import json
import os
import re
import webbrowser
import threading

PORT = 5000

# [A-1] 공용 상수 (api/_common.py 와 동일하게 유지 — 로컬 서버는 단독 실행)
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept':          'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer':         'https://finance.yahoo.com/',
    'Origin':          'https://finance.yahoo.com',
}

HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']

# [W-1] 심볼 화이트리스트 패턴 — api/quote.py 와 동일한 규칙
SYMBOL_RE = re.compile(r'^[A-Za-z0-9.\-^=+]{1,20}$')


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {args[0]} {args[1]}')

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/quote/'):
            symbol = urllib.parse.unquote(path[len('/api/quote/'):])
            # [W-1] 심볼 입력 검증 추가
            if not SYMBOL_RE.match(symbol):
                self.send_error(400, 'Invalid symbol')
                return
            # [A-4] f-string + .format() 혼용 제거 — 변수 직접 삽입
            self._proxy_quote(symbol)

        elif path == '/api/search':
            q = urllib.parse.parse_qs(parsed.query).get('q', [''])[0]
            has_korean = any('\uac00' <= c <= '\ud7a3' for c in q)
            if has_korean:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'quotes': []}).encode())
                return
            # [A-4] f-string + .format() 혼용 제거
            self._proxy_search(q)

        elif path in ('/', '/index.html', '/stock-search.html'):
            self._serve_html()

        else:
            self.send_error(404)

    def _proxy_quote(self, symbol: str):
        """quote 엔드포인트: query1 → query2 순서로 시도"""
        encoded = urllib.parse.quote(symbol)
        last_err = None
        for host in HOSTS:
            url = f'https://{host}/v8/finance/chart/{encoded}?interval=1d&range=1d&includePrePost=false'
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                last_err = e

        # [C-1] 내부 에러 메시지(str(last_err)) 클라이언트 노출 제거
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'chart': {'result': None, 'error': None}, 'quotes': []}).encode())

    def _proxy_search(self, q: str):
        """search 엔드포인트: query1 → query2 순서로 시도"""
        encoded = urllib.parse.quote(q)
        last_err = None
        for host in HOSTS:
            url = (
                f'https://{host}/v1/finance/search'
                f'?q={encoded}&quotesCount=10&newsCount=0'
                f'&enableFuzzyQuery=true&region=US&lang=en-US'
            )
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                last_err = e

        # [C-1] 내부 에러 메시지 숨김
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'quotes': []}).encode())

    def _serve_html(self):
        html_path = os.path.join(os.path.dirname(__file__), 'stock-search.html')
        try:
            with open(html_path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404, 'stock-search.html not found')


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(('localhost', PORT), Handler)
    url = f'http://localhost:{PORT}'
    print(f'\n  주가 검색 앱 시작!')
    print(f'  브라우저: {url}')
    print(f'  종료: Ctrl+C\n')
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n  서버 종료')
