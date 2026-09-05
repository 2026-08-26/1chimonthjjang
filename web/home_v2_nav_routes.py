from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data

from analysis.drama.mock_data import load_all_contents

import os
import pandas as pd
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
def load_stock_home_signals(limit=5):
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        stock_path = os.path.join(
            base_dir,
            "result",
            "stock",
            "all_stock_signals.csv"
        )

        df = pd.read_csv(stock_path)

        # 점수가 높은 종목부터
        df = df.sort_values(
            "score",
            ascending=False
        ).head(limit)

        result = []

        for rank, (_, row) in enumerate(df.iterrows(), start=1):

            # 어떤 시그널이 발생했는지 한글로 표시
            signals = []

            if row["volume_signal"]:
                signals.append("거래량 급증")

            if row["price_signal"]:
                signals.append("가격 이상")

            if row["concentration_signal"]:
                signals.append("수급 집중")

            signal_name = " + ".join(signals)

            # 등급
            score = float(row["score"])

            if score >= 4:
                severity = "HIGH"
            elif score >= 2:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            result.append({
                "category": "주식",
                "region": row["market"],
                "signal_name": f"{row['name']} · {signal_name}",
                "score": round(score, 2),
                "severity": severity,
                "signal_type": "stock",
                "detail_url": f"/stock/detail/{row['code']}",
                "category_rank": rank,
                "code": row["code"],
                "name": row["name"]
            })

        return result

    except Exception as e:
        print("[HOME ERROR] 주식 시그널 로딩 실패:", e)
        return []
def load_baseball_home_signals(limit=5):
    try:
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        processed_dir = os.path.join(
            base_dir,
            "data",
            "processed"
        )

        # ==========================================
        # 야구 이상신호 CSV
        # ==========================================

        temp = pd.read_csv(
            os.path.join(processed_dir, "temp_signal.csv")
        )

        humidity = pd.read_csv(
            os.path.join(processed_dir, "humidity_signal.csv")
        )

        rain = pd.read_csv(
            os.path.join(processed_dir, "rain_signal.csv")
        )

        # ==========================================
        # 각 데이터가 어떤 날씨 신호인지 표시
        # ==========================================

        temp["weather_type"] = "기온"
        temp["condition"] = temp["temp_group"]

        humidity["weather_type"] = "습도"
        humidity["condition"] = humidity["humidity_group"]

        rain["weather_type"] = "강수"
        rain["condition"] = rain["rain_group"]

        # ==========================================
        # 세 종류 이상신호 합치기
        # ==========================================

        baseball = pd.concat(
            [temp, humidity, rain],
            ignore_index=True
        )

        # 이상신호 강도 기준 TOP
        baseball = baseball.sort_values(
            "signal_strength",
            ascending=False
        )

        # 같은 선수가 여러 번 TOP에 나오는 것을 방지
        baseball = baseball.drop_duplicates(
            subset=["player_name"],
            keep="first"
        )

        baseball = baseball.head(limit)

        result = []

        # ==========================================
        # 홈 화면 형식으로 변환
        # ==========================================

        for rank, (_, row) in enumerate(
            baseball.iterrows(),
            start=1
        ):

            strength = float(row["signal_strength"])
            diff = float(row["weather_diff"])

            # 성적 상승 / 하락
            if diff > 0:
                direction = "성적 상승"
            else:
                direction = "성적 하락"

            # 이상신호 등급
            if strength >= 1.0:
                severity = "HIGH"
            elif strength >= 0.5:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            signal_name = (
                f"{row['player_name']} · "
                f"{row['weather_type']} {row['condition']}에서 "
                f"{direction}"
            )

            result.append({
                "category": "야구",

                # 화면의 '구분' 부분
                "region": row["weather_type"],

                # 취재 시그널
                "signal_name": signal_name,

                # 이상신호 강도
                "score": round(strength, 2),

                "severity": severity,

                "signal_type": "baseball",

                # 일단 기존 야구 페이지로 연결
                "detail_url": "/baseball",

                "category_rank": rank,

                # 추가 데이터
                "player_name": row["player_name"],
                "weather_type": row["weather_type"],
                "condition": str(row["condition"]),
                "weather_diff": round(diff, 3)
            })

        return result

    except Exception as e:
        print(
            "[HOME ERROR] 야구 시그널 로딩 실패:",
            e
        )
        return []
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

    stock_signals = (
        load_stock_home_signals(
            limit=5
    )
)
    baseball_signals = load_baseball_home_signals(limit=5)
    # =====================================================
    # 기존 사회/경제는 유지
    # 실제 K콘텐츠만 뒤에 추가
    # =====================================================

    top_signals.extend(
        kcontent_signals
    )

    top_signals.extend(
    stock_signals
    )
    top_signals.extend(baseball_signals)
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
    print(
        "주식:",
        len(stock_signals)
    )   
    print("야구:", len(baseball_signals))
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