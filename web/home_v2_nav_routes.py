from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data

from analysis.drama.mock_data import load_all_contents


# =========================================================
# BLUEPRINT
# =========================================================

home_v2_nav_bp = Blueprint(
    "home_v2_nav",
    __name__
)


# =========================================================
# K콘텐츠 메인페이지 데이터 생성
# =========================================================

def load_kcontent_home_signals(limit=5):

    try:

        all_items = load_all_contents()

    except Exception as e:

        print(
            "[HOME ERROR] K콘텐츠 로딩 실패:",
            e
        )

        return []


    # =====================================================
    # 신호 우선순위
    # =====================================================

    signal_priority = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }


    # =====================================================
    # 정렬
    #
    # HIGH > MEDIUM > LOW
    # trend_score
    # z_score
    # increase_rate
    # =====================================================

    sorted_items = sorted(
        all_items,

        key=lambda item: (

            signal_priority.get(
                item.get("signal"),
                0
            ),

            float(
                item.get(
                    "trend_score",
                    0
                )
                or 0
            ),

            float(
                item.get(
                    "z_score",
                    0
                )
                or 0
            ),

            float(
                item.get(
                    "increase_rate",
                    0
                )
                or 0
            )
        ),

        reverse=True
    )


    result = []


    # =====================================================
    # TOP 5
    # =====================================================

    for rank, item in enumerate(
        sorted_items[:limit],
        start=1
    ):

        z_score = float(
            item.get(
                "z_score",
                0
            )
            or 0
        )


        result.append(
            {

                # 메인 분야
                "category":
                    "K콘텐츠",


                # 노래 / 드라마 / 웹툰
                "region":
                    item.get(
                        "category_name",
                        "콘텐츠"
                    ),


                # 실제 콘텐츠 이름
                "signal_name":
                    item.get(
                        "title",
                        "콘텐츠"
                    ),


                # K콘텐츠 메인 표시 점수
                # 99/10 방식 사용 X
                # 실제 Z-score 사용
                "score":
                    round(
                        z_score,
                        2
                    ),


                # HIGH / MEDIUM / LOW
                "severity":
                    item.get(
                        "signal",
                        "LOW"
                    ),


                # music / drama / webtoon
                "signal_type":
                    item.get(
                        "category",
                        "content"
                    ),


                # 상세페이지
                "detail_url":
                    f"/detail/{item.get('id')}",


                # 콘텐츠 ID
                "item_id":
                    item.get(
                        "id"
                    ),


                # ★ K콘텐츠 전용 순위
                "category_rank":
                    rank,


                # 추가 데이터
                "trend_score":
                    item.get(
                        "trend_score",
                        0
                    ),

                "z_score":
                    round(
                        z_score,
                        2
                    ),

                "increase_rate":
                    item.get(
                        "increase_rate",
                        0
                    ),
            }
        )


    return result


# =========================================================
# HOME V2 NAV
# =========================================================

@home_v2_nav_bp.route(
    "/home-v2-nav"
)
def home_v2_nav():

    # =====================================================
    # 기존 사회 / 경제 데이터
    # =====================================================

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart

    ) = load_dashboard_data()


    # =====================================================
    # LIST 변환
    # =====================================================

    top_signals = list(
        top_signals
        or []
    )


    # =====================================================
    # ★ 중요
    #
    # load_dashboard_data 안에 들어있는
    # 기존 임시 K콘텐츠
    #
    # 콘텐츠1
    # 콘텐츠2
    # 콘텐츠3
    # 콘텐츠4
    # 콘텐츠5
    #
    # 를 전부 제거
    # =====================================================

    top_signals = [

        item

        for item in top_signals

        if item.get(
            "category"
        ) != "K콘텐츠"

    ]


    # =====================================================
    # 실제 K콘텐츠 이상감지 데이터
    # =====================================================

    kcontent_signals = (
        load_kcontent_home_signals(
            limit=5
        )
    )


    # =====================================================
    # 기존 사회/경제는 유지
    # 실제 K콘텐츠만 뒤에 추가
    # =====================================================

    top_signals.extend(
        kcontent_signals
    )


    # =====================================================
    # 터미널 확인
    # =====================================================

    print()
    print(
        "======================================"
    )

    print(
        "[HOME] 메인페이지 데이터 확인"
    )

    print(
        "전체 시그널:",
        len(top_signals)
    )

    print(
        "K콘텐츠:",
        len(kcontent_signals)
    )


    for item in kcontent_signals:

        print(
            f"{item['category_rank']:02d}",
            item["region"],
            item["signal_name"],
            "Z:",
            item["score"],
            item["severity"]
        )


    print(
        "======================================"
    )
    print()


    # =====================================================
    # TEMPLATE
    # =====================================================

    return render_template(
        "home/home_index_v2_nav.html",

        stats=stats,

        top_signals=top_signals,

        monthly_chart=monthly_chart,

        rule_chart=rule_chart
    )