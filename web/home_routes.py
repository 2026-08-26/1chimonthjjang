import os
import pandas as pd

from flask import Blueprint, render_template


home_bp = Blueprint("home", __name__)


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

SOCIAL_PATH = os.path.join(
    BASE_DIR,
    "result",
    "all_social_signals.csv"
)

ECONOMY_PATH = os.path.join(
    BASE_DIR,
    "result",
    "all_economy_signals.csv"
)


def load_dashboard_data():

    # ==========================================
    # 1. 데이터 불러오기
    # ==========================================

    social = pd.read_csv(SOCIAL_PATH)
    economy = pd.read_csv(ECONOMY_PATH)

    social["Date"] = pd.to_datetime(
        social["Date"],
        errors="coerce"
    )

    economy["Date"] = pd.to_datetime(
        economy["Date"],
        errors="coerce"
    )


    # ==========================================
    # 2. 공통 컬럼 맞추기
    # ==========================================

    social["category"] = "사회"
    economy["category"] = "경제"

    social["region_display"] = social["Region_ko"]
    economy["region_display"] = economy["Region"]

    social["signal_display"] = social["signal_name"]
    economy["signal_display"] = economy["signal_name"]


    common_columns = [
        "Date",
        "category",
        "region_display",
        "signal_display",
        "Signal_score",
        "severity",
        "signal_type",
    ]


    combined = pd.concat(
        [
            social[common_columns],
            economy[common_columns],
        ],
        ignore_index=True
    )


    combined = combined.dropna(
        subset=["Date"]
    )


    combined = combined.sort_values(
        ["Signal_score", "Date"],
        ascending=[False, False]
    )


    # ==========================================
    # 3. 기본 통계
    # ==========================================

    total_candidates = len(combined)

    social_rules = social[
        "signal_type"
    ].nunique()

    economy_rules = economy[
        "signal_type"
    ].nunique()

    total_rules = (
        social_rules
        + economy_rules
    )


    severity_upper = (
        combined["severity"]
        .astype(str)
        .str.upper()
    )


    high_count = int(
        severity_upper.eq("HIGH").sum()
    )

    medium_count = int(
        severity_upper.eq("MEDIUM").sum()
    )

    low_count = int(
        severity_upper.eq("LOW").sum()
    )


    stats = {
        "total_candidates": total_candidates,
        "total_rules": total_rules,
        "social_rules": social_rules,
        "economy_rules": economy_rules,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
    }


    # ==========================================
    # 4. TOP 시그널
    # ==========================================

    top_signals = []


    for _, row in combined.head(7).iterrows():

        if row["category"] == "사회":

            detail_url = (
                "/social/detail/"
                + str(row["signal_type"])
            )

        else:

            detail_url = (
                "/economy/detail/"
                + str(row["signal_type"])
            )


        top_signals.append(
            {
                "category": row["category"],

                "region": row[
                    "region_display"
                ],

                "signal_name": row[
                    "signal_display"
                ],

                "date": (
                    row["Date"].strftime(
                        "%Y.%m"
                    )
                    if pd.notna(row["Date"])
                    else "-"
                ),

                "score": round(
                    float(
                        row["Signal_score"]
                    ),
                    2
                ),

                "severity": str(
                    row["severity"]
                ).upper(),

                "signal_type": row[
                    "signal_type"
                ],

                "detail_url": detail_url,
            }
        )


    # ==========================================
    # 5. 월별 시그널 발생 추이
    # ==========================================

    monthly = (
        combined
        .set_index("Date")
        .resample("MS")
        .size()
        .rename("count")
        .reset_index()
    )


    monthly_chart = []

    for _, row in monthly.iterrows():

        monthly_chart.append(
            {
                "date": row[
                    "Date"
                ].strftime("%Y.%m"),

                "count": int(
                    row["count"]
                )
            }
        )


    # ==========================================
    # 6. 탐지 규칙별 발생 건수
    # ==========================================

    rule_counts = (
        combined
        .groupby(
            [
                "category",
                "signal_display",
                "signal_type"
            ]
        )
        .size()
        .reset_index(
            name="count"
        )
        .sort_values(
            "count",
            ascending=False
        )
    )


    rule_max = (
        int(
            rule_counts["count"].max()
        )
        if len(rule_counts) > 0
        else 1
    )


    rule_chart = []

    for _, row in rule_counts.iterrows():

        rule_chart.append(
            {
                "category": row[
                    "category"
                ],

                "name": row[
                    "signal_display"
                ],

                "signal_type": row[
                    "signal_type"
                ],

                "count": int(
                    row["count"]
                ),

                "width": round(
                    float(
                        row["count"]
                    )
                    / rule_max
                    * 100,
                    1
                )
            }
        )


    return (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    )


@home_bp.route("/home")
def home():

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    ) = load_dashboard_data()


    return render_template(
        "home/home_index.html",

        stats=stats,

        top_signals=top_signals,

        monthly_chart=monthly_chart,

        rule_chart=rule_chart
    )