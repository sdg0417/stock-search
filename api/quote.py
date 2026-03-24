from http.server import BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Referer': 'https://finance.yahoo.com/',
    'Origin': 'https://finance.yahoo.com',
}
HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com']


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        symbol = urllib.parse.parse_qs(parsed.query).get('symbol', [''])[0]

        if not symbol:
            self._json(400, {'error': 'symbol required'})
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

        self._json(200, {'chart': {'result': None, 'error': str(last_err)}})

    def _json(self, status, obj):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
