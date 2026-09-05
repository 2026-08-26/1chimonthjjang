import os

import pandas as pd
from flask import Blueprint, jsonify, render_template


social_bp = Blueprint(
    "social",
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
    "all_social_signals.csv"
)


# =========================================================
# 데이터 불러오기
# =========================================================

def load_social_signals():

    df = pd.read_csv(
        SIGNAL_PATH
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    df = df.sort_values(
        [
            "Signal_score",
            "Date"
        ],
        ascending=[
            False,
            False
        ]
    )

    return df


# =========================================================
# 숫자 안전 변환
# =========================================================

def safe_number(value, digits=0):

    if pd.isna(value):
        return None

    return round(
        float(value),
        digits
    )


# =========================================================
# 사회 메인 페이지
# =========================================================

@social_bp.route(
    "/social"
)
def social_index():

    df = load_social_signals()

    stats = {
        "total": len(df),

        "rules": (
            df["signal_type"]
            .nunique()
        ),

        "high": (
            df["severity"]
            .eq("HIGH")
            .sum()
        ),

        "medium": (
            df["severity"]
            .eq("MEDIUM")
            .sum()
        ),

        "low": (
            df["severity"]
            .eq("LOW")
            .sum()
        )
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
                row["Region_ko"],

            "date":
                row["Date"].strftime(
                    "%Y.%m"
                ),

            "score":
                safe_number(
                    row["Signal_score"],
                    2
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
        "social/social_index.html",
        items=items,
        stats=stats
    )
    # ==================================================
# 사회 시그널 V2
# 후보2 뉴스룸 디자인 테스트 페이지
# ==================================================

@social_bp.route("/social-v2")
def social_index_v2():

    df = load_social_signals()

    # ----------------------------------------------
    # 1. 상단 통계
    # 후보2 템플릿에서 사용하는 이름에 맞춤
    # ----------------------------------------------

    stats = {
        "total_candidates": len(df),

        "total_rules": (
            df["signal_type"]
            .nunique()
        ),

        "high_count": (
            df["severity"]
            .eq("HIGH")
            .sum()
        ),

        "medium_count": (
            df["severity"]
            .eq("MEDIUM")
            .sum()
        ),

        "low_count": (
            df["severity"]
            .eq("LOW")
            .sum()
        )
    }


    # ----------------------------------------------
    # 2. 취재 우선순위
    # Signal Score가 높은 후보 TOP 7
    # ----------------------------------------------

    top_df = (
        df
        .sort_values(
            ["Signal_score", "Date"],
            ascending=[False, False]
        )
        .head(7)
    )


    top_signals = []

    for _, row in top_df.iterrows():

        top_signals.append({
            "category": "사회",

            "region":
                row["Region_ko"],

            "signal_name":
                row["signal_name"],

            "date":
                row["Date"].strftime("%Y.%m"),

            "score":
                safe_number(
                    row["Signal_score"],
                    2
                ),

            "severity":
                row["severity"],

            "signal_type":
                row["signal_type"],

            "detail_url":
                "/social/detail/"
                + str(row["signal_type"])
        })


    # ----------------------------------------------
    # 3. 월별 탐지량
    # 후보2의 선 그래프에서 사용
    # ----------------------------------------------

    monthly = (
        df
        .set_index("Date")
        .resample("MS")
        .size()
        .reset_index(name="count")
    )


    monthly_chart = []

    for _, row in monthly.iterrows():

        monthly_chart.append({
            "date":
                row["Date"].strftime("%Y.%m"),

            "count":
                int(row["count"])
        })


    # ----------------------------------------------
    # 4. 탐지 규칙별 발생량
    # 후보2 오른쪽 막대그래프에서 사용
    # ----------------------------------------------

    rule_counts = (
        df
        .groupby(
            ["signal_type", "signal_name"]
        )
        .size()
        .reset_index(name="count")
        .sort_values(
            "count",
            ascending=False
        )
    )


    max_count = (
        rule_counts["count"].max()
        if len(rule_counts) > 0
        else 1
    )


    rule_chart = []

    for _, row in rule_counts.iterrows():

        rule_chart.append({
            "name":
                row["signal_name"],

            "signal_type":
                row["signal_type"],

            "count":
                int(row["count"]),

            "width":
                round(
                    row["count"]
                    / max_count
                    * 100,
                    1
                )
        })


    # ----------------------------------------------
    # 5. V2 템플릿 전달
    # ----------------------------------------------

    return render_template(
        "social/social_index_v2.html",

        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart
    )


# =========================================================
# 사회 상세 페이지
# =========================================================

@social_bp.route(
    "/social/detail/<signal_type>"
)
def social_detail(
    signal_type
):

    df = load_social_signals()

    signal_df = df[
        df["signal_type"]
        == signal_type
    ].copy()


    if signal_df.empty:

        return (
            "사회 시그널을 찾을 수 없습니다.",
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
            row["Region_ko"],

        "date":
            row["Date"].strftime(
                "%Y년 %m월"
            ),

        "score":
            safe_number(
                row["Signal_score"],
                2
            ),

        "severity":
            row["severity"],

        "reason":
            row["reason"],

        "natural_prev":
            safe_number(
                row["Natural_growth_prev"]
            ),

        "natural_now":
            safe_number(
                row["Natural_growth"]
            ),

        "natural_change":
            safe_number(
                row["Natural_growth_change"]
            ),

        "migration_prev":
            safe_number(
                row["Net_migration_prev"]
            ),

        "migration_now":
            safe_number(
                row["Net_migration"]
            ),

        "migration_change":
            safe_number(
                row["Net_migration_change"]
            )
    }


    # -----------------------------------------------------
    # 그래프용 데이터
    # -----------------------------------------------------

    chart_rows = []

    metrics = [
        (
            "자연증가",
            item["natural_prev"],
            item["natural_now"]
        ),

        (
            "순이동",
            item["migration_prev"],
            item["migration_now"]
        )
    ]


    for label, prev_value, now_value in metrics:

        values = [
            abs(v)
            for v in [
                prev_value,
                now_value
            ]
            if v is not None
        ]

        max_value = max(
            values + [1]
        )

        prev_width = 0
        now_width = 0


        if prev_value is not None:

            prev_width = round(
                abs(prev_value)
                / max_value
                * 100,
                1
            )


        if now_value is not None:

            now_width = round(
                abs(now_value)
                / max_value
                * 100,
                1
            )


        chart_rows.append({
            "label":
                label,

            "prev_value":
                prev_value,

            "current_value":
                now_value,

            "prev_width":
                prev_width,

            "current_width":
                now_width
        })


    # -----------------------------------------------------
    # TOP 10
    # -----------------------------------------------------

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
                r["Region_ko"],

            "natural_growth":
                safe_number(
                    r["Natural_growth"]
                ),

            "net_migration":
                safe_number(
                    r["Net_migration"]
                ),

            "score":
                safe_number(
                    r["Signal_score"],
                    2
                ),

            "severity":
                r["severity"]
        })


    return render_template(
        "social/social_detail.html",
        item=item,
        chart_rows=chart_rows,
        table_rows=table_rows,
        candidate_count=len(signal_df)
    )


# =========================================================
# AI 취재 브리핑
# =========================================================

@social_bp.route(
    "/api/social-report/<signal_type>",
    methods=["POST"]
)
def social_report(
    signal_type
):

    df = load_social_signals()

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


    region = row["Region_ko"]

    date = row["Date"].strftime(
        "%Y년 %m월"
    )

    signal_name = row["signal_name"]

    reason = row["reason"]

    natural_now = safe_number(
        row["Natural_growth"]
    )

    migration_now = safe_number(
        row["Net_migration"]
    )


    briefing = (
        f"<strong>{region}</strong>의 "
        f"<strong>{date}</strong> 데이터에서 "
        f"<strong>{signal_name}</strong> 시그널이 탐지되었습니다. "
        f"{reason}. "
        f"현재 자연증가는 <strong>{natural_now:,.0f}명</strong>, "
        f"순이동은 <strong>{migration_now:,.0f}명</strong>입니다. "
        f"이 결과는 통계적 패턴을 보여주는 것이며 "
        f"특정 원인을 의미하지는 않습니다. "
        f"원인을 확인하기 위한 추가 취재가 필요합니다."
    )


    article_ideas = [
        f"{region}에서 나타난 '{signal_name}', 어떤 변화가 있었나",

        "인구 이동과 자연증감이 엇갈린 지역의 공통점",

        "통계적 이상징후 뒤에 숨은 지역 인구구조 변화"
    ]


    questions = [
        "어떤 연령대의 전입·전출 변화가 가장 컸나?",

        "특정 시군구가 전체 변화량을 주도했나?",

        "일자리·주거·교육 환경 변화와 같은 시기에 나타났나?"
    ]


    verification_data = [
        "연령대별 전입·전출 데이터",

        "시군구별 인구이동 데이터",

        "지역별 고용·사업체 데이터",

        "주택 공급 및 주거비 관련 데이터"
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