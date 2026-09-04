import os
from ai_agent import TrendAIAgent
from flask import Flask, jsonify, render_template, request
from mock_data import load_all_contents

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "templates"))
STATIC_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "static"))

app = Flask(
    __name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR
)
ai_agent = TrendAIAgent()


# 메인 랜딩 페이지 (팀원 index.html 연동)
@app.route("/")
def home():
    all_items = load_all_contents()
    stats = {
        "total": len(all_items),
        "high": sum(1 for item in all_items if item["signal"] == "HIGH"),
        "medium": sum(1 for item in all_items if item["signal"] == "MEDIUM"),
        "low": sum(1 for item in all_items if item["signal"] == "LOW"),
    }
    top_items = all_items[:3]
    return render_template("index.html", top_items=top_items, stats=stats)


# 트렌드 대시보드 리스트 페이지
@app.route("/trend")
def trend_dashboard():
    all_items = load_all_contents()
    stats = {
        "total": len(all_items),
        "high": sum(1 for item in all_items if item["signal"] == "HIGH"),
        "medium": sum(1 for item in all_items if item["signal"] == "MEDIUM"),
        "low": sum(1 for item in all_items if item["signal"] == "LOW"),
    }
    return render_template(
        "trend/trend_index.html", items=all_items, stats=stats
    )


# 카테고리별 필터링 페이지
@app.route("/content/<category_type>")
def category_page(category_type):
    category_map = {"music": "노래", "drama": "드라마", "webtoon": "웹툰"}
    cat_name = category_map.get(category_type, "콘텐츠")

    all_items = load_all_contents()
    filtered_items = [
        item for item in all_items if item["category"] == category_type
    ]
    stats = {
        "total": len(filtered_items),
        "high": sum(1 for item in filtered_items if item["signal"] == "HIGH"),
        "medium": sum(
            1 for item in filtered_items if item["signal"] == "MEDIUM"
        ),
        "low": sum(1 for item in filtered_items if item["signal"] == "LOW"),
    }
    return render_template(
        "trend/trend_index.html",
        items=filtered_items,
        stats=stats,
        category_type=category_type,
        category_name=cat_name,
    )


# 상세 페이지
@app.route("/detail/<int:item_id>")
def detail_page(item_id):
    all_items = load_all_contents()
    item = next((i for i in all_items if i["id"] == item_id), None)
    if not item:
        return "콘텐츠를 찾을 수 없습니다.", 404
    return render_template("trend/trend_detail.html", item=item)


# AI 기자 리포트 API
@app.route("/api/ai-report/<int:item_id>", methods=["POST"])
def ai_agent_report(item_id):
    all_items = load_all_contents()
    item = next((i for i in all_items if i["id"] == item_id), None)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    report = ai_agent.generate_report(item)
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True, port=5000)