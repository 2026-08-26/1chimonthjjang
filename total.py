import pandas as pd

from flask import (
    Flask,
    render_template,
    jsonify,
    redirect,
    url_for
)

# ==================================================
# 야구
# ==================================================

from baseball_ai_agent import BaseballAIAgent


# ==================================================
# K-콘텐츠
# ==================================================

from analysis.drama.ai_agent import TrendAIAgent
from analysis.drama.mock_data import load_all_contents


# ==================================================
# 다른 팀 기능
# ==================================================

from web.economy_routes import economy_bp
from web.home_v2_nav_routes import home_v2_nav_bp
from web.social_routes import social_bp


# ==================================================
# Flask 서버 생성
# ==================================================

app = Flask(__name__)


# ==================================================
# Blueprint 등록
# ==================================================

app.register_blueprint(economy_bp)

app.register_blueprint(social_bp)

app.register_blueprint(home_v2_nav_bp)


# ==================================================
# AI Agent 생성
# ==================================================

baseball_ai_agent = BaseballAIAgent()

trend_ai_agent = TrendAIAgent()


# ==================================================
# K-콘텐츠 통계 함수
# ==================================================

def make_trend_stats(items):

    return {

        "total": len(items),

        "high": sum(
            1
            for item in items
            if item.get("signal") == "HIGH"
        ),

        "medium": sum(
            1
            for item in items
            if item.get("signal") == "MEDIUM"
        ),

        "low": sum(
            1
            for item in items
            if item.get("signal") == "LOW"
        ),
    }


# ==================================================
# K-콘텐츠 취재 우선순위 정렬
# ==================================================

def sort_trend_items(items):

    # HIGH > MEDIUM > LOW
    signal_priority = {

        "HIGH": 3,

        "MEDIUM": 2,

        "LOW": 1,
    }


    return sorted(

        items,

        key=lambda item: (

            signal_priority.get(
                item.get("signal"),
                0
            ),

            item.get(
                "trend_score",
                0
            ),

            item.get(
                "increase_rate",
                0
            ),

            item.get(
                "z_score",
                0
            ),
        ),

        reverse=True
    )


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


    # ==================================================
    # 날씨 종류 구분용 컬럼
    # ==================================================

    temp["weather_type"] = "기온"

    temp["weather_group"] = (
        temp["temp_group"]
    )


    humidity["weather_type"] = "습도"

    humidity["weather_group"] = (
        humidity["humidity_group"]
    )


    rain["weather_type"] = "강수"

    rain["weather_group"] = (
        rain["rain_group"]
    )


    # ==================================================
    # 데이터 합치기
    # ==================================================

    result = pd.concat(

        [
            temp,
            humidity,
            rain
        ],

        ignore_index=True
    )


    return result


# ==================================================
# 메인 페이지
# ==================================================

@app.route("/")
def index():

    return redirect(

        url_for(
            "home_v2_nav.home_v2_nav"
        )
    )


# ==================================================
# 야구 페이지
# ==================================================

@app.route("/baseball")
def baseball():

    # ==================================================
    # CSV
    # ==================================================

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


    # ==================================================
    # 이상신호 강도
    # ==================================================

    temp["signal_strength"] = (
        temp["signal_score"].abs()
    )

    humidity["signal_strength"] = (
        humidity["signal_score"].abs()
    )

    rain["signal_strength"] = (
        rain["signal_score"].abs()
    )


    # ==================================================
    # 기온 TOP 10
    # ==================================================

    temp_top = (

        temp

        .sort_values(
            "signal_strength",
            ascending=False
        )

        .head(10)

        .to_dict(
            "records"
        )
    )


    # ==================================================
    # 습도 TOP 10
    # ==================================================

    humidity_top = (

        humidity

        .sort_values(
            "signal_strength",
            ascending=False
        )

        .head(10)

        .to_dict(
            "records"
        )
    )


    # ==================================================
    # 강수 TOP 10
    # ==================================================

    rain_top = (

        rain[
            rain["rain_group"] == "비"
        ]

        .sort_values(
            "signal_strength",
            ascending=False
        )

        .head(10)

        .to_dict(
            "records"
        )
    )


    return render_template(

        "baseball.html",

        temp_top=temp_top,

        humidity_top=humidity_top,

        rain_top=rain_top
    )


# ==================================================
# K-CONTENTS 전체 트렌드
#
# 노래 + 드라마 + 웹툰 전체에서
# 취재 가치 높은 TOP 10
# ==================================================

@app.route("/trend")
def trend_dashboard():

    # ==================================================
    # CSV 전체 데이터 분석
    # ==================================================

    all_items = (
        load_all_contents()
    )


    # ==================================================
    # 확실하게 취재 우선순위 정렬
    # ==================================================

    sorted_items = (
        sort_trend_items(
            all_items
        )
    )


    # ==================================================
    # 상단 통계는 전체 CSV 데이터 기준
    # ==================================================

    stats = (
        make_trend_stats(
            sorted_items
        )
    )


    # ==================================================
    # 화면에는 TOP 10만
    # ==================================================

    top_items = (
        sorted_items[:10]
    )


    return render_template(

        "trend/trend_index.html",

        items=top_items,

        stats=stats,

        category_type=None,

        category_name=None
    )


# ==================================================
# K-CONTENTS 카테고리
#
# /content/music
# /content/drama
# /content/webtoon
# ==================================================

@app.route(
    "/content/<category_type>"
)
def category_page(
    category_type
):

    # ==================================================
    # 카테고리 이름
    # ==================================================

    category_map = {

        "music": "노래",

        "drama": "드라마",

        "webtoon": "웹툰"
    }


    # ==================================================
    # 존재하지 않는 카테고리 방지
    # ==================================================

    if category_type not in category_map:

        return (
            "존재하지 않는 카테고리입니다.",
            404
        )


    cat_name = (
        category_map[
            category_type
        ]
    )


    # ==================================================
    # CSV 전체 분석
    # ==================================================

    all_items = (
        load_all_contents()
    )


    # ==================================================
    # 선택한 카테고리만 추출
    #
    # webtoon 클릭:
    # naver.csv 데이터만
    #
    # drama 클릭:
    # kdrama.csv 데이터만
    #
    # music 클릭:
    # kpopidolsv3.csv 데이터만
    # ==================================================

    filtered_items = [

        item

        for item in all_items

        if item.get(
            "category"
        ) == category_type
    ]


    # ==================================================
    # 취재 우선순위 재정렬
    # ==================================================

    sorted_items = (
        sort_trend_items(
            filtered_items
        )
    )


    # ==================================================
    # 상단 통계
    #
    # IMPORTANT:
    # TOP 10 기준이 아니라
    # CSV 전체 후보 기준 통계
    # ==================================================

    stats = (
        make_trend_stats(
            sorted_items
        )
    )


    # ==================================================
    # ★ 핵심 ★
    #
    # 취재 우선순위 TOP 10만 화면에 전달
    # ==================================================

    top_items = (
        sorted_items[:10]
    )


    return render_template(

        "trend/trend_index.html",

        # 여기 중요
        items=top_items,

        stats=stats,

        category_type=category_type,

        category_name=cat_name
    )


# ==================================================
# K-CONTENTS 상세 페이지
# ==================================================

@app.route(
    "/detail/<int:item_id>"
)
def detail_page(
    item_id
):

    # ==================================================
    # 전체 분석 데이터
    # ==================================================

    all_items = (
        load_all_contents()
    )


    # ==================================================
    # ID로 콘텐츠 검색
    # ==================================================

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


    # ==================================================
    # 없는 데이터
    # ==================================================

    if item is None:

        return (
            "콘텐츠를 찾을 수 없습니다.",
            404
        )


    # ==================================================
    # 상세 페이지
    # ==================================================

    return render_template(

        "trend/trend_detail.html",

        item=item
    )


# ==================================================
# K-CONTENTS AI REPORT
# ==================================================

@app.route(
    "/api/ai-report/<int:item_id>",
    methods=["POST"]
)
def ai_agent_report(
    item_id
):

    # ==================================================
    # 전체 콘텐츠
    # ==================================================

    all_items = (
        load_all_contents()
    )


    # ==================================================
    # ID 검색
    # ==================================================

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


    # ==================================================
    # 데이터 없음
    # ==================================================

    if item is None:

        return jsonify(

            {
                "error":
                    "Item not found"
            }

        ), 404


    # ==================================================
    # AI 취재 분석
    # ==================================================

    report = (
        trend_ai_agent
        .generate_report(
            item
        )
    )


    return jsonify(
        report
    )


# ==================================================
# 야구 AI REPORT
# ==================================================

@app.route(
    "/api/baseball-ai-report/<int:item_id>",
    methods=["POST"]
)
def baseball_ai_report(
    item_id
):

    # ==================================================
    # 전체 이상신호
    # ==================================================

    df = (
        load_baseball_signals()
    )


    # ==================================================
    # 잘못된 번호 방지
    # ==================================================

    if (
        item_id < 0
        or
        item_id >= len(df)
    ):

        return jsonify(

            {
                "error":
                    "데이터를 찾을 수 없습니다."
            }

        ), 404


    # ==================================================
    # 해당 데이터 한 행
    # ==================================================

    item = (
        df
        .iloc[item_id]
        .to_dict()
    )


    # ==================================================
    # AI Agent
    # ==================================================

    report = (
        baseball_ai_agent
        .generate_report(
            item
        )
    )


    return jsonify(
        report
    )


# ==================================================
# 야구 TOP 이상신호 AI REPORT
# ==================================================

@app.route(
    "/api/baseball-ai-report/top",
    methods=["POST"]
)
def baseball_ai_report_top():

    try:

        # ==================================================
        # 전체 이상신호
        # ==================================================

        df = (
            load_baseball_signals()
        )


        # ==================================================
        # 이상신호 강도
        # ==================================================

        df["signal_strength"] = (
            df["signal_score"].abs()
        )


        # ==================================================
        # 가장 강한 이상신호
        # ==================================================

        top_item = (

            df

            .sort_values(
                "signal_strength",
                ascending=False
            )

            .iloc[0]

            .to_dict()
        )


        # ==================================================
        # AI 분석
        # ==================================================

        report = (
            baseball_ai_agent
            .generate_report(
                top_item
            )
        )


        return jsonify(
            report
        )


    except Exception as e:

        print(
            "AI REPORT ERROR:",
            e
        )


        return jsonify(

            {
                "error":
                    str(e)
            }

        ), 500


# ==================================================
# 서버 실행
# ==================================================

if __name__ == "__main__":

    print()

    print(
        "=========================================="
    )

    print(
        "DATA TIP-OFF 서버 실행"
    )

    print(
        "메인 / 사회 / 경제 / K콘텐츠 / 야구"
    )

    print(
        "K콘텐츠: CSV 전체 → 이상감지 → TOP 10"
    )

    print(
        "http://127.0.0.1:5001"
    )

    print(
        "=========================================="
    )

    print()


    app.run(
        debug=True,
        port=5001
    )