import os

import pandas as pd
from flask import Blueprint, jsonify, render_template


# =========================================================
# Blueprint
# =========================================================

economy_bp = Blueprint("economy", __name__)


# =========================================================
# 경로 설정
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

RATE_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "economy_rate_reverse_top10.csv"
)

CROSS_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "economy_price_volume_cross_top10.csv"
)


# =========================================================
# CSV 불러오기
# =========================================================

def load_rate_signal():
    df = pd.read_csv(RATE_PATH)

    df["Date"] = pd.to_datetime(df["Date"])

    return df


def load_cross_signal():
    df = pd.read_csv(CROSS_PATH)

    df["Date"] = pd.to_datetime(df["Date"])

    return df


# =========================================================
# 차트 너비 계산
# =========================================================

def make_chart_row(label, prev_value, current_value, unit=""):

    prev_value = float(prev_value)
    current_value = float(current_value)

    max_value = max(
        abs(prev_value),
        abs(current_value),
        1
    )

    prev_width = round(
        abs(prev_value) / max_value * 100,
        1
    )

    current_width = round(
        abs(current_value) / max_value * 100,
        1
    )

    return {
        "label": label,
        "prev_value": round(prev_value, 1),
        "current_value": round(current_value, 1),
        "prev_width": prev_width,
        "current_width": current_width,
        "unit": unit
    }


# =========================================================
# 상세 데이터 생성
# =========================================================

def build_signal_data(signal_type):

    # -----------------------------------------------------
    # 기준금리 ↑ + 가격 ↑
    # -----------------------------------------------------

    if signal_type == "rate":

        df = load_rate_signal()

        if df.empty:
            return None, None, None

        row = df.iloc[0]

        item = {
            "signal_type": "rate",

            "title": "기준금리 ↑ + 가격 ↑",

            "region": row["Region"],

            "date": row["Date"].strftime(
                "%Y년 %m월"
            ),

            "score": round(
                float(row["Signal_score"]),
                2
            ),

            "price_prev": round(
                float(row["Price_prev_year"]),
                1
            ),

            "price_now": round(
                float(row["Median_price_per_m2"]),
                1
            ),

            "price_change": round(
                float(row["Price_yoy_pct"]),
                1
            ),

            "rate_prev": round(
                float(row["Base_rate_prev_year"]),
                1
            ),

            "rate_now": round(
                float(row["Base_rate"]),
                1
            ),

            "rate_change": round(
                float(row["Base_rate_change"]),
                1
            )
        }

        chart_rows = [
            make_chart_row(
                "아파트 ㎡당 중앙가격",
                item["price_prev"],
                item["price_now"],
                "만원/㎡"
            ),

            make_chart_row(
                "한국은행 기준금리",
                item["rate_prev"],
                item["rate_now"],
                "%"
            )
        ]

        table_rows = []

        for rank, (_, r) in enumerate(
            df.head(10).iterrows(),
            start=1
        ):

            table_rows.append({
                "rank": rank,

                "date": r["Date"].strftime(
                    "%Y.%m"
                ),

                "region": r["Region"],

                "price_change": round(
                    float(r["Price_yoy_pct"]),
                    1
                ),

                "second_change": round(
                    float(r["Base_rate_change"]),
                    1
                ),

                "score": round(
                    float(r["Signal_score"]),
                    2
                )
            })

        return item, chart_rows, table_rows


    # -----------------------------------------------------
    # 가격 ↑ + 거래량 ↓
    # -----------------------------------------------------

    elif signal_type == "cross":

        df = load_cross_signal()

        if df.empty:
            return None, None, None

        row = df.iloc[0]

        item = {
            "signal_type": "cross",

            "title": "가격 ↑ + 거래량 ↓",

            "region": row["Region"],

            "date": row["Date"].strftime(
                "%Y년 %m월"
            ),

            "score": round(
                float(row["Signal_score"]),
                2
            ),

            "price_prev": round(
                float(row["Price_prev_year"]),
                1
            ),

            "price_now": round(
                float(row["Median_price_per_m2"]),
                1
            ),

            "price_change": round(
                float(row["Price_yoy_pct"]),
                1
            ),

            "transaction_prev": int(
                row["Transaction_prev_year"]
            ),

            "transaction_now": int(
                row["Transaction_count"]
            ),

            "transaction_change": round(
                float(row["Transaction_yoy_pct"]),
                1
            )
        }

        chart_rows = [
            make_chart_row(
                "아파트 ㎡당 중앙가격",
                item["price_prev"],
                item["price_now"],
                "만원/㎡"
            ),

            make_chart_row(
                "아파트 거래량",
                item["transaction_prev"],
                item["transaction_now"],
                "건"
            )
        ]

        table_rows = []

        for rank, (_, r) in enumerate(
            df.head(10).iterrows(),
            start=1
        ):

            table_rows.append({
                "rank": rank,

                "date": r["Date"].strftime(
                    "%Y.%m"
                ),

                "region": r["Region"],

                "price_change": round(
                    float(r["Price_yoy_pct"]),
                    1
                ),

                "second_change": round(
                    float(r["Transaction_yoy_pct"]),
                    1
                ),

                "score": round(
                    float(r["Signal_score"]),
                    2
                )
            })

        return item, chart_rows, table_rows


    return None, None, None


# =========================================================
# 경제 메인 페이지
# =========================================================

@economy_bp.route("/economy")
def economy_index():

    rate_df = load_rate_signal()
    cross_df = load_cross_signal()

    items = []


    # -----------------------------------------------------
    # 기준금리 ↑ + 가격 ↑ TOP1
    # -----------------------------------------------------

    if not rate_df.empty:

        row = rate_df.iloc[0]

        items.append({
            "signal_type": "rate",

            "title": "기준금리 ↑ + 가격 ↑",

            "region": row["Region"],

            "date": row["Date"].strftime(
                "%Y년 %m월"
            ),

            "description": (
                f"기준금리 +{float(row['Base_rate_change']):.1f}%p, "
                f"아파트 ㎡당 중앙가격 "
                f"+{float(row['Price_yoy_pct']):.1f}%"
            ),

            "score": round(
                float(row["Signal_score"]),
                2
            )
        })


    # -----------------------------------------------------
    # 가격 ↑ + 거래량 ↓ TOP1
    # -----------------------------------------------------

    if not cross_df.empty:

        row = cross_df.iloc[0]

        items.append({
            "signal_type": "cross",

            "title": "가격 ↑ + 거래량 ↓",

            "region": row["Region"],

            "date": row["Date"].strftime(
                "%Y년 %m월"
            ),

            "description": (
                f"아파트 ㎡당 중앙가격 "
                f"+{float(row['Price_yoy_pct']):.1f}%, "
                f"거래량 {float(row['Transaction_yoy_pct']):.1f}%"
            ),

            "score": round(
                float(row["Signal_score"]),
                2
            )
        })


    return render_template(
        "economy/economy_index.html",
        items=items
    )


# =========================================================
# 경제 상세 페이지
# =========================================================

@economy_bp.route(
    "/economy/detail/<signal_type>"
)
def economy_detail(signal_type):

    item, chart_rows, table_rows = (
        build_signal_data(signal_type)
    )

    if item is None:

        return (
            "경제 시그널을 찾을 수 없습니다.",
            404
        )

    return render_template(
        "economy/economy_detail.html",
        item=item,
        chart_rows=chart_rows,
        table_rows=table_rows
    )


# =========================================================
# AI Agent 리포트 API
# =========================================================

@economy_bp.route(
    "/api/economy-report/<signal_type>",
    methods=["POST"]
)
def economy_report(signal_type):

    item, _, _ = build_signal_data(
        signal_type
    )

    if item is None:

        return jsonify({
            "error": "Signal not found"
        }), 404


    # -----------------------------------------------------
    # 기준금리 ↑ + 가격 ↑
    # -----------------------------------------------------

    if signal_type == "rate":

        briefing = (
            f"<strong>{item['region']}</strong>의 "
            f"<strong>{item['date']}</strong> 데이터에서 "
            f"기준금리가 전년보다 "
            f"<strong>{item['rate_change']}%p 상승</strong>한 가운데, "
            f"아파트 ㎡당 중앙가격도 "
            f"<strong>{item['price_change']}% 상승</strong>한 "
            f"패턴이 탐지됐습니다. "
            f"두 지표의 동반 상승이 원인과 결과를 뜻하는 것은 아니며, "
            f"해당 지역의 공급·수요·거래 구성 변화 등을 "
            f"추가 취재할 필요가 있습니다."
        )

        article_ideas = [
            (
                f"{item['region']} 아파트 가격, "
                "금리 상승기에도 왜 함께 올랐나"
            ),

            (
                "금리와 주택가격이 같은 방향으로 움직인 "
                "지역의 공통점 분석"
            ),

            (
                "실거래 구성 변화가 지역 가격 통계에 "
                "미친 영향 점검"
            )
        ]

        questions = [
            (
                "해당 시기 지역 내 신규 입주량이나 "
                "공급 물량에 변화가 있었나?"
            ),

            (
                "거래된 아파트의 면적·연식·입지 구성에 "
                "큰 변화가 있었나?"
            ),

            (
                "특정 단지 또는 특정 가격대 거래가 "
                "중앙가격 상승을 주도했나?"
            )
        ]

        verification_data = [
            "지역별 아파트 입주 및 공급 물량",

            "아파트 면적·연식·단지별 실거래 구성",

            "주택담보대출 및 지역별 금융 여건",

            "미분양·청약·매매 수급 관련 지표"
        ]


    # -----------------------------------------------------
    # 가격 ↑ + 거래량 ↓
    # -----------------------------------------------------

    elif signal_type == "cross":

        briefing = (
            f"<strong>{item['region']}</strong>의 "
            f"<strong>{item['date']}</strong> 데이터에서 "
            f"아파트 ㎡당 중앙가격은 "
            f"<strong>{item['price_change']}% 상승</strong>했지만, "
            f"거래량은 "
            f"<strong>{abs(item['transaction_change'])}% 감소</strong>"
            f"했습니다. "
            f"가격과 거래량이 서로 반대 방향으로 움직인 패턴으로, "
            f"거래 감소가 가격 상승의 원인이라는 의미는 아닙니다. "
            f"거래 구성이나 특정 단지의 영향 등을 "
            f"추가 확인할 필요가 있습니다."
        )

        article_ideas = [
            (
                f"거래는 줄었는데 가격은 오른 "
                f"{item['region']} 아파트 시장"
            ),

            (
                "거래 절벽 속 가격 상승을 만든 "
                "실거래 구성 변화"
            ),

            (
                "적은 거래량 속 지역 가격 통계를 "
                "어떻게 해석해야 하나"
            )
        ]

        questions = [
            (
                "거래 감소가 특정 가격대 또는 "
                "특정 면적에 집중됐나?"
            ),

            (
                "고가 단지 거래 비중 증가가 "
                "중앙가격 상승에 영향을 줬나?"
            ),

            (
                "해당 시기의 신규 입주·분양·매물량은 "
                "어떻게 변했나?"
            )
        ]

        verification_data = [
            "단지별·면적별 실거래 건수",

            "가격대별 거래 비중",

            "지역 내 매물량 및 입주 물량",

            "월별 거래 취소 및 신고 변동 내역"
        ]


    else:

        return jsonify({
            "error": "Signal not found"
        }), 404


    return jsonify({
        "title": item["title"],

        "briefing": briefing,

        "article_ideas": article_ideas,

        "questions": questions,

        "verification_data": verification_data
    })