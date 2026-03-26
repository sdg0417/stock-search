"""
KRX 전 종목(코스피+코스닥) → data/kr_stocks.json 저장
실행: python scripts/fetch_kr_stocks.py

[A-2] 부분 실패 시 파일을 저장하지 않도록 수정
"""
import json
import os
import sys
from datetime import datetime

try:
    import FinanceDataReader as fdr
except ImportError:
    print("pip install finance-datareader")
    sys.exit(1)

OUTPUT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'kr_stocks.json')
)


def main():
    all_stocks = []
    failed_markets = []

    for market, suffix in [('KOSPI', 'KS'), ('KOSDAQ', 'KQ')]:
        print(f'{market} 가져오는 중...', flush=True)
        try:
            df = fdr.StockListing(market)
            market_stocks = []
            for _, row in df.iterrows():
                code = str(row['Code']).strip().zfill(6)
                name = str(row['Name']).strip()
                if code and name:
                    market_stocks.append({
                        'symbol': f'{code}.{suffix}',
                        'name':   name,
                        'market': market,
                    })
            all_stocks.extend(market_stocks)
            print(f'  → {len(market_stocks)}개')
        except Exception as e:
            print(f'  오류: {e}')
            failed_markets.append(market)

    # [A-2] 하나라도 실패하면 파일 저장 차단 — 부분 데이터 덮어쓰기 방지
    if failed_markets:
        print(f'\n오류: {", ".join(failed_markets)} 데이터 수집 실패. 파일을 저장하지 않습니다.')
        print('기존 파일이 있다면 그대로 유지됩니다.')
        sys.exit(1)

    if not all_stocks:
        print('데이터 없음')
        sys.exit(1)

    all_stocks.sort(key=lambda x: x['name'])
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({
            'updated': datetime.now().strftime('%Y-%m-%d'),
            'count':   len(all_stocks),
            'stocks':  all_stocks,
        }, f, ensure_ascii=False, indent=2)

    print(f'\n완료: {OUTPUT}  (총 {len(all_stocks)}개)')


if __name__ == '__main__':
    main()
