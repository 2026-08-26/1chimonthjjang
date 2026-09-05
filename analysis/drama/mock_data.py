import hashlib
import os

import numpy as np
import pandas as pd

from analysis.drama.anomaly import TrendAnomalyEngine


# =========================================================
# 경로 설정
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..")
)

engine = TrendAnomalyEngine()


# =========================================================
# CSV 파일 찾기
# =========================================================

def _get_file_path(filename):

    candidate_paths = [
        os.path.join(PROJECT_ROOT, "data", "raw", filename),
        os.path.join(PROJECT_ROOT, "data", filename),
        os.path.join(BASE_DIR, filename),
    ]

    for path in candidate_paths:

        if os.path.exists(path):
            return path

    return None


# =========================================================
# CSV 읽기
# =========================================================

def _read_csv(path):

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

    return pd.read_csv(path)


# =========================================================
# 콘텐츠마다 고정 seed 생성
#
# 새로고침해도 같은 콘텐츠는 같은 결과가 나오도록 함
# =========================================================

def _stable_seed(text):

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return int(
        digest[:8],
        16
    )


# =========================================================
# 이상징후 프로필
# =========================================================

def _select_profile(seed):

    bucket = seed % 10

    # 약 40%
    if bucket <= 3:
        return "HIGH"

    # 약 30%
    if bucket <= 6:
        return "MEDIUM"

    # 약 30%
    return "LOW"


# =========================================================
# 30일 관심도 데이터 생성
#
# 앞 23일 = 기준
# 뒤 7일 = 최근
# =========================================================

def generate_time_series(
    seed,
    category="content",
    profile="LOW"
):

    rng = np.random.default_rng(seed)


    # 카테고리별 기본 관심도
    base_level = {
        "music": 120,
        "drama": 100,
        "webtoon": 85,
    }.get(
        category,
        100
    )


    # =====================================================
    # 이전 23일
    # =====================================================

    base_scale = max(
        base_level * 0.22,
        12
    )

    baseline = rng.normal(
        loc=base_level,
        scale=base_scale,
        size=23
    )

    baseline = np.clip(
        baseline,
        base_level * 0.35,
        None
    )


    # =====================================================
    # 최근 7일
    # =====================================================

    if profile == "HIGH":

        recent_center = (
            base_level
            * rng.uniform(2.15, 2.65)
        )

        recent_scale = (
            base_level * 0.15
        )


    elif profile == "MEDIUM":

        recent_center = (
            base_level
            * rng.uniform(1.38, 1.55)
        )

        recent_scale = (
            base_level * 0.12
        )


    else:

        recent_center = (
            base_level
            * rng.uniform(0.95, 1.18)
        )

        recent_scale = (
            base_level * 0.10
        )


    recent = rng.normal(
        loc=recent_center,
        scale=recent_scale,
        size=7
    )

    recent = np.clip(
        recent,
        1,
        None
    )


    return np.concatenate(
        [
            baseline,
            recent
        ]
    ).tolist()


# =========================================================
# 카테고리 하나 읽기
# =========================================================

def _load_category(
    cat_key,
    cat_name,
    csv_name,
    col1,
    col2,
    col_sub,
    start_id
):

    contents = []

    item_id = start_id


    # CSV 경로
    csv_path = _get_file_path(
        csv_name
    )


    if csv_path is None:

        print(
            f"[경고] CSV 파일을 찾을 수 없습니다: {csv_name}"
        )

        return contents, item_id


    # CSV 읽기
    try:

        df = _read_csv(
            csv_path
        )

    except Exception as e:

        print(
            f"[경고] CSV 읽기 실패: {csv_name}"
        )

        print(e)

        return contents, item_id


    # 제목 컬럼 존재 확인
    if col1 not in df.columns:

        print(
            f"[경고] {csv_name} 파일에 "
            f"'{col1}' 컬럼이 없습니다."
        )

        print(
            "현재 컬럼:",
            list(df.columns)
        )

        return contents, item_id


    # =====================================================
    # CSV 전체 데이터 사용
    #
    # 기존 .head(15) 삭제
    # =====================================================

    df_clean = df.dropna(
        subset=[col1]
    )


    for _, row in df_clean.iterrows():


        # =================================================
        # 제목
        # =================================================

        if (
            col2 is not None
            and col2 in df.columns
            and pd.notna(row.get(col2))
        ):

            title = (
                f"{row[col1]} - {row[col2]}"
            )

        else:

            title = str(
                row[col1]
            )


        # =================================================
        # 부가 정보
        # =================================================

        if (
            col_sub is not None
            and col_sub in df.columns
            and pd.notna(row.get(col_sub))
        ):

            sub_val = str(
                row.get(col_sub)
            )

        else:

            sub_val = "N/A"


        sub_info = (
            f"정보: {sub_val}"
        )


        # =================================================
        # 콘텐츠 고유 seed
        # =================================================

        seed_text = (
            f"{cat_key}|{title}|{sub_val}"
        )

        seed = _stable_seed(
            seed_text
        )


        # =================================================
        # 이상징후 프로필
        # =================================================

        profile = _select_profile(
            seed
        )


        # =================================================
        # 30일 데이터 생성
        # =================================================

        daily_data = generate_time_series(
            seed=seed,
            category=cat_key,
            profile=profile
        )


        # =================================================
        # 이상감지
        # =================================================

        metrics = engine.calculate_metrics(
            daily_data
        )


        if not metrics:

            continue


        # =================================================
        # 화면에 사용할 데이터
        # =================================================

        item = {

            "id": item_id,

            "category": cat_key,

            "category_name": cat_name,

            "title": title,

            "sub_info": sub_info,

            "daily_data": daily_data,

            "yt_views_inc": round(
                metrics.get(
                    "increase_rate",
                    0
                ) * 0.75,
                1
            ),

            "yt_comments_inc": round(
                metrics.get(
                    "increase_rate",
                    0
                ) * 0.68,
                1
            ),

            **metrics,
        }


        contents.append(
            item
        )


        item_id += 1


    return contents, item_id


# =========================================================
# ★★★ 이 함수가 total.py에서 import하는 함수 ★★★
# =========================================================

def load_all_contents():

    contents = []

    item_id = 1


    # =====================================================
    # CSV 설정
    # =====================================================

    categories = [

        # 노래
        (
            "music",
            "노래",
            "kpopidolsv3.csv",
            "Group",
            "Stage Name",
            "Company"
        ),

        # 드라마
        (
            "drama",
            "드라마",
            "kdrama.csv",
            "Name",
            None,
            "Original Network"
        ),

        # 웹툰
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
    # CSV 전체 분석
    # =====================================================

    for (
        cat_key,
        cat_name,
        csv_name,
        col1,
        col2,
        col_sub
    ) in categories:


        category_items, item_id = _load_category(

            cat_key=cat_key,

            cat_name=cat_name,

            csv_name=csv_name,

            col1=col1,

            col2=col2,

            col_sub=col_sub,

            start_id=item_id
        )


        contents.extend(
            category_items
        )


    # =====================================================
    # 취재 우선순위 정렬
    #
    # HIGH → MEDIUM → LOW
    # 그 안에서는 trend_score 높은 순
    # =====================================================

    signal_priority = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }


    contents.sort(

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


    return contents


# =========================================================
# 이 파일 단독 실행 테스트
# =========================================================

if __name__ == "__main__":

    items = load_all_contents()

    print()
    print(
        "================================"
    )

    print(
        f"전체 콘텐츠 분석 완료: {len(items)}개"
    )

    print(
        "================================"
    )


    for index, item in enumerate(
        items[:10],
        start=1
    ):

        print(
            index,
            item.get("category_name"),
            item.get("title"),
            item.get("signal"),
            item.get("trend_score"),
            item.get("increase_rate")
        )