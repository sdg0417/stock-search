from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json
import re

# [A-1] 공용 상수 임포트 — HEADERS/HOSTS 중복 제거
from api._common import HEADERS, HOSTS

# [W-1] 심볼 입력 검증 패턴 (기존 유지)
SYMBOL_RE = re.compile(r'^[A-Za-z0-9.\-^=+]{1,20}$')


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        symbol = urllib.parse.parse_qs(parsed.query).get('symbol', [''])[0]

        if not symbol:
            self._json(400, {'error': 'symbol required'})
            return

        # [W-1] 심볼 화이트리스트 검증
        if not SYMBOL_RE.match(symbol):
            self._json(400, {'error': 'invalid symbol format'})
            return

        last_err = None
        for host in HOSTS:
            url = (
                f'https://{host}/v8/finance/chart/'
                f'{urllib.parse.quote(symbol)}'
                f'?interval=1d&range=1d&includePrePost=false'
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

        # [C-1] 실패 시 내부 에러 메시지 숨김 — str(last_err) 노출 금지
        self._json(502, {'error': '데이터를 불러올 수 없습니다.'})

    def _json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
