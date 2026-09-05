import pandas as pd
from flask import Flask, render_template, jsonify, redirect, url_for
# 야구
from baseball_ai_agent import BaseballAIAgent

# K-콘텐츠
from analysis.drama.ai_agent import TrendAIAgent
from analysis.drama.mock_data import load_all_contents
from web.economy_routes import economy_bp
from web.home_v2_nav_routes import home_v2_nav_bp
from web.social_routes import social_bp
# ==================================================
# Flask 서버 생성
# ==================================================

app = Flask(__name__)


# ==================================================
# 야구 AI Agent 생성
# ==================================================
app.register_blueprint(economy_bp)
baseball_ai_agent = BaseballAIAgent()
# 사회 페이지와 확정한 메인 화면
app.register_blueprint(social_bp)
app.register_blueprint(home_v2_nav_bp)
# K-Contents AI Agent
trend_ai_agent = TrendAIAgent()
# ==================================================
# 야구 이상신호 데이터 불러오기
# ==================================================

def load_baseball_signals():

    temp = pd.read_csv(
        "data/processed/temp_signal.csv",
        encoding="utf-8-sig"
    )

    humidity = pd.read_csv(
        "data/processed/humidity_signal.csv",
        encoding="utf-8-sig"
    )

    rain = pd.read_csv(
        "data/processed/rain_signal.csv",
        encoding="utf-8-sig"
    )

    # 날씨 종류 구분용 컬럼 추가
    temp["weather_type"] = "기온"
    temp["weather_group"] = temp["temp_group"]

    humidity["weather_type"] = "습도"
    humidity["weather_group"] = humidity["humidity_group"]

    rain["weather_type"] = "강수"
    rain["weather_group"] = rain["rain_group"]

    # 3개 데이터 합치기
    result = pd.concat(
        [temp, humidity, rain],
        ignore_index=True
    )

    return result


# ==================================================
# 메인 페이지
# ==================================================

@app.route("/")
def index():
    return redirect(url_for("home_v2_nav.home_v2_nav"))


# ==================================================
# 야구 페이지
# ==================================================

@app.route("/baseball")
def baseball():

    # 분석 결과 CSV 불러오기
    temp = pd.read_csv(
        "data/processed/temp_signal.csv",
        encoding="utf-8-sig"
    )

    humidity = pd.read_csv(
        "data/processed/humidity_signal.csv",
        encoding="utf-8-sig"
    )

    rain = pd.read_csv(
        "data/processed/rain_signal.csv",
        encoding="utf-8-sig"
    )

    # 이상신호 강도 계산
    temp["signal_strength"] = temp["signal_score"].abs()
    humidity["signal_strength"] = humidity["signal_score"].abs()
    rain["signal_strength"] = rain["signal_score"].abs()

    # 기온 이상신호 TOP 10
    temp_top = (
        temp
        .sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    # 습도 이상신호 TOP 10
    humidity_top = (
        humidity
        .sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    # 비 오는 날 이상신호 TOP 10
    rain_top = (
        rain[rain["rain_group"] == "비"]
        .sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    return render_template(
        "baseball.html",
        temp_top=temp_top,
        humidity_top=humidity_top,
        rain_top=rain_top
    )


# ==================================================
# 야구 AI Agent 리포트 API
# ==================================================
# ==================================================
# K-CONTENTS 트렌드 대시보드
# ==================================================

@app.route("/trend")
def trend_dashboard():

    all_items = load_all_contents()

    stats = {
        "total": len(all_items),
        "high": sum(
            1 for item in all_items
            if item["signal"] == "HIGH"
        ),
        "medium": sum(
            1 for item in all_items
            if item["signal"] == "MEDIUM"
        ),
        "low": sum(
            1 for item in all_items
            if item["signal"] == "LOW"
        ),
    }

    return render_template(
        "trend/trend_index.html",
        items=all_items,
        stats=stats
    )
# ==================================================
# K-CONTENTS 카테고리
# ==================================================

@app.route("/content/<category_type>")
def category_page(category_type):

    category_map = {
        "music": "노래",
        "drama": "드라마",
        "webtoon": "웹툰"
    }

    cat_name = category_map.get(
        category_type,
        "콘텐츠"
    )

    all_items = load_all_contents()

    filtered_items = [
        item
        for item in all_items
        if item["category"] == category_type
    ]

    stats = {
        "total": len(filtered_items),
        "high": sum(
            1 for item in filtered_items
            if item["signal"] == "HIGH"
        ),
        "medium": sum(
            1 for item in filtered_items
            if item["signal"] == "MEDIUM"
        ),
        "low": sum(
            1 for item in filtered_items
            if item["signal"] == "LOW"
        ),
    }

    return render_template(
        "trend/trend_index.html",
        items=filtered_items,
        stats=stats,
        category_type=category_type,
        category_name=cat_name
    )


# ==================================================
# K-CONTENTS 상세 페이지
# ==================================================

@app.route("/detail/<int:item_id>")
def detail_page(item_id):

    all_items = load_all_contents()

    item = next(
        (
            item
            for item in all_items
            if item["id"] == item_id
        ),
        None
    )

    if item is None:
        return "콘텐츠를 찾을 수 없습니다.", 404

    return render_template(
        "trend/trend_detail.html",
        item=item
    )
# ==================================================
# K-CONTENTS AI REPORT
# ==================================================

@app.route("/api/ai-report/<int:item_id>", methods=["POST"])
def ai_agent_report(item_id):

    all_items = load_all_contents()

    item = next(
        (
            item
            for item in all_items
            if item["id"] == item_id
        ),
        None
    )

    if item is None:
        return jsonify({
            "error": "Item not found"
        }), 404

    report = trend_ai_agent.generate_report(item)

    return jsonify(report)
@app.route(
    "/api/baseball-ai-report/<int:item_id>",
    methods=["POST"]
)

def baseball_ai_report(item_id):

    # 전체 이상신호 데이터 가져오기
    df = load_baseball_signals()

    # 잘못된 번호 방지
    if item_id < 0 or item_id >= len(df):
        return jsonify({
            "error": "데이터를 찾을 수 없습니다."
        }), 404

    # 해당 선수/날씨 데이터 한 행 가져오기
    item = df.iloc[item_id].to_dict()

    # AI Agent에게 전달
    report = baseball_ai_agent.generate_report(item)

    # 결과를 HTML/JS 쪽으로 반환
    return jsonify(report)

@app.route("/api/baseball-ai-report/top", methods=["POST"])
def baseball_ai_report_top():

    try:
        # 전체 이상신호 데이터
        df = load_baseball_signals()

        # 신호 강도 계산
        df["signal_strength"] = df["signal_score"].abs()

        # 가장 강한 이상신호 1개 선택
        top_item = (
            df
            .sort_values("signal_strength", ascending=False)
            .iloc[0]
            .to_dict()
        )

        # AI Agent 분석
        report = baseball_ai_agent.generate_report(top_item)

        return jsonify(report)

    except Exception as e:

        print("AI REPORT ERROR:", e)

        return jsonify({
            "error": str(e)
        }), 500
# ==================================================
# 서버 실행
# ==================================================

if __name__ == "__main__":
    app.run(debug=True, port=5001)