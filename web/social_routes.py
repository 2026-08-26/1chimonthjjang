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


CROSS_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "social_cross_top10.csv"
)

DECLINE_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "social_decline_top10.csv"
)


# ---------------------------------------------------------
# CSV 불러오기
# ---------------------------------------------------------

def load_cross_signal():

    df = pd.read_csv(
        CROSS_PATH
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    return df


def load_decline_signal():

    df = pd.read_csv(
        DECLINE_PATH
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    return df


# ---------------------------------------------------------
# 전년 동월 값 계산
# 현재값 - 변화량 = 전년 동월 값
# ---------------------------------------------------------

def get_previous_value(
    current_value,
    change_value
):

    return (
        float(current_value)
        - float(change_value)
    )


# ---------------------------------------------------------
# 막대차트용 데이터
# ---------------------------------------------------------

def make_chart_row(
    label,
    prev_value,
    current_value,
    unit=""
):

    prev_value = float(
        prev_value
    )

    current_value = float(
        current_value
    )


    max_value = max(
        abs(prev_value),
        abs(current_value),
        1
    )


    prev_width = round(
        abs(prev_value)
        / max_value
        * 100,
        1
    )


    current_width = round(
        abs(current_value)
        / max_value
        * 100,
        1
    )


    return {
        "label": label,

        "prev_value": round(
            prev_value,
            1
        ),

        "current_value": round(
            current_value,
            1
        ),

        "prev_width": prev_width,

        "current_width": current_width,

        "unit": unit
    }


# ---------------------------------------------------------
# 상세 페이지용 데이터 만들기
# ---------------------------------------------------------

def build_signal_data(
    signal_type
):

    # =====================================================
    # 1. 자연감소 + 순이동 증가
    # =====================================================

    if signal_type == "cross":

        df = load_cross_signal()


        if df.empty:

            return (
                None,
                None,
                None
            )


        row = df.iloc[0]


        natural_now = float(
            row["Natural_growth"]
        )

        migration_now = float(
            row["Net_migration"]
        )


        natural_change = float(
            row["Natural_growth_change"]
        )

        migration_change = float(
            row["Net_migration_change"]
        )


        natural_prev = get_previous_value(
            natural_now,
            natural_change
        )

        migration_prev = get_previous_value(
            migration_now,
            migration_change
        )


        item = {

            "signal_type": "cross",

            "title":
                "자연감소 ↓ + 순이동 ↑",

            "region":
                row["Region_ko"],

            "date":
                row["Date"].strftime(
                    "%Y년 %m월"
                ),

            "score":
                round(
                    float(
                        row["Signal_score"]
                    ),
                    2
                ),

            "natural_prev":
                round(
                    natural_prev,
                    0
                ),

            "natural_now":
                round(
                    natural_now,
                    0
                ),

            "natural_change":
                round(
                    natural_change,
                    0
                ),

            "migration_prev":
                round(
                    migration_prev,
                    0
                ),

            "migration_now":
                round(
                    migration_now,
                    0
                ),

            "migration_change":
                round(
                    migration_change,
                    0
                )
        }


        chart_rows = [

            make_chart_row(
                "자연증가",
                item["natural_prev"],
                item["natural_now"],
                "명"
            ),

            make_chart_row(
                "순이동",
                item["migration_prev"],
                item["migration_now"],
                "명"
            )
        ]


        table_rows = []


        for rank, (_, r) in enumerate(
            df.head(10).iterrows(),
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
                    round(
                        float(
                            r["Natural_growth"]
                        ),
                        0
                    ),

                "net_migration":
                    round(
                        float(
                            r["Net_migration"]
                        ),
                        0
                    ),

                "score":
                    round(
                        float(
                            r["Signal_score"]
                        ),
                        2
                    )
            })


        return (
            item,
            chart_rows,
            table_rows
        )


    # =====================================================
    # 2. 자연감소 + 순이동 감소
    # =====================================================

    elif signal_type == "decline":

        df = load_decline_signal()


        if df.empty:

            return (
                None,
                None,
                None
            )


        row = df.iloc[0]


        natural_now = float(
            row["Natural_growth"]
        )

        migration_now = float(
            row["Net_migration"]
        )


        natural_change = float(
            row["Natural_growth_change"]
        )

        migration_change = float(
            row["Net_migration_change"]
        )


        natural_prev = get_previous_value(
            natural_now,
            natural_change
        )

        migration_prev = get_previous_value(
            migration_now,
            migration_change
        )


        item = {

            "signal_type":
                "decline",

            "title":
                "자연감소 ↓ + 순이동 ↓",

            "region":
                row["Region_ko"],

            "date":
                row["Date"].strftime(
                    "%Y년 %m월"
                ),

            "score":
                round(
                    float(
                        row["Signal_score"]
                    ),
                    2
                ),

            "natural_prev":
                round(
                    natural_prev,
                    0
                ),

            "natural_now":
                round(
                    natural_now,
                    0
                ),

            "natural_change":
                round(
                    natural_change,
                    0
                ),

            "migration_prev":
                round(
                    migration_prev,
                    0
                ),

            "migration_now":
                round(
                    migration_now,
                    0
                ),

            "migration_change":
                round(
                    migration_change,
                    0
                )
        }


        chart_rows = [

            make_chart_row(
                "자연증가",
                item["natural_prev"],
                item["natural_now"],
                "명"
            ),

            make_chart_row(
                "순이동",
                item["migration_prev"],
                item["migration_now"],
                "명"
            )
        ]


        table_rows = []


        for rank, (_, r) in enumerate(
            df.head(10).iterrows(),
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
                    round(
                        float(
                            r["Natural_growth"]
                        ),
                        0
                    ),

                "net_migration":
                    round(
                        float(
                            r["Net_migration"]
                        ),
                        0
                    ),

                "score":
                    round(
                        float(
                            r["Signal_score"]
                        ),
                        2
                    )
            })


        return (
            item,
            chart_rows,
            table_rows
        )


    return (
        None,
        None,
        None
    )


# ---------------------------------------------------------
# 사회 메인 페이지
# ---------------------------------------------------------

@social_bp.route(
    "/social"
)
def social_index():

    cross_df = load_cross_signal()

    decline_df = load_decline_signal()


    items = []


    # 자연감소 + 순이동 증가
    if not cross_df.empty:

        row = cross_df.iloc[0]


        items.append({

            "signal_type":
                "cross",

            "title":
                "자연감소 ↓ + 순이동 ↑",

            "region":
                row["Region_ko"],

            "date":
                row["Date"].strftime(
                    "%Y년 %m월"
                ),

            "description":
                (
                    f"자연증가 "
                    f"{float(row['Natural_growth']):.0f}명, "
                    f"순이동 "
                    f"{float(row['Net_migration']):+.0f}명"
                ),

            "score":
                round(
                    float(
                        row["Signal_score"]
                    ),
                    2
                )
        })


    # 자연감소 + 순이동 감소
    if not decline_df.empty:

        row = decline_df.iloc[0]


        items.append({

            "signal_type":
                "decline",

            "title":
                "자연감소 ↓ + 순이동 ↓",

            "region":
                row["Region_ko"],

            "date":
                row["Date"].strftime(
                    "%Y년 %m월"
                ),

            "description":
                (
                    f"자연증가 "
                    f"{float(row['Natural_growth']):.0f}명, "
                    f"순이동 "
                    f"{float(row['Net_migration']):+.0f}명"
                ),

            "score":
                round(
                    float(
                        row["Signal_score"]
                    ),
                    2
                )
        })


    return render_template(
        "social/social_index.html",
        items=items
    )


# ---------------------------------------------------------
# 사회 상세 페이지
# ---------------------------------------------------------

@social_bp.route(
    "/social/detail/<signal_type>"
)
def social_detail(
    signal_type
):

    (
        item,
        chart_rows,
        table_rows
    ) = build_signal_data(
        signal_type
    )


    if item is None:

        return (
            "사회 시그널을 찾을 수 없습니다.",
            404
        )


    return render_template(
        "social/social_detail.html",

        item=item,

        chart_rows=chart_rows,

        table_rows=table_rows
    )


# ---------------------------------------------------------
# AI 취재 브리핑 API
# 버튼을 눌렀을 때만 실행
# ---------------------------------------------------------

@social_bp.route(
    "/api/social-report/<signal_type>",
    methods=["POST"]
)
def social_report(
    signal_type
):

    (
        item,
        _,
        _
    ) = build_signal_data(
        signal_type
    )


    if item is None:

        return jsonify({
            "error":
                "Signal not found"
        }), 404


    # =====================================================
    # 자연감소 + 순이동 증가
    # =====================================================

    if signal_type == "cross":

        briefing = (

            f"<strong>{item['region']}</strong>의 "

            f"<strong>{item['date']}</strong> 데이터에서 "

            f"자연증가는 전년 동월 "

            f"<strong>{item['natural_prev']:.0f}명</strong>에서 "

            f"<strong>{item['natural_now']:.0f}명</strong>으로 감소했습니다. "

            f"반면 순이동은 전년 동월 "

            f"<strong>{item['migration_prev']:.0f}명</strong>에서 "

            f"<strong>{item['migration_now']:.0f}명</strong>으로 바뀌며 "

            f"순유입 방향을 보였습니다. "

            f"자연적 인구 변화와 지역 간 이동이 "

            f"서로 다른 방향으로 움직인 이례적 패턴입니다. "

            f"이 결과만으로 원인을 단정할 수는 없으며, "

            f"연령대별 이동과 주거·고용 여건 등을 "

            f"추가로 확인할 필요가 있습니다."
        )


        article_ideas = [

            f"인구는 자연감소인데 사람은 들어온 "
            f"{item['region']}, 무슨 일이 있었나",

            "출생·사망과 지역 이동이 "
            "엇갈린 지역의 공통점",

            "지역 인구 감소 속 순유입을 만든 "
            "연령대와 이동 목적 추적"
        ]


        questions = [

            "순유입은 어떤 연령대에서 "
            "가장 크게 나타났나?",

            "취업·교육·주거 이동이 "
            "순유입과 함께 나타났나?",

            "특정 시군구가 전체 지역의 "
            "순이동 증가를 주도했나?"
        ]


        verification_data = [

            "연령대별 순이동 데이터",

            "시군구별 전입·전출 데이터",

            "지역별 고용 및 사업체 변화",

            "주택 공급·입주·전월세 관련 데이터"
        ]


    # =====================================================
    # 자연감소 + 순이동 감소
    # =====================================================

    elif signal_type == "decline":

        briefing = (

            f"<strong>{item['region']}</strong>의 "

            f"<strong>{item['date']}</strong> 데이터에서 "

            f"자연증가는 전년 동월 "

            f"<strong>{item['natural_prev']:.0f}명</strong>에서 "

            f"<strong>{item['natural_now']:.0f}명</strong>으로 변했습니다. "

            f"순이동 역시 전년 동월 "

            f"<strong>{item['migration_prev']:.0f}명</strong>에서 "

            f"<strong>{item['migration_now']:.0f}명</strong>으로 변하며 "

            f"순유출 방향을 보였습니다. "

            f"자연감소와 순유출이 동시에 나타난 패턴으로, "

            f"두 현상이 같은 원인 때문에 발생했다고 "

            f"단정할 수는 없습니다. "

            f"연령별 인구 이동과 지역의 고용·교육·주거 환경을 "

            f"추가로 취재할 필요가 있습니다."
        )


        article_ideas = [

            f"자연감소와 순유출이 동시에 나타난 "
            f"{item['region']}",

            "인구 감소가 겹친 지역, "
            "어떤 계층이 먼저 빠져나갔나",

            "자연감소와 인구 이동을 함께 보니 "
            "드러난 지역 변화"
        ]


        questions = [

            "순유출은 어떤 연령층에서 "
            "가장 크게 나타났나?",

            "청년층 유출과 자연감소가 "
            "동시에 나타났나?",

            "지역 내 일자리·교육·주거 환경에 "
            "어떤 변화가 있었나?"
        ]


        verification_data = [

            "연령별 전입·전출 데이터",

            "출생·사망 세부 통계",

            "지역별 고용률 및 사업체 수",

            "학교·대학 및 주택 공급 관련 데이터"
        ]


    else:

        return jsonify({
            "error":
                "Signal not found"
        }), 404


    return jsonify({

        "title":
            item["title"],

        "briefing":
            briefing,

        "article_ideas":
            article_ideas,

        "questions":
            questions,

        "verification_data":
            verification_data
    })