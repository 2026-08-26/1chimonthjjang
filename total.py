import pandas as pd
from flask import Flask, render_template, jsonify
from baseball_ai_agent import BaseballAIAgent


# ==================================================
# Flask 서버 생성
# ==================================================

app = Flask(__name__)


# ==================================================
# 야구 AI Agent 생성
# ==================================================

baseball_ai_agent = BaseballAIAgent()


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
    return render_template("index.html")


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
    app.run(debug=True)

# ==================================================
# 가장 강한 야구 이상신호 AI 리포트
# ==================================================

@app.route("/api/baseball-ai-report/top", methods=["POST"])
def baseball_ai_report_top():

    # 기온 + 습도 + 강수 데이터 전부 가져오기
    df = load_baseball_signals()

    # 이상신호 절대값 계산
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