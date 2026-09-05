import hashlib
import os

import numpy as np
import pandas as pd

from analysis.drama.anomaly import TrendAnomalyEngine


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


# ==========================================
# CSV 파일 위치 탐색
# ==========================================
def _get_file_path(filename):

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

        if os.path.exists(path):
            return path

    return None


# ==========================================
# 콘텐츠마다 고정된 Seed 생성
# ==========================================
def _stable_seed(text):
    """
    같은 콘텐츠는 항상 같은 seed를 사용합니다.

    따라서 새로고침하거나 서버를 다시 실행해도
    같은 콘텐츠의 트렌드 결과가 바뀌지 않습니다.
    """

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return int(
        digest[:8],
        16
    )


# ==========================================
# HIGH / MEDIUM / LOW 데이터 프로필 선택
# ==========================================
def _select_profile(seed):
    """
    학습용 미니프로젝트에서
    HIGH / MEDIUM / LOW 데이터가
    적절하게 섞이도록 합니다.

    random.random() 대신 고정 seed를 사용하기 때문에
    실행할 때마다 결과가 바뀌지 않습니다.
    """

    bucket = seed % 10

    # 약 40%
    if bucket <= 3:
        return "HIGH"

    # 약 30%
    if bucket <= 6:
        return "MEDIUM"

    # 약 30%
    return "LOW"


# ==========================================
# 30일 트렌드 시계열 생성
# ==========================================
def generate_time_series(
    is_spike=False,
    seed=None,
    category="content",
    profile=None
):
    """
    30일 트렌드 시계열 데이터를 생성합니다.

    이전 코드와의 호환성을 위해
    generate_time_series(is_spike) 호출도 가능합니다.

    실제 Google Trends 등의 실측 데이터가 아니라
    미니프로젝트용 재현 가능한 시뮬레이션 데이터입니다.
    """

    if seed is None:
        seed = 0

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

    # 이전 23일 데이터
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

    # 기존 방식과 호환
    if profile is None:

        if is_spike:
            profile = "HIGH"

        else:
            profile = "LOW"

    # 최근 7일 데이터 생성
    if profile == "HIGH":

        recent_center = (
            base_level
            * rng.uniform(
                2.15,
                2.65
            )
        )

        recent_scale = (
            base_level
            * 0.15
        )

    elif profile == "MEDIUM":

        recent_center = (
            base_level
            * rng.uniform(
                1.38,
                1.55
            )
        )

        recent_scale = (
            base_level
            * 0.12
        )

    else:

        recent_center = (
            base_level
            * rng.uniform(
                0.95,
                1.18
            )
        )

        recent_scale = (
            base_level
            * 0.10
        )

    recent = rng.normal(
        loc=recent_center,
        scale=recent_scale,
        size=7
    )

    recent = np.clip(
        recent,
        base_level * 0.35,
        None
    )

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


# ==========================================
# 카테고리별 보조 지표
# ==========================================
def _build_category_metrics(
    category,
    increase_rate
):
    """
    콘텐츠 종류에 따라
    화면에 표시할 보조 지표 이름을 다르게 합니다.

    실제 외부 API 측정값은 아니며
    관심도 변화율을 활용한 데모용 파생 지표입니다.
    """

    # K-POP / 노래
    if category == "music":

        return {
            "secondary_metric_name":
                "YouTube 조회수 추정 증가율",

            "secondary_metric_value":
                round(
                    increase_rate * 0.75,
                    1
                ),

            "reaction_metric_name":
                "YouTube 댓글/반응 추정 증가율",

            "reaction_metric_value":
                round(
                    increase_rate * 0.68,
                    1
                ),
        }

    # 드라마
    if category == "drama":

        return {
            "secondary_metric_name":
                "OTT/영상 화제성 추정 증가율",

            "secondary_metric_value":
                round(
                    increase_rate * 0.72,
                    1
                ),

            "reaction_metric_name":
                "커뮤니티 반응 추정 증가율",

            "reaction_metric_value":
                round(
                    increase_rate * 0.63,
                    1
                ),
        }

    # 웹툰
    return {
        "secondary_metric_name":
            "작품 관심도 추정 증가율",

        "secondary_metric_value":
            round(
                increase_rate * 0.70,
                1
            ),

        "reaction_metric_name":
            "댓글/평점 반응 추정 증가율",

        "reaction_metric_value":
            round(
                increase_rate * 0.60,
                1
            ),
    }


# ==========================================
# 전체 K-콘텐츠 로딩
# ==========================================
def load_all_contents():

    contents = []

    item_id = 1

    # 기존 CSV 연결 구조 그대로 유지
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

    for (
        cat_key,
        cat_name,
        csv_name,
        col1,
        col2,
        col_sub
    ) in categories:

        csv_path = _get_file_path(
            csv_name
        )

        if not csv_path:
            continue

        # ------------------------------
        # CSV Encoding 처리
        # ------------------------------
        try:

            df = pd.read_csv(
                csv_path,
                encoding="cp949"
            )

        except Exception:

            try:

                df = pd.read_csv(
                    csv_path,
                    encoding="utf-8"
                )

            except Exception:

                continue

        # 필수 컬럼이 없는 경우
        if col1 not in df.columns:
            continue

        # 기존처럼 최대 15개 사용
        df_clean = (
            df
            .dropna(
                subset=[col1]
            )
            .head(15)
        )

        for _, row in df_clean.iterrows():

            # --------------------------
            # 콘텐츠 제목
            # --------------------------
            if (
                col2
                and col2 in df.columns
                and pd.notna(
                    row.get(col2)
                )
            ):

                title = (
                    f"{row[col1]} - "
                    f"{row[col2]}"
                )

            else:

                title = str(
                    row[col1]
                )

            # --------------------------
            # 부가 정보
            # --------------------------
            if col_sub in df.columns:

                sub_val = row.get(
                    col_sub,
                    "N/A"
                )

            else:

                sub_val = "N/A"

            if pd.isna(sub_val):
                sub_val = "N/A"

            else:
                sub_val = str(
                    sub_val
                )

            sub_info = (
                f"정보: {sub_val}"
            )

            # --------------------------
            # 콘텐츠마다 고정 Seed
            # --------------------------
            seed = _stable_seed(
                f"{cat_key}:{title}"
            )

            profile = _select_profile(
                seed
            )

            # --------------------------
            # 트렌드 데이터 생성
            # --------------------------
            daily_data = (
                generate_time_series(
                    seed=seed,
                    category=cat_key,
                    profile=profile,
                )
            )

            # --------------------------
            # 이상감지
            # --------------------------
            metrics = (
                engine.calculate_metrics(
                    daily_data
                )
            )

            if not metrics:
                continue

            # --------------------------
            # 카테고리별 보조 지표
            # --------------------------
            category_metrics = (
                _build_category_metrics(
                    cat_key,
                    metrics[
                        "increase_rate"
                    ]
                )
            )

            contents.append(
                {
                    # -------------------
                    # 기본 정보
                    # -------------------
                    "id": item_id,

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

                    # -------------------
                    # 기존 코드 호환용
                    # -------------------
                    "yt_views_inc":
                        category_metrics[
                            "secondary_metric_value"
                        ],

                    "yt_comments_inc":
                        category_metrics[
                            "reaction_metric_value"
                        ],

                    # -------------------
                    # 카테고리별 추가 지표
                    # -------------------
                    **category_metrics,

                    # -------------------
                    # 데이터 설명
                    # -------------------
                    "data_source_note":
                        "CSV 콘텐츠 정보 + "
                        "재현 가능한 시뮬레이션 트렌드",

                    "trend_profile":
                        profile,

                    # -------------------
                    # 이상감지 결과
                    # -------------------
                    **metrics,
                }
            )

            item_id += 1

    # ----------------------------------
    # 트렌드 점수 높은 순 정렬
    # ----------------------------------
    # 점수가 같은 경우 id 순서로 정렬해서
    # 결과 순서가 매번 같도록 함
    contents.sort(
        key=lambda x: (
            -x["trend_score"],
            x["id"]
        )
    )

    return contents