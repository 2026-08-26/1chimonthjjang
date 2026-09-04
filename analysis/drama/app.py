import os
from flask import Flask, jsonify, render_template, request
from mock_data import load_all_contents

# 1. templates 폴더 위치를 프로젝트 최상단(1chimonthjjang/templates)으로 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "templates"))

app = Flask(__name__, template_folder=TEMPLATE_DIR)


@app.route("/")
def main_dashboard():
    all_items = load_all_contents()

    stats = {
        "total": len(all_items),
        "high": sum(1 for item in all_items if item["signal"] == "HIGH"),
        "medium": sum(1 for item in all_items if item["signal"] == "MEDIUM"),
        "low": sum(1 for item in all_items if item["signal"] == "LOW"),
    }

    top_items = all_items[:5]

    # trend/trend_index.html 로 경로 변경
    return render_template(
        "trend/trend_index.html", items=top_items, stats=stats
    )


@app.route("/content/<category_type>")
def category_page(category_type):
    category_map = {"music": "노래", "drama": "드라마", "webtoon": "웹툰"}
    cat_name = category_map.get(category_type, "콘텐츠")

    all_items = load_all_contents()
    filtered_items = [
        item for item in all_items if item["category"] == category_type
    ]

    # trend/trend_index.html 로 경로 변경
    return render_template(
        "trend/trend_index.html",
        items=filtered_items,
        category_type=category_type,
        category_name=cat_name,
    )


@app.route("/detail/<int:item_id>")
def detail_page(item_id):
    all_items = load_all_contents()
    item = next((i for i in all_items if i["id"] == item_id), None)

    if not item:
        return "콘텐츠를 찾을 수 없습니다.", 404

    # trend/trend_detail.html 로 경로 변경
    return render_template("trend/trend_detail.html", item=item)


@app.route("/api/ai-report/<int:item_id>", methods=["POST"])
def ai_agent_report(item_id):
    all_items = load_all_contents()
    item = next((i for i in all_items if i["id"] == item_id), None)

    if not item:
        return jsonify({"error": "Item not found"}), 404

    report = {
        "title": item["title"],
        "briefing": f"<strong>[{item['title']}]</strong>은(는) 최근 7일간 검색 관심도가 과거 30일 평균 대비 <strong>+{item['increase_rate']}%</strong> 급증했습니다. 이상징후 신호 <strong>{item['signal']}</strong> 등급으로 감지되었습니다.",
        "article_ideas": [
            f"급상승 중인 '{item['title']}', 미디어 관심도 폭발 원인 분석",
            f"팬덤 및 온·오프라인 커뮤니티의 주요 반응 추이",
        ],
        "questions": [
            "최근 7일 사이 특별한 이슈, SNS 밈(Meme), 숏폼 챌린지가 있었는가?",
            "주요 타깃 연령층에서의 검색 비율 변화 특징은 어떠한가?",
        ],
        "verification_data": [
            "네이버 데이터랩 연령대/성별 검색 데이터",
            "YouTube 알고리즘 노출량 및 댓글 감성 분석 데이터",
        ],
    }
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True, port=5000)