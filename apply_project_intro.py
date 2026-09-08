"""Minimal, backed-up installer. Python standard library only."""
from pathlib import Path
import argparse,hashlib,json,datetime,shutil,sys

UPGRADE_HASHES = {'web/project_intro_data.py': ['43dd2c4472b0d3f3fb5b621cc4585006b4c61fdc6894456364edfece30862da7', '43dd2c4472b0d3f3fb5b621cc4585006b4c61fdc6894456364edfece30862da7', '8971c12c3dc7fadf8afdd986038ef65483742733c6911a405712f0de1e5f7230'], 'static/project_intro/intro.css': ['00af48b10af5d32a8701275a0fa1d258c3d4e38520b56976fe6fabaadb887bff', 'bfc80ae3b5c223666a2170725b9c244fe54342c4b6afce8952916fb149737cfb', 'baaa65b5674dd5e5403a78007edf02663260a2ba099f0e8f1bc447b0ae184b1b', 'f6d8da061170e7583e0439e1ad7b261423cd0f4c70958d93c18b859a9c5aa826'], 'static/project_intro/intro.js': ['b43359170c39ea7127fbcfd9b1a2ac5edcd344044194b67f5b2f892dc0e96127', 'bada7fd0c8e5b8fecd329c8939348860921b9909b5bda67b1b8868078eaa91c8', 'f7dbf73a864e773cfcd6c3d8b9d4b3167d41ddef789dc1459afb5a68f6d9ed4b'], 'templates/project_intro/index.html': ['bddbad27a8b0b6b5b8cf1d15743fb6a47972b7aa8ae21b87f4bc668aa97d37be', 'ea1fb98087e8b323ed1325fabb155ce08a32958f89e1930c3c3ad86944f1975e', '6e37de838eec85243667f14564094d85489c9e37d6b2390ecfa983466ed603ac']}

def prepare(root):
    payload=Path(__file__).resolve().parent/'payload'
    route=root/'web/dashboard_routes.py'; nav=root/'templates/home/home_index_v2_nav.html'
    if not route.is_file() or not nav.is_file(): raise ValueError('대시보드가 등록된 DATA-TIP-OFF 프로젝트 폴더를 지정해 주세요.')
    text=route.read_text(encoding='utf-8'); original=text
    old="return render_template('dashboard/index.html')"; new="return render_template('project_intro/index.html')"
    if old in text:
        if text.count(old)!=1: raise ValueError('대시보드 라우트가 예상과 다릅니다. 원본을 유지하고 중단합니다.')
        text=text.replace(old,new,1)
    elif new not in text: raise ValueError('대시보드 템플릿 경로를 확인할 수 없습니다.')
    additions="\n\n@dashboard_bp.get('/project-intro')\ndef project_intro():\n    return render_template('project_intro/index.html')\n\n\n@dashboard_bp.get('/api/project-intro')\ndef project_intro_api():\n    from web.project_intro_data import load_intro\n    return jsonify(load_intro())\n"
    if "@dashboard_bp.get('/project-intro')" not in text:
        if 'def project_intro' in text or '/api/project-intro' in text: raise ValueError('기존 프로젝트 소개 라우트가 있어 자동 변경하지 않습니다.')
        text=text.rstrip()+additions
    elif 'def project_intro_api():' not in text: raise ValueError('기존 소개 API를 확인해 주세요.')
    html=nav.read_text(encoding='utf-8');old_link='<a href="/dashboard">대시보드</a>';new_link='<a href="/project-intro">프로젝트 소개</a>'
    if old_link in html:
        if html.count(old_link)!=1: raise ValueError('메뉴 링크가 여러 개여서 자동 변경하지 않습니다.')
        html=html.replace(old_link,new_link,1)
    elif new_link not in html: raise ValueError('메인 메뉴의 대시보드 링크 형식이 달라 자동 변경하지 않습니다.')
    changes={route:text.encode(),nav:html.encode()}
    for p in payload.rglob('*'):
        if p.is_file():
            dest=root/p.relative_to(payload)
            if dest.exists() and dest.read_bytes()!=p.read_bytes() and hashlib.sha256(dest.read_bytes()).hexdigest() not in UPGRADE_HASHES.get(str(p.relative_to(payload)), []): raise ValueError(f'같은 이름의 다른 파일이 있습니다: {dest}. 원본을 보존하고 중단합니다.')
            changes[dest]=p.read_bytes()
    return {p:b for p,b in changes.items() if not p.exists() or p.read_bytes()!=b}

def main():
    ap=argparse.ArgumentParser(description='기존 페이지를 보존하는 프로젝트 소개 설치기')
    ap.add_argument('project',help='DATA-TIP-OFF 폴더 경로');ap.add_argument('--apply',action='store_true',help='백업 후 적용 (생략하면 변경 목록만 확인)');a=ap.parse_args();root=Path(a.project).expanduser().resolve()
    try: changes=prepare(root)
    except ValueError as e: print(e);return 1
    if not changes: print('이미 같은 버전이 설치되어 있습니다. 변경 없음.');return 0
    for p in changes: print(('수정: ' if p.exists() else '추가: ')+str(p.relative_to(root)))
    if not a.apply: print('확인만 완료했습니다. 적용하려면 명령 끝에 --apply를 추가하세요.');return 0
    backup=root/'.project-intro-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    manifest={}
    for p,b in changes.items():
        rel=str(p.relative_to(root));exists=p.exists();manifest[rel]={'existed':exists,'installed_sha256':hashlib.sha256(b).hexdigest()}
        if exists:
            target=backup/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    (backup/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for p,b in changes.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    except Exception:
        for rel,m in manifest.items():
            p=root/rel
            if m['existed']:shutil.copy2(backup/rel,p)
            elif p.exists():p.unlink()
        raise
    print('설치 완료. Flask 서버를 재시작하고 /project-intro 에 접속하세요.');print('원본 백업: '+str(backup))
    return 0
if __name__=='__main__':sys.exit(main())
