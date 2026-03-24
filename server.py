#!/usr/bin/env python3
"""주가 검색 앱 로컬 서버 - Yahoo Finance 프록시"""
import http.server
import urllib.request
import urllib.parse
import json
import os
import webbrowser
import threading

PORT = 5000
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer': 'https://finance.yahoo.com/',
    'Origin': 'https://finance.yahoo.com',
}

HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f'  {args[0]} {args[1]}')

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/quote/'):
            symbol = urllib.parse.unquote(path[len('/api/quote/'):])
            base = f'https://{{host}}/v8/finance/chart/{urllib.parse.quote(symbol)}?interval=1d&range=1d&includePrePost=false'
            self.proxy(base)

        elif path == '/api/search':
            q = urllib.parse.parse_qs(parsed.query).get('q', [''])[0]
            has_korean = any('\uac00' <= c <= '\ud7a3' for c in q)
            if has_korean:
                # Yahoo Finance search API가 한글 쿼리를 지원하지 않음 → 빈 결과 반환
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'quotes': []}).encode())
                return
            base = (
                f'https://{{host}}/v1/finance/search'
                f'?q={urllib.parse.quote(q)}&quotesCount=10&newsCount=0'
                f'&enableFuzzyQuery=true&region=US&lang=en-US'
            )
            self.proxy(base)

        elif path in ('/', '/index.html', '/stock-search.html'):
            self.serve_html()

        else:
            self.send_error(404)

    def proxy(self, url_template):
        """query1 → query2 순서로 시도, 첫 성공 결과를 반환"""
        last_err = None
        for host in HOSTS:
            url = url_template.format(host=host)
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
                continue

        # 두 호스트 모두 실패 → 빈 result 응답
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'chart': {'result': None, 'error': str(last_err)},
                                     'quotes': []}).encode())

    def serve_html(self):
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
