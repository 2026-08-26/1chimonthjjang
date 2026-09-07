"""Run: python apply_fix.py /path/to/DATA-TIP-OFF. Preserves existing code."""
from pathlib import Path
from datetime import datetime
import shutil
import sys
import re
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
if not (root/'web/kcontent_media_routes.py').is_file():
    raise SystemExit('web/kcontent_media_routes.py가 있는 프로젝트 경로를 지정해주세요.')
include="{% include 'includes/desk_motion.html' %}"
changes={}
for filename in ('total.py','total_team.py'):
    p=root/filename
    if not p.exists():continue
    text=p.read_text()
    if not re.search(r'app\.register_blueprint\(\s*kcontent_media_bp\s*\)',text):
        anchor=re.search(r'^app\s*=\s*Flask\(__name__\).*$',text,re.M)
        if not anchor:raise SystemExit(f'{filename}: Flask app 생성 위치를 찾지 못했습니다. 자동 변경을 중단합니다.')
        text=text[:anchor.end()]+"\n\n# K콘텐츠 썸네일 엔드포인트 등록\nfrom web.kcontent_media_routes import kcontent_media_bp\napp.register_blueprint(kcontent_media_bp)\n"+text[anchor.end():]
        changes[p]=text
for filename in ('templates/stock/base.html','templates/baseball.html'):
    p=root/filename;text=p.read_text()
    if include not in text:
        if '</body>' not in text:raise SystemExit(f'{filename}: body 종료 태그를 찾지 못했습니다.')
        changes[p]=text.replace('</body>',include+'\n</body>',1)
p=root/'templates/includes/desk_motion.html'
text=Path(__file__).with_name('desk_motion.html').read_text()
if not p.exists() or p.read_text()!=text:changes[p]=text
if not changes:
    print('이미 적용되어 있습니다.');raise SystemExit(0)
backup=root/'backups'/('kcontent-motion-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
for path in changes:
    if path.exists():
        dest=backup/path.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
for path,text in changes.items():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
print(f'{len(changes)}개 파일 적용 완료. 백업: {backup}. 서버를 재시작해주세요.')
