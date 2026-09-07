"""Read-only dashboard aggregates. No regenerated observational data or cross-domain scores."""
from pathlib import Path
from functools import lru_cache
import json
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

def read(path):
    p = ROOT / path
    if not p.exists(): return pd.DataFrame()
    try: return pd.read_csv(p, low_memory=False)
    except UnicodeDecodeError: return pd.read_csv(p, encoding='cp949', low_memory=False)

def records(df):
    return json.loads(df.replace([np.inf, -np.inf], np.nan).to_json(orient='records', force_ascii=False))

def period(df, col='Date'):
    if col not in df or df.empty: return '기간 정보 없음'
    ds = pd.to_datetime(df[col], errors='coerce', format='mixed').dropna()
    return f'{ds.min():%Y.%m.%d} — {ds.max():%Y.%m.%d}' if len(ds) else '기간 정보 없음'

def signature():
    return tuple((str(p.relative_to(ROOT)), p.stat().st_mtime_ns, p.stat().st_size) for directory in ['data/raw','data/processed','result'] for p in sorted((ROOT/directory).rglob('*.csv')))

def dataset_meta(path, df):
    cols = df.columns.tolist()
    date_col = next((c for c in ['Date','game_date','일시','date','날짜'] if c in cols), None)
    span = period(df, date_col) if date_col and not ('year' in cols and date_col=='date') else '기간 정보 없음'
    if 'year' in cols and date_col=='date': span=f'{df.year.min()} — {df.year.max()} (연도)'
    if 'gameinfo' in cols and 'game_date' not in cols:
        span=period(pd.DataFrame({'Date':df.gameinfo.astype(str).str[:8]}))
    months=[c for c in cols if len(c)>=7 and c[:4].isdigit() and c[4] in '/.']
    if months: span=f'{months[0][:7]} — {months[-1][:7]} (월별 열)'
    return dict(file=path, rows=len(df), columns=cols, period=span, missing=int(df.isna().sum().sum()))

def load_dashboard(): return _build(signature())

@lru_cache(maxsize=1)
def _build(_signature):
    sources=[]
    for directory in ['data/raw','data/processed']:
        for p in sorted((ROOT/directory).rglob('*.csv')):
            path=str(p.relative_to(ROOT)); sources.append(dataset_meta(path,read(path)))
    for path in ['result/all_social_signals.csv','result/all_economy_signals.csv','result/stock/all_stock_signals.csv','result/stock/stock_daily.csv']:
        if (ROOT/path).exists(): sources.append(dataset_meta(path,read(path)))
    social=read('data/processed/social_monthly.csv')
    economy=read('data/processed/economy_monthly.csv')
    stock=read('result/stock/all_stock_signals.csv')
    stock_raw_available=(ROOT/'data/raw/stock/krx_all_stocks_1y.csv').is_file()
    stock_daily_available=(ROOT/'result/stock/stock_daily.csv').is_file()
    baseball=read('data/processed/baseball_weather_2019.csv')
    signals=[]; domain_counts=[]
    for domain,path,region in [('사회','result/all_social_signals.csv','Region_ko'),('경제','result/all_economy_signals.csv','Region')]:
        df=read(path)
        for r in records(df): signals.append(dict(domain=domain,target=r[region],date=r['Date'],signal=r['signal_name'],score=r['Signal_score'],level=r['severity'],reason=r.get('reason',''),source=path))
        domain_counts.append(dict(domain=domain,count=len(df),unit='지역 × 월 × 규칙',period=period(df)))
    if len(stock):
        latest=stock.date.max(); latest_stock=stock[stock.date==latest].copy()
        for r in records(stock):
            names=[label for c,label in [('volume_signal','거래량'),('price_signal','가격'),('concentration_signal','거래집중')] if r[c]]
            signals.append(dict(domain='주식',target=r['name'],date=r['date'],signal=' · '.join(names),score=r['score'],level='미분류',reason=f"{r['market']} · 동시 조건 {r['signal_count']}개",source='result/stock/all_stock_signals.csv'))
    else: latest=None; latest_stock=stock
    domain_counts.append(dict(domain='주식',count=len(stock),unit='종목 × 거래일',period=period(stock,'date')))
    weather=[]
    for key,group,label in [('temp','temp_group','기온'),('humidity','humidity_group','습도'),('rain','rain_group','강수')]:
        path=f'data/processed/{key}_signal.csv'; df=read(path)
        for r in records(df):
            strength=abs(r['signal_score']); level='HIGH' if strength>=.8 else 'MEDIUM' if strength>=.5 else 'LOW'
            row=dict(domain='야구',target=r['player_name'],date=None,signal=f"{label} · {r[group]}",score=strength,level=level,reason=f"{r['AB']}타수 · 조건 타율 {r['weather_avg']:.3f} · 시즌 대비 {r['weather_diff']:+.3f}",source=path,weather=label,condition=r[group],ab=r['AB'],avg=r['weather_avg'],diff=r['weather_diff'])
            signals.append(row); weather.append(row)
    domain_counts.append(dict(domain='야구',count=len(weather),unit='선수 × 날씨 조건',period=period(baseball,'game_date')))
    # Existing deterministic demo engine, never added to observational totals.
    from analysis.drama.mock_data import load_all_contents
    contents=load_all_contents()
    content_keys=['id','title','category','category_name','daily_data','z_score','increase_rate','trend_score','signal','signal_reason','baseline_avg','anomaly_threshold']
    content=[{k:r.get(k) for k in content_keys} for r in contents]
    counts={k:sum(r['level']==k for r in signals) for k in ['HIGH','MEDIUM','LOW','미분류']}
    # National row takes precedence; never double-count national and regional rows.
    national=social[social.Region_ko.isin(['전국','대한민국','전국계'])] if len(social) else social
    if len(national): national=national.sort_values('Date'); national_note='전국 행 사용'
    elif len(social):
        national=social.groupby('Date',as_index=False)[['Birth','Death','Natural_growth']].sum(min_count=1)
        national_note='보유 지역 합계 · 시점별 지역 커버리지 차이 가능'
    else: national_note='데이터 없음'
    latest_social=social[(social.Date==social.Date.max()) & ~social.Region_ko.isin(['전국','대한민국','전국계'])] if len(social) else social
    # Keep original game-level metric and eligibility used in 04_analysis.py.
    batting=baseball[baseball.AB>0].copy() if len(baseball) else baseball.copy()
    if len(batting):
        total_ab=batting.groupby('player_name').AB.transform('sum')
        batting=batting[total_ab>=100].copy(); batting['game_avg']=batting.H/batting.AB
        batting['rain_group']=np.where(batting.rainfall>0,'비','비없음')
        rain=batting[batting.rainfall.notna()].groupby('rain_group',as_index=False).agg(H=('H','sum'),AB=('AB','sum'),n=('AB','size'))
        rain['avg']=rain.H/rain.AB
    else: rain=pd.DataFrame()
    social_top=sorted([r for r in signals if r['domain']=='사회'],key=lambda r:r['score'],reverse=True)[:10]
    economy_top=sorted([r for r in signals if r['domain']=='경제'],key=lambda r:r['score'],reverse=True)[:10]
    per_domain={d:sorted([r for r in signals if r['domain']==d],key=lambda r:r['score'],reverse=True)[:10] for d in ['사회','경제','주식','야구']}
    from web.dashboard_evidence import build_evidence
    return dict(
        evidence=build_evidence(read,records),
        overview=dict(domains=sum([len(social)>0,len(economy)>0,len(stock)>0,len(baseball)>0,len(content)>0]),raw=sum(s['file'].startswith('data/raw/') for s in sources),processed=sum(s['file'].startswith('data/processed/') or s['file']=='result/stock/stock_daily.csv' for s in sources),total=len(signals),levels=counts,domains_detail=domain_counts),
        social=dict(period=period(social),rows=len(social),national=records(national),national_note=national_note,latest=records(latest_social),latest_date=None if social.empty else social.Date.max(),top=social_top),
        economy=dict(period=period(economy),rows=len(economy),data=records(economy),top=economy_top),
        stock=dict(raw_available=stock_raw_available,daily_available=stock_daily_available,period=period(stock,'date'),rows=len(stock),latest=latest,latest_count=len(latest_stock),data=records(latest_stock),thresholds='거래대금 10억 원 이상 · 최근 21개 관측치 내 무거래/상장주식수 변동 제외. 거래량 ≥ 직전 20일 평균 3배 · |5거래일 수익률| ≥ 10% · 거래대금 점유율 ≥ 평균 3배이면서 시장 내 0.1% 이상. HIGH/MEDIUM 등급은 원 코드에 없음.'),
        baseball=dict(period=period(baseball,'game_date'),rows=len(baseball),eligible=len(batting),players=0 if batting.empty else batting.player_name.nunique(),data=records(batting[[c for c in ['game_date','player_name','temperature','humidity','game_avg','AB','H'] if c in batting]]),rain=records(rain),top=sorted(weather,key=lambda r:r['score'],reverse=True)[:15]),
        content=dict(data=content,rows=len(content),levels={k:sum(r['signal']==k for r in content) for k in ['HIGH','MEDIUM','LOW']}),
        signals=dict(counts=domain_counts,levels=counts,top=per_domain),sources=sources,
        limitations=['Apart Deal.csv 원본이 없어 economy_monthly.csv의 원본 재현은 불가합니다.',('KRX 원본 및 stock_daily.csv 보유 여부: '+str(stock_raw_available)+' / '+str(stock_daily_available)+'. 주식 차트는 최신 거래일 시그널 후보만 비교하며, 실제 파일 행 수는 출처 화면에 표시합니다.'),'주식은 등급 미분류, 야구는 기존 BaseballAIAgent의 강도 기준(0.8 / 0.5)을 적용합니다. 분야 간 점수·발생 건수는 동일 척도가 아닙니다.','K콘텐츠 관심도는 기존 엔진의 고정 시드 시뮬레이션이며 실제 관측 시그널 합계에서 제외합니다.'])
