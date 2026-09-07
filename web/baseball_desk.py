"""Baseball desk: CSV-backed selection, official profiles and article drafts."""
import csv
import html
import re
import time
import ssl
import subprocess
from urllib.error import URLError
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from flask import Blueprint, jsonify, request
import pandas as pd
from baseball_ai_agent import BaseballAIAgent
from web.article_draft import attach_draft, draft_response

baseball_desk_bp=Blueprint('baseball_desk',__name__)
ROOT=Path(__file__).resolve().parents[1]
KINDS={'temp':'기온','humidity':'습도','rain':'강수'}
_cache={}

def signals():
    frames=[]
    for kind,label in KINDS.items():
        df=pd.read_csv(ROOT/f'data/processed/{kind}_signal.csv')
        df['kind']=kind;df['weather_type']=label;df['weather_group']=df[f'{kind}_group']
        frames.append(df)
    return pd.concat(frames,ignore_index=True)

def parse_profile(body,name):
    def value(key):
        match=re.search(r'<span[^>]*id="[^"]*_'+key+r'"[^>]*>(.*?)</span>',body,re.S)
        return html.unescape(re.sub('<[^>]+>','',match.group(1))).strip() if match else ''
    if value('lblName')!=name:
        return {}
    photo=re.search(r'<img[^>]*id="[^"]*_imgProgile"[^>]*src="([^"]+)"',body)
    image=html.unescape(photo.group(1)) if photo else ''
    if image.startswith('//'):image='https:'+image
    if urlparse(image).scheme!='https' or urlparse(image).hostname not in ('6ptotvmi5753.edge.naverncp.com','www.koreabaseball.com'):image=''
    return dict(photo=image,birthday=value('lblBirthday'),position=value('lblPosition'),physique=value('lblHeightWeight'),career=value('lblCareer'))

@baseball_desk_bp.get('/api/baseball-player')
def player():
    name=request.args.get('name','')
    with open(ROOT/'data/raw/KBO_player_info_full.csv',encoding='utf-8-sig') as f:
        matches=[r for r in csv.DictReader(f) if r['선수명']==name and r.get('season_2019') not in ('','소속팀없음')]
    if len(matches)!=1:
        return jsonify(name=name,team='확인 필요',status='선수 ID를 정확히 식별할 수 없습니다.',photo='')
    row=matches[0];pid=row['ID']
    if not pid.isdigit():return jsonify(error='선수 ID 오류'),400
    url=f'https://www.koreabaseball.com/Record/Player/HitterDetail/Basic.aspx?playerId={pid}'
    profile=dict(name=name,team=row['season_2019'],id=pid,source_url=url,photo='',status='공식 프로필을 불러오지 못했습니다. 원문에서 확인해주세요.')
    cached=_cache.get(pid)
    if cached and time.monotonic()-cached[0]<3600:
        return jsonify(cached[1])
    try:
        try:
            with urlopen(Request(url,headers={'User-Agent':'DATA-TIP-OFF/1.0'}),timeout=8) as response:body=response.read(1_000_001)
        except URLError as exc:
            if not isinstance(exc.reason, ssl.SSLCertVerificationError):raise
            # System curl uses the OS trust store on macOS; TLS validation stays enabled.
            body=subprocess.run(['curl','--fail','--silent','--show-error','--proto','=https','--max-time','8','--max-filesize','1000000',url],capture_output=True,check=True,timeout=10).stdout
        if len(body)>1_000_000:raise ValueError('Too large')
        details=parse_profile(body.decode('utf-8'),name)
        if details:
            profile.update(details,status='사진·프로필: KBO 공식 페이지 조회 기준 / 팀: 2019 시즌 데이터 기준')
            _cache[pid]=(time.monotonic(),profile)
    except Exception:pass
    return jsonify(profile)

@baseball_desk_bp.post('/api/baseball-desk-report')
def report():
    payload=request.get_json(silent=True) or {}
    if not isinstance(payload,dict):return jsonify(error='잘못된 요청입니다.'),400
    df=signals()
    if payload.get('name'):
        df=df[(df.player_name==payload['name'])&(df.kind==payload.get('kind'))&(df.weather_group==payload.get('group'))]
    if df.empty:return jsonify(error='선택한 선수 조건을 찾을 수 없습니다.'),404
    item=df.loc[df.signal_score.abs().idxmax()].to_dict()
    result=BaseballAIAgent().generate_report(item)
    metrics=[]
    for label,key,digits,unit in [('시즌 타율','season_avg',3,''),('조건 타율','weather_avg',3,''),('타율 차이','weather_diff',3,''),('조건 경기','games',0,'경기'),('조건 타수','AB',0,'타수'),('신호 점수','signal_score',2,'')]:
        value=float(item[key]);metrics.append(dict(label=label,value=format(value,('+' if key=='weather_diff' else '')+f'.{digits}f')+unit,direction='up' if key=='weather_diff' and value>0 else 'down' if key=='weather_diff' and value<0 else ''))
    result.update(metrics=metrics,region=item['player_name'],period='2019 시즌',articles=[],selection=dict(name=item['player_name'],kind=item['kind'],group=str(item['weather_group'])))
    return jsonify(attach_draft(result,f"{item['weather_type']} · {item['weather_group']} 조건의 타격 변화"))

baseball_desk_bp.add_url_rule('/api/baseball-desk-draft',view_func=draft_response,methods=['POST'])
