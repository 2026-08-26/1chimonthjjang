import hashlib
import os

import numpy as np
import pandas as pd

from analysis.drama.anomaly import (
    TrendAnomalyEngine
)


# =========================================================
# 기본 경로
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


PROJECT_ROOT = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        ".."
    )
)


engine = TrendAnomalyEngine()


# 서버 실행 중 반복 계산 방지
_CONTENTS_CACHE = None


# =========================================================
# CSV 경로
# =========================================================

def _get_file_path(
    filename
):

    candidate_paths = [

        os.path.join(
            PROJECT_ROOT,
            "data",
            "raw",
            filename
        ),

        os.path.join(
            PROJECT_ROOT,
            "data",
            filename
        ),

        os.path.join(
            "data",
            "raw",
            filename
        ),

        os.path.join(
            BASE_DIR,
            filename
        ),
    ]


    for path in candidate_paths:

        if os.path.exists(
            path
        ):

            return path


    return None


# =========================================================
# CSV 읽기
# =========================================================

def _read_csv(
    path
):

    encodings = [

        "cp949",

        "utf-8-sig",

        "utf-8",
    ]


    for encoding in encodings:

        try:

            return pd.read_csv(
                path,
                encoding=encoding
            )


        except UnicodeDecodeError:

            continue


    return pd.read_csv(
        path
    )


# =========================================================
# 콘텐츠별 고정 Seed
# =========================================================

def _stable_seed(
    text
):

    """
    같은 콘텐츠는 새로고침해도
    같은 결과가 나오도록 합니다.
    """

    digest = hashlib.sha256(

        text.encode(
            "utf-8"
        )

    ).hexdigest()


    return int(

        digest[:8],

        16
    )


# =========================================================
# 이상징후 프로필
# =========================================================

def _select_profile(
    seed
):

    """
    데모용 이상신호 비율

    HIGH   약 8%
    MEDIUM 약 20%
    LOW    약 72%

    실제 등급은 anomaly.py의
    Z-score 판정 때문에 약간 달라질 수 있습니다.
    """

    bucket = (
        seed % 100
    )


    if bucket < 8:

        return "HIGH"


    if bucket < 28:

        return "MEDIUM"


    return "LOW"


# =========================================================
# 30일 관심도 데이터
# =========================================================

def generate_time_series(
    is_spike=False,
    seed=None,
    category="content",
    profile=None
):

    """
    CSV에는 실제 30일 검색 관심도 시계열이 없으므로

    콘텐츠 정보:
        실제 CSV

    관심도 시계열:
        고정 seed 기반 시뮬레이션

    으로 사용합니다.

    앞 23일 = 기준
    뒤 7일  = 최근 관찰
    """


    if seed is None:

        seed = 0


    rng = np.random.default_rng(
        seed
    )


    # =====================================================
    # 카테고리별 기본 관심도
    # =====================================================

    base_level = {

        "music":
            120,

        "drama":
            100,

        "webtoon":
            85,

    }.get(
        category,
        100
    )


    # =====================================================
    # 이전 23일
    # =====================================================

    base_scale = max(

        base_level
        * 0.22,

        12
    )


    baseline = rng.normal(

        loc=
            base_level,

        scale=
            base_scale,

        size=
            23
    )


    baseline = np.clip(

        baseline,

        base_level
        * 0.35,

        None
    )


    # 기존 호출 방식 호환
    if profile is None:

        profile = (

            "HIGH"

            if is_spike

            else "LOW"
        )


    # =====================================================
    # 최근 7일
    # =====================================================

    if profile == "HIGH":

        recent_center = (

            base_level

            * rng.uniform(
                2.05,
                2.45
            )
        )


        recent_scale = (

            base_level

            * 0.14
        )


    elif profile == "MEDIUM":

        recent_center = (

            base_level

            * rng.uniform(
                1.32,
                1.50
            )
        )


        recent_scale = (

            base_level

            * 0.11
        )


    else:

        recent_center = (

            base_level

            * rng.uniform(
                0.92,
                1.16
            )
        )


        recent_scale = (

            base_level

            * 0.10
        )


    recent = rng.normal(

        loc=
            recent_center,

        scale=
            recent_scale,

        size=
            7
    )


    recent = np.clip(

        recent,

        base_level
        * 0.35,

        None
    )


    # =====================================================
    # 합치기
    # =====================================================

    values = np.concatenate(

        [
            baseline,
            recent
        ]
    )


    return [

        round(
            float(value),
            1
        )

        for value in values
    ]


# =========================================================
# 전체 콘텐츠 로드
# =========================================================

def load_all_contents():

    global _CONTENTS_CACHE


    # 이미 계산했으면 재사용
    if _CONTENTS_CACHE is not None:

        return _CONTENTS_CACHE


    contents = []

    item_id = 1


    # =====================================================
    # CSV 설정
    # =====================================================

    categories = [

        (
            "music",
            "노래",
            "kpopidolsv3.csv",
            "Group",
            "Stage Name",
            "Company"
        ),

        (
            "drama",
            "드라마",
            "kdrama.csv",
            "Name",
            None,
            "Original Network"
        ),

        (
            "webtoon",
            "웹툰",
            "naver.csv",
            "title",
            None,
            "author"
        ),
    ]


    # =====================================================
    # 카테고리 반복
    # =====================================================

    for (

        cat_key,
        cat_name,
        csv_name,
        col1,
        col2,
        col_sub

    ) in categories:


        csv_path = (
            _get_file_path(
                csv_name
            )
        )


        if not csv_path:

            print(

                "⚠️ CSV 파일을 "
                f"찾을 수 없습니다: "
                f"{csv_name}"
            )

            continue


        # =================================================
        # CSV 읽기
        # =================================================

        try:

            df = _read_csv(
                csv_path
            )


        except Exception as e:

            print(

                f"⚠️ CSV 읽기 실패: "
                f"{csv_name} / {e}"
            )

            continue


        # =================================================
        # 제목 컬럼 확인
        # =================================================

        if col1 not in df.columns:

            print(

                f"⚠️ {csv_name}에 "
                f"'{col1}' 컬럼이 없습니다."
            )

            continue


        # =================================================
        # ★ CSV 전체 분석
        #
        # head(15) 사용 안 함
        # =================================================

        df_clean = df.dropna(
            subset=[col1]
        )


        # =================================================
        # 콘텐츠 반복
        # =================================================

        for _, row in df_clean.iterrows():


            # =============================================
            # 제목
            # =============================================

            if (

                col2

                and

                col2 in df.columns

                and

                pd.notna(
                    row.get(col2)
                )
            ):

                title = (

                    f"{row[col1]}"
                    f" - "
                    f"{row[col2]}"
                )


            else:

                title = str(
                    row[col1]
                )


            # =============================================
            # 부가 정보
            # =============================================

            if (

                col_sub

                and

                col_sub in df.columns

                and

                pd.notna(
                    row.get(col_sub)
                )
            ):

                sub_val = str(
                    row.get(col_sub)
                )


            else:

                sub_val = "N/A"


            sub_info = (

                f"정보: "
                f"{sub_val}"
            )


            # =============================================
            # 고정 Seed
            # =============================================

            seed = _stable_seed(

                f"{cat_key}"
                f"|{title}"
                f"|{sub_val}"
            )


            profile = (
                _select_profile(
                    seed
                )
            )


            # =============================================
            # 30일 관심도
            # =============================================

            daily_data = (

                generate_time_series(

                    seed=
                        seed,

                    category=
                        cat_key,

                    profile=
                        profile
                )
            )


            # =============================================
            # 이상감지
            # =============================================

            metrics = (

                engine
                .calculate_metrics(
                    daily_data
                )
            )


            if not metrics:

                continue


            # =============================================
            # 결과
            # =============================================

            contents.append(

                {

                    "id":
                        item_id,

                    "category":
                        cat_key,

                    "category_name":
                        cat_name,

                    "title":
                        title,

                    "sub_info":
                        sub_info,

                    "daily_data":
                        daily_data,


                    # 데이터의 성격 명시
                    "data_source_note":
                        (
                            "콘텐츠 정보는 CSV, "
                            "30일 관심도는 "
                            "고정 seed 기반 "
                            "시뮬레이션 데이터"
                        ),


                    "trend_profile":
                        profile,


                    **metrics,
                }
            )


            item_id += 1


    # =====================================================
    # 취재 우선순위 정렬
    # =====================================================

    signal_priority = {

        "HIGH":
            3,

        "MEDIUM":
            2,

        "LOW":
            1,
    }


    contents.sort(

        key=lambda item: (

            signal_priority.get(
                item.get(
                    "signal"
                ),
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

            -item.get(
                "id",
                0
            ),
        ),

        reverse=True
    )


    # 캐시
    _CONTENTS_CACHE = contents


    return _CONTENTS_CACHE


# =========================================================
# 단독 실행 테스트
# =========================================================

if __name__ == "__main__":

    items = load_all_contents()


    print(
        f"전체 분석 콘텐츠: "
        f"{len(items)}개"
    )


    print(

        "HIGH:",

        sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "HIGH"
        )
    )


    print(

        "MEDIUM:",

        sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "MEDIUM"
        )
    )


    print(

        "LOW:",

        sum(

            1

            for item in items

            if item.get(
                "signal"
            ) == "LOW"
        )
    )


    print()

    print(
        "취재 우선순위 TOP 10"
    )


    for rank, item in enumerate(

        items[:10],

        start=1
    ):

        print(

            rank,

            item.get(
                "category_name"
            ),

            item.get(
                "title"
            ),

            item.get(
                "signal"
            ),

            item.get(
                "trend_score"
            ),

            f"{item.get('increase_rate'):+.1f}%"
        )