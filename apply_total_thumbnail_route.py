from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path.cwd()
TARGET = ROOT / "total.py"

if not TARGET.exists():
    raise SystemExit(
        "\n[ERROR] total.py를 찾을 수 없습니다.\n"
        "프로젝트 최상위 폴더에서 실행해주세요."
    )

text = TARGET.read_text(
    encoding="utf-8"
)

for marker in (
    "<<<<<<<",
    "=======",
    ">>>>>>>",
):
    if marker in text:
        raise SystemExit(
            "\n[ERROR] total.py에 Git 충돌 마커가 남아 있습니다.\n"
            f"발견: {marker}"
        )

import_line = (
    "from web.kcontent_media_routes "
    "import kcontent_media_bp"
)

register_line = (
    "app.register_blueprint("
    "kcontent_media_bp)"
)

changed = False

if import_line not in text:
    anchor = (
        "from web.home_v2_nav_routes "
        "import home_v2_nav_bp"
    )

    if anchor not in text:
        raise SystemExit(
            "\n[ERROR] Blueprint import 위치를 찾지 못했습니다."
        )

    text = text.replace(
        anchor,
        anchor
        + "\n"
        + import_line,
        1,
    )

    changed = True

if register_line not in text:
    anchor = (
        "app.register_blueprint("
        "home_v2_nav_bp)"
    )

    if anchor not in text:
        raise SystemExit(
            "\n[ERROR] Blueprint 등록 위치를 찾지 못했습니다."
        )

    text = text.replace(
        anchor,
        anchor
        + "\n"
        + register_line,
        1,
    )

    changed = True

try:
    compile(
        text,
        str(TARGET),
        "exec",
    )
except SyntaxError as exc:
    raise SystemExit(
        "\n[ERROR] 수정 후 total.py 문법 검사 실패\n"
        + str(exc)
    )

if not changed:
    print(
        "이미 K콘텐츠 썸네일 Blueprint가 등록되어 있습니다."
    )
    raise SystemExit(0)

stamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

backup = TARGET.with_name(
    f"total_BEFORE_KCONTENT_THUMB_{stamp}.py"
)

shutil.copy2(
    TARGET,
    backup,
)

TARGET.write_text(
    text,
    encoding="utf-8",
)

print()
print("========================================")
print("total.py Blueprint 등록 완료")
print("========================================")
print("수정:", TARGET)
print("백업:", backup)
print()
print("추가된 Blueprint:")
print("kcontent_media_bp")
print("========================================")
