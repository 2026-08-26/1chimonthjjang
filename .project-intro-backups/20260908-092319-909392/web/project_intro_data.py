"""Small presentation view of the existing CSV-backed dashboard. Read only."""
from web.dashboard_data import load_dashboard

def load_intro():
    d=load_dashboard();e=d['evidence'];social=d['social'];latest=social['latest']
    falling=[r for r in latest if r['Natural_growth'] is not None and r['Natural_growth']<0]
    econ_case=d['economy']['top'][0] if d['economy']['top'] else None
    econ_rows=[r for r in d['economy']['data'] if econ_case and r['Region']==econ_case['target'] and r['Date']<=econ_case['date']]
    econ_rows=sorted(econ_rows,key=lambda r:r['Date'])[-24:]
    stock=sorted([r for r in d['stock']['data'] if r.get('volume_ratio') is not None],key=lambda r:r['volume_ratio'],reverse=True)[:6]
    bat=d['baseball']['top'][0] if d['baseball']['top'] else None
    demo=d['content']['data'][0] if d['content']['data'] else None
    return dict(
        domains=d['overview']['domains'],
        social=dict(date=social['latest_date'],regions=len(latest),decline=len(falling),inflow=sum(r['Net_migration']>0 for r in falling),outflow=sum(r['Net_migration']<0 for r in falling),rows=latest),
        economy=dict(case=econ_case,rows=econ_rows),
        stock=dict(date=d['stock']['latest'],candidates=d['stock']['latest_count'],rows=stock),
        baseball=dict(case=bat,rows=d['baseball']['rows'],eligible=d['baseball']['eligible']),
        content=dict(case=demo,total=d['content']['rows']),
        lineage=e['lineage'],provenance=e['provenance'],useful=e['useful'],excluded=e['excluded'],
        sources=[dict(file=s['file'],rows=s['rows'],period=s['period']) for s in d['sources']],
    )
