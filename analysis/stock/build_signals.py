"""Run from the repository root: python analysis/stock/build_signals.py --input PATH"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def build(source, destination):
    df = pd.read_csv(source, dtype={'종목코드': str})
    mapping = {'날짜':'date','시장':'market','종목코드':'code','종목명':'name','종가':'close','거래량':'volume','거래대금_원':'value','상장주식수':'shares','등락률_pct':'change'}
    missing = set(mapping) - set(df.columns)
    if missing:
        raise ValueError(f'Missing columns: {sorted(missing)}')
    df = df.rename(columns=mapping)[list(mapping.values())]
    df['date'] = pd.to_datetime(df['date'], errors='raise')
    if df.duplicated(['date','market','code']).any():
        raise ValueError('Duplicate date/market/code')
    for c in ['close','volume','value','shares','change']:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', ''), errors='coerce')
    df = df.sort_values(['market','code','date']).reset_index(drop=True)
    groups = df.groupby(['market','code'], sort=False)
    df['volume_avg20'] = groups.volume.transform(lambda x:x.shift(1).rolling(20,min_periods=20).mean())
    df['volume_ratio'] = df.volume / df.volume_avg20.where(df.volume_avg20 > 0)
    df['return5'] = groups.close.transform(lambda x:x / x.shift(5) - 1) * 100
    df['return20'] = groups.close.transform(lambda x:x / x.shift(20) - 1) * 100
    df['share_pct'] = df.value / df.groupby(['date','market']).value.transform('sum').replace(0,np.nan) * 100
    df['share_avg20'] = df.groupby(['market','code']).share_pct.transform(lambda x:x.shift(1).rolling(20,min_periods=20).mean())
    df['share_ratio'] = df.share_pct / df.share_avg20.where(df.share_avg20 > 0)
    previous_shares = groups.shares.shift(1)
    # Corporate action suspicion, not a definitive split classification.
    df['shares_changed'] = previous_shares.notna() & df.shares.ne(previous_shares)
    df['recent_share_change'] = df.groupby(['market','code']).shares_changed.transform(lambda x:x.rolling(21,min_periods=1).max()).astype(bool)
    df['inactive'] = df.volume.isna() | (df.volume <= 0) | df.close.isna() | (df.close <= 0)
    df['recent_inactive'] = df.groupby(['market','code']).inactive.transform(lambda x:x.rolling(21,min_periods=1).max()).astype(bool)
    df['eligible'] = df.volume_avg20.notna() & ~df.recent_inactive & ~df.recent_share_change & (df.value >= 1_000_000_000)
    # Initial editorial filters: turnover >= KRW 1bn; volume >=3x;
    # absolute 5-session raw-price return >=10%; market value-share >=3x and >=0.1%.
    df['volume_signal'] = df.eligible & (df.volume_ratio >= 3)
    df['price_signal'] = df.eligible & (df.return5.abs() >= 10)
    df['concentration_signal'] = df.eligible & (df.share_ratio >= 3) & (df.share_pct >= .1)
    df['signal_count'] = df[['volume_signal','price_signal','concentration_signal']].sum(axis=1)
    df['score'] = pd.concat([df.volume_ratio/3, df.return5.abs()/10, df.share_ratio/3],axis=1).max(axis=1)
    destination.mkdir(parents=True,exist_ok=True)
    df['date'] = df.date.dt.strftime('%Y-%m-%d')
    df = df.replace([np.inf,-np.inf],np.nan)
    df.to_csv(destination/'stock_daily.csv',index=False,encoding='utf-8-sig')
    signals = df[df.signal_count > 0].sort_values(['date','signal_count','score'],ascending=False)
    signals.to_csv(destination/'all_stock_signals.csv',index=False,encoding='utf-8-sig')
    metadata = {'latest_date':df.date.max(),'rows':len(df),'signal_rows':len(signals),'latest_candidates':int(signals.date.eq(df.date.max()).sum()),'source':'한국거래소 통계정보','source_url':'https://openapi.krx.co.kr/','note':'수정주가 미적용. 상장주식수 변동과 무거래 관측치가 최근 21개 관측치에 포함된 종목은 제외. 변동 원인은 별도 확인 필요.'}
    (destination/'stock_meta.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(metadata,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',default=str(ROOT/'data/raw/stock/krx_all_stocks_1y.csv'))
    parser.add_argument('--output',default=str(ROOT/'result/stock'))
    args = parser.parse_args()
    build(Path(args.input),Path(args.output))
