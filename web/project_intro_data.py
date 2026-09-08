"""Small presentation view of the existing CSV-backed dashboard. Read only."""
from web.dashboard_data import load_dashboard, read, records
import pandas as pd
import numpy as np

def load_intro():
    d=load_dashboard();e=d['evidence'];social=d['social'];latest=social['latest']
    falling=[r for r in latest if r['Natural_growth'] is not None and r['Natural_growth']<0]
    econ_case=d['economy']['top'][0] if d['economy']['top'] else None
    econ_rows=[r for r in d['economy']['data'] if econ_case and r['Region']==econ_case['target'] and r['Date']<=econ_case['date']]
    econ_rows=sorted(econ_rows,key=lambda r:r['Date'])[-24:]
    stock=d['stock']['data']
    bat=d['baseball']['top'][0] if d['baseball']['top'] else None
    demo=d['content']['data'][0] if d['content']['data'] else None
    return dict(
        domains=d['overview']['domains'], overview=d['overview'], content_levels=d['content']['levels'],
        social=dict(national=social['national'],national_note=social['national_note'],date=social['latest_date'],regions=len(latest),decline=len(falling),inflow=sum(r['Net_migration']>0 for r in falling),outflow=sum(r['Net_migration']<0 for r in falling),rows=latest),
        economy=dict(case=econ_case,rows=econ_rows,all_rows=d['economy']['data']),
        stock=dict(date=d['stock']['latest'],candidates=d['stock']['latest_count'],rows=stock),
        baseball=dict(weather=weather_summary(),case=bat,rows=d['baseball']['rows'],eligible=d['baseball']['eligible']),
        content=dict(case=demo,total=d['content']['rows']),
        lineage=e['lineage'],provenance=e['provenance'],useful=e['useful'],excluded=e['excluded'],
        sources=d['sources'],
    )


def weather_summary():
    b=read('data/processed/baseball_weather_2019.csv')
    b=b[b.AB>0].copy()
    b=b[b.groupby('player_name').AB.transform('sum')>=100].copy()
    result={}
    for key,col,bins,labels in [('temperature','temperature',[-np.inf,15,25,np.inf],['≤15°C','15–25°C','>25°C']),('humidity','humidity',[-np.inf,50,70,np.inf],['≤50%','50–70%','>70%'])]:
        t=b[b[col].notna()].copy();t['condition']=pd.cut(t[col],bins=bins,labels=labels)
        g=t.groupby('condition',observed=True).agg(H=('H','sum'),AB=('AB','sum'),records=('H','size')).reset_index();g['avg']=g.H/g.AB
        result[key]=records(g)
    t=b[b.rainfall.notna()].copy();t['condition']=np.where(t.rainfall>0,'비 >0mm','비 없음 0mm')
    g=t.groupby('condition').agg(H=('H','sum'),AB=('AB','sum'),records=('H','size')).reset_index();g['avg']=g.H/g.AB
    result['rainfall']=records(g)
    return result
