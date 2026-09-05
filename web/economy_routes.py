import os

import pandas as pd
from flask import Blueprint, jsonify, render_template


economy_bp = Blueprint(
    "economy",
    __name__
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        BASE_DIR,
        ".."
    )
)

SIGNAL_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "all_economy_signals.csv"
)


def load_economy_signals():

    df = pd.read_csv(
        SIGNAL_PATH
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    return df.sort_values(
        [
            "Signal_score",
            "Date"
        ],
        ascending=[
            False,
            False
        ]
    )


def safe_number(value, digits=2):

    if pd.isna(value):
        return None

    return round(
        float(value),
        digits
    )


# =========================================================
# 경제 메인
# =========================================================

@economy_bp.route(
    "/economy"
)
def economy_index():

    df = load_economy_signals()

    stats = {
        "total":
            len(df),

        "rules":
            df["signal_type"].nunique(),

        "high":
            df["severity"]
            .eq("HIGH")
            .sum(),

        "medium":
            df["severity"]
            .eq("MEDIUM")
            .sum(),

        "low":
            df["severity"]
            .eq("LOW")
            .sum()
    }


    items = []


    for signal_type, group in df.groupby(
        "signal_type",
        sort=False
    ):

        group = group.sort_values(
            "Signal_score",
            ascending=False
        )

        row = group.iloc[0]


        items.append({
            "signal_type":
                signal_type,

            "signal_name":
                row["signal_name"],

            "region":
                row["Region"],

            "date":
                row["Date"].strftime(
                    "%Y.%m"
                ),

            "score":
                safe_number(
                    row["Signal_score"]
                ),

            "severity":
                row["severity"],

            "reason":
                row["reason"],

            "count":
                len(group)
        })


    items = sorted(
        items,
        key=lambda x: x["score"],
        reverse=True
    )


    return render_template(
        "economy/economy_index.html",
        items=items,
        stats=stats
    )


# =========================================================
# 경제 상세
# =========================================================

@economy_bp.route(
    "/economy/detail/<signal_type>"
)
def economy_detail(
    signal_type
):

    df = load_economy_signals()

    signal_df = df[
        df["signal_type"]
        == signal_type
    ].copy()


    if signal_df.empty:

        return (
            "경제 시그널을 찾을 수 없습니다.",
            404
        )


    signal_df = signal_df.sort_values(
        "Signal_score",
        ascending=False
    )

    row = signal_df.iloc[0]


    item = {
        "signal_type":
            signal_type,

        "signal_name":
            row["signal_name"],

        "region":
            row["Region"],

        "date":
            row["Date"].strftime(
                "%Y년 %m월"
            ),

        "score":
            safe_number(
                row["Signal_score"]
            ),

        "severity":
            row["severity"],

        "reason":
            row["reason"],

        "price_prev":
            safe_number(
                row["Price_prev"]
            ),

        "price_now":
            safe_number(
                row["Median_price_per_m2"]
            ),

        "price_change":
            safe_number(
                row["Price_yoy_pct"]
            ),

        "transaction_prev":
            safe_number(
                row["Transaction_prev"],
                0
            ),

        "transaction_now":
            safe_number(
                row["Transaction_count"],
                0
            ),

        "transaction_change":
            safe_number(
                row["Transaction_yoy_pct"]
            ),

        "rate_prev":
            safe_number(
                row["Base_rate_prev"]
            ),

        "rate_now":
            safe_number(
                row["Base_rate"]
            ),

        "rate_change":
            safe_number(
                row["Base_rate_change"]
            )
    }


    table_rows = []


    for rank, (_, r) in enumerate(
        signal_df
        .head(10)
        .iterrows(),
        start=1
    ):

        table_rows.append({
            "rank":
                rank,

            "date":
                r["Date"].strftime(
                    "%Y.%m"
                ),

            "region":
                r["Region"],

            "price_change":
                safe_number(
                    r["Price_yoy_pct"]
                ),

            "transaction_change":
                safe_number(
                    r["Transaction_yoy_pct"]
                ),

            "rate_change":
                safe_number(
                    r["Base_rate_change"]
                ),

            "score":
                safe_number(
                    r["Signal_score"]
                ),

            "severity":
                r["severity"]
        })


    return render_template(
        "economy/economy_detail.html",
        item=item,
        table_rows=table_rows,
        candidate_count=len(signal_df)
    )


# =========================================================
# AI 취재 브리핑
# =========================================================

@economy_bp.route(
    "/api/economy-report/<signal_type>",
    methods=["POST"]
)
def economy_report(
    signal_type
):

    df = load_economy_signals()

    signal_df = df[
        df["signal_type"]
        == signal_type
    ]


    if signal_df.empty:

        return jsonify({
            "error":
                "Signal not found"
        }), 404


    row = signal_df.iloc[0]

    region = row["Region"]

    date = row["Date"].strftime(
        "%Y년 %m월"
    )

    signal_name = row["signal_name"]

    reason = row["reason"]

    price_change = safe_number(
        row["Price_yoy_pct"]
    )

    transaction_change = safe_number(
        row["Transaction_yoy_pct"]
    )


    briefing = (
        f"<strong>{region}</strong>의 "
        f"<strong>{date}</strong> 데이터에서 "
        f"<strong>{signal_name}</strong> 시그널이 탐지되었습니다. "
        f"{reason}. "
        f"주택가격은 전년 동월 대비 "
        f"<strong>{price_change:+.1f}%</strong>, "
        f"거래량은 "
        f"<strong>{transaction_change:+.1f}%</strong> 변화했습니다. "
        f"이 패턴만으로 시장 변화의 원인을 단정할 수 없으며 "
        f"공급, 수요, 정책, 지역 개발 등 추가 자료 확인이 필요합니다."
    )


    article_ideas = [
        f"{region}에서 나타난 '{signal_name}', 시장에 무슨 일이 있었나",

        "가격과 거래량 데이터를 함께 보니 드러난 지역별 온도차",

        "금리 변화 속 지역 주택시장의 이례적 움직임 추적"
    ]


    questions = [
        "특정 단지나 면적대가 가격 변화를 주도했나?",

        "거래량 변화가 실수요·투자수요 중 어느 쪽에서 나타났나?",

        "같은 시기 공급·입주·정책 변화가 있었나?"
    ]


    verification_data = [
        "지역별 아파트 실거래 세부 데이터",

        "주택 공급 및 입주 물량",

        "매매·전세 가격지수",

        "지역별 인구·고용 및 개발사업 데이터"
    ]


    return jsonify({
        "title":
            signal_name,

        "briefing":
            briefing,

        "article_ideas":
            article_ideas,

        "questions":
            questions,

        "verification_data":
            verification_data
    })