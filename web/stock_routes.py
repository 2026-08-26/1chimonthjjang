import json
from functools import lru_cache
from pathlib import Path
import pandas as pd
from flask import Blueprint, abort, render_template, request, jsonify
from stock_ai_agent import StockAIAgent

stock_bp = Blueprint('stock',__name__)
stock_ai_agent = StockAIAgent()
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'result/stock'

@lru_cache(maxsize=4)
def _read(path, modified):
    return pd.read_csv(path,dtype={'code':str,'종목코드':str}).fillna('')

def read(name):
    path = DATA/name
    if not path.exists():
        abort(503,description='주식 분석 파일이 없습니다. build_signals.py를 먼저 실행하세요.')
    return _read(str(path),path.stat().st_mtime_ns)

def records(df):
    return json.loads(df.to_json(orient='records',force_ascii=False))

def labels(row):
    names = []
    for key,title in [('volume_signal','거래량 급증'),('price_signal','5거래일 가격 급변'),('concentration_signal','거래대금 쏠림')]:
        if row[key]: names.append(title)
    return names

@stock_bp.route('/stock')
def index():
    daily = read('stock_daily.csv')
    dates = sorted(daily.date.unique(),reverse=True)
    selected = request.args.get('date',dates[0])
    market = request.args.get('market','ALL')
    if selected not in dates or market not in ['ALL','KOSPI','KOSDAQ']: abort(400)
    signals = read('all_stock_signals.csv')
    selected_rows = signals[signals.date.eq(selected)]
    if market != 'ALL': selected_rows = selected_rows[selected_rows.market.eq(market)]
    items = records(selected_rows.sort_values(['signal_count','score'],ascending=False).head(10))
    for item in items: item['labels'] = labels(item)
    return render_template('stock/index.html',items=items,dates=dates,selected=selected,market=market,count=len(selected_rows))

@stock_bp.route('/stock/<market>/<code>/<date>')
def detail(market,code,date):
    signals = read('all_stock_signals.csv')
    found = signals[signals.market.eq(market)&signals.code.eq(code)&signals.date.eq(date)]
    if found.empty: abort(404)
    item = records(found.head(1))[0]
    item['labels'] = labels(item)
    daily = read('stock_daily.csv')
    history = daily[daily.market.eq(market)&daily.code.eq(code)&(daily.date<=date)].sort_values('date')
    # Fetch actual OHLC from the local KRX source for this stock only.
    raw_path = ROOT/'data/raw/stock/krx_all_stocks_1y.csv'
    if raw_path.exists():
        raw = _read(str(raw_path),raw_path.stat().st_mtime_ns)
        selected = raw[raw['종목코드'].eq(code)&raw['시장'].eq(market)]
        prices = selected[['날짜','시가','고가','저가']].rename(columns={'날짜':'date','시가':'open','고가':'high','저가':'low'})
        history = history.merge(prices,on='date',how='left',validate='one_to_one')
    else:
        history = history.assign(open=None,high=None,low=None)
    for col in ['open','high','low']:
        history[col] = pd.to_numeric(history[col],errors='coerce')
    history = records(history[['date','open','high','low','close','volume']])
    questions = ['같은 시기 실적 발표나 주요 계약·투자 공시가 있었나?','주식분할·병합·유상증자·거래 재개가 수치에 영향을 줬나?','투자자별 매매 동향과 업종 흐름에서도 같은 변화가 확인되나?']
    return render_template('stock/detail.html',item=item,history=history,questions=questions)

@stock_bp.route('/api/stock-report/<market>/<code>/<date>',methods=['POST'])
def stock_report(market,code,date):
    signals=read('all_stock_signals.csv')
    found=signals[signals.market.eq(market)&signals.code.eq(code)&signals.date.eq(date)]
    if found.empty: return jsonify({'error':'주식 시그널을 찾을 수 없습니다.'}),404
    item=records(found.head(1))[0]
    payload=request.get_json(silent=True) or {}
    if not isinstance(payload,dict): return jsonify({'error':'잘못된 요청입니다.'}),400
    return jsonify(stock_ai_agent.generate_report(item,include_news=payload.get('include_news') is True))
