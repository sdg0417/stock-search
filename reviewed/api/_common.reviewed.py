"""
api/_common.py — 공용 상수 모듈
[A-1] HEADERS / HOSTS 가 3곳(server.py, quote.py, search.py)에 중복 정의되어
      User-Agent 변경 시 모두 수정해야 하는 문제를 해결.
      이 파일 하나에서 관리한다.
"""

HEADERS: dict[str, str] = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept':          'application/json',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    'Referer':         'https://finance.yahoo.com/',
    'Origin':          'https://finance.yahoo.com',
}

HOSTS: list[str] = [
    'query1.finance.yahoo.com',
    'query2.finance.yahoo.com',
]
