import os
import sys

from flask import (
    Flask,
    jsonify,
    render_template
)


# ==========================================================
# 프로젝트 경로
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        ".."
    )
)


if PROJECT_ROOT not in sys.path:

    sys.path.insert(
        0,
        PROJECT_ROOT
    )


# ==========================================================
# 프로젝트 모듈
# ==========================================================

from analysis.drama.ai_agent import TrendAIAgent
from analysis.drama.mock_data import load_all_contents


# ==========================================================
# Flask
# ==========================================================

TEMPLATE_DIR = os.path.join(
    PROJECT_ROOT,
    "templates"
)


STATIC_DIR = os.path.join(
    PROJECT_ROOT,
    "static"
)


app = Flask(

    __name__,

    template_folder=TEMPLATE_DIR,

    static_folder=STATIC_DIR
)


ai_agent = TrendAIAgent()


# ==========================================================
# 통계
# ==========================================================

def _make_stats(items):

    return {

        "total": len(items),

        "high": sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "HIGH"
        ),

        "medium": sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "MEDIUM"
        ),

        "low": sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "LOW"
        ),
    }


# ==========================================================
# 메인
#
# 전체 K콘텐츠 중 취재 우선순위 TOP 10
# ==========================================================

@app.route("/")
def home():

    all_items = load_all_contents()


    # CSV 전체 분석 통계
    stats = _make_stats(
        all_items
    )


    # 기자에게 보여주는 TOP 10
    top_items = all_items[:10]


    return render_template(

        "trend/trend_index.html",

        items=top_items,

        stats=stats,

        category_type=None,

        category_name=None
    )


# ==========================================================
# /trend
# ==========================================================

@app.route("/trend")
def trend_dashboard():

    return home()


# ==========================================================
# 카테고리
#
# music / drama / webtoon
# 각각 CSV 전체 분석 후 TOP 10
# ==========================================================

@app.route(
    "/content/<category_type>"
)
def category_page(
    category_type
):

    category_map = {

        "music": "노래",

        "drama": "드라마",

        "webtoon": "웹툰",
    }


    # 잘못된 카테고리 주소 방지
    if category_type not in category_map:

        return (
            "존재하지 않는 카테고리입니다.",
            404
        )


    all_items = load_all_contents()


    # ==========================================
    # 해당 카테고리 전체 데이터
    # ==========================================

    category_items = [

        item

        for item in all_items

        if item.get(
            "category"
        ) == category_type
    ]


    # ==========================================
    # 통계는 CSV 전체 기준
    # ==========================================

    stats = _make_stats(
        category_items
    )


    # ==========================================
    # 화면에는 취재 우선순위 TOP 10
    # ==========================================

    top_items = (
        category_items[:10]
    )


    return render_template(

        "trend/trend_index.html",

        items=top_items,

        stats=stats,

        category_type=category_type,

        category_name=category_map[
            category_type
        ]
    )


# ==========================================================
# 상세 페이지
# ==========================================================

@app.route(
    "/detail/<int:item_id>"
)
def detail_page(
    item_id
):

    all_items = load_all_contents()


    item = next(

        (

            item

            for item in all_items

            if item.get(
                "id"
            ) == item_id
        ),

        None
    )


    if item is None:

        return (
            "콘텐츠를 찾을 수 없습니다.",
            404
        )


    return render_template(

        "trend/trend_detail.html",

        item=item
    )


# ==========================================================
# AI 취재 리포트 API
# ==========================================================

@app.route(
    "/api/ai-report/<int:item_id>",
    methods=["POST"]
)
def ai_agent_report(
    item_id
):

    all_items = load_all_contents()


    item = next(

        (

            item

            for item in all_items

            if item.get(
                "id"
            ) == item_id
        ),

        None
    )


    if item is None:

        return jsonify(

            {
                "error":
                    "Item not found"
            }

        ), 404


    report = (
        ai_agent.generate_report(
            item
        )
    )


    return jsonify(
        report
    )


# ==========================================================
# 실행
# ==========================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "DATA TIP-OFF K-콘텐츠 이상감지 시스템"
    )

    print(
        "CSV 전체 분석 → 이상감지 → 취재 TOP 10"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print(
        "=========================================="
    )
    print()


    app.run(

        debug=True,

        port=5000
    )