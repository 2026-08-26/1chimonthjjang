"""Export the actual CSV aggregates as a self-contained presentation HTML."""
import argparse
import json
from pathlib import Path
from datetime import datetime
from web.dashboard_data import ROOT, load_dashboard

def export(destination):
    data=load_dashboard()
    html=(ROOT/'templates/dashboard/index.html').read_text()
    css=(ROOT/'static/dashboard/dashboard.css').read_text()
    js=(ROOT/'static/dashboard/dashboard.js').read_text()
    payload=json.dumps(data,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    html=html.replace('<link rel="stylesheet" href="/static/dashboard/dashboard.css">','<style>'+css+'</style>')
    html=html.replace('<script src="/static/dashboard/dashboard.js" defer></script>', '<script id="dashboard-snapshot" type="application/json">'+payload+'</script><script>'+js+'</script>')
    html=html.replace('CSV 기반 분석 · 분야별 기준 시점 상이',f'CSV 스냅샷 · {datetime.now():%Y-%m-%d %H:%M} 생성 · 재집계 시 재내보내기')
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(html,encoding='utf-8')
    print(destination.resolve())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='dashboard.html');args=p.parse_args();export(args.output)
