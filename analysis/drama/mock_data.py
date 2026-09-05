import hashlib
import os
from urllib.parse import quote_plus, urlparse

import numpy as np
import pandas as pd

from analysis.drama.anomaly import TrendAnomalyEngine


# =========================================================
# PATH
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


# =========================================================
# ANOMALY ENGINE
# =========================================================

engine = TrendAnomalyEngine()


# =========================================================
# CSV PATH
# =========================================================

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


# =========================================================
# CSV READ
# =========================================================

def _read_csv(path):

    encodings = [

        "cp949",

        "utf-8-sig",

        "utf-8"
    ]


    for encoding in encodings:

        try:

            return pd.read_csv(
                path,
                encoding=encoding
            )

        except Exception:

            continue


    return None


# =========================================================
# SAFE TEXT
# =========================================================

def _clean_text(value):

    if value is None:

        return ""


    try:

        if pd.isna(value):

            return ""

    except Exception:

        pass


    return str(
        value
    ).strip()


# =========================================================
# STABLE SEED
# =========================================================

def _stable_seed(text):

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
# PROFILE
# =========================================================

def _select_profile(seed):
    """
    같은 콘텐츠는 항상 같은 프로필을 갖게 합니다.

    약:
    HIGH   40%
    MEDIUM 30%
    LOW    30%
    """

    bucket = (
        seed
        %
        10
    )


    if bucket <= 3:

        return "HIGH"


    if bucket <= 6:

        return "MEDIUM"


    return "LOW"


# =========================================================
# 30-DAY SIMULATION
# =========================================================

def generate_time_series(
    is_spike=False,
    seed=None,
    category="content",
    profile=None
):
    """
    CSV 콘텐츠 자체는 실제 데이터입니다.

    단, 30일 관심도 시계열은
    이상감지 알고리즘을 시연하기 위한
    재현 가능한 시뮬레이션 지수입니다.

    앞 23일 = 기준 구간
    뒤 7일  = 최근 구간
    """

    if seed is None:

        seed = 0


    rng = np.random.default_rng(
        seed
    )


    # 카테고리별 기본 관심도 지수
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


    # 기준 구간의 평소 변동성
    baseline_scale = max(
        base_level
        *
        0.22,

        12
    )


    baseline = rng.normal(

        loc=base_level,

        scale=baseline_scale,

        size=23
    )


    baseline = np.clip(

        baseline,

        base_level
        *
        0.35,

        None
    )


    if profile is None:

        profile = (

            "HIGH"

            if is_spike

            else "LOW"
        )


    # =====================================================
    # 최근 7일 패턴
    # =====================================================

    if profile == "HIGH":

        recent_center = (

            base_level

            *

            rng.uniform(
                2.15,
                2.65
            )
        )


        recent_scale = (

            base_level

            *
            0.15
        )


    elif profile == "MEDIUM":

        recent_center = (

            base_level

            *

            rng.uniform(
                1.38,
                1.55
            )
        )


        recent_scale = (

            base_level

            *
            0.12
        )


    else:

        recent_center = (

            base_level

            *

            rng.uniform(
                0.95,
                1.18
            )
        )


        recent_scale = (

            base_level

            *
            0.10
        )


    recent = rng.normal(

        loc=recent_center,

        scale=recent_scale,

        size=7
    )


    recent = np.clip(

        recent,

        base_level
        *
        0.35,

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


# =========================================================
# WEBTOON LINK SECURITY
# =========================================================

def _allowed_naver_webtoon_url(value):
    """
    CSV에 직접 URL이 있을 경우
    네이버웹툰 주소만 허용합니다.
    """

    url = _clean_text(
        value
    )


    if not url:

        return ""


    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return ""


    if parsed.scheme not in {

        "http",

        "https"

    }:

        return ""


    host = (
        parsed.netloc
        .lower()
        .split(":")[0]
    )


    allowed_hosts = {

        "comic.naver.com",

        "m.comic.naver.com"
    }


    if host not in allowed_hosts:

        return ""


    return url


# =========================================================
# WEBTOON EXTERNAL LINK
# =========================================================

def _build_webtoon_link(
    row,
    title
):
    """
    1순위:
        CSV URL

    2순위:
        titleId

    3순위:
        네이버 제목 검색
    """

    # =====================================================
    # URL 컬럼 찾기
    # =====================================================

    possible_url_columns = [

        "url",

        "URL",

        "link",

        "Link",

        "webtoon_url",

        "webtoonUrl",

        "detail_url",

        "href"
    ]


    for column in possible_url_columns:

        if column not in row.index:

            continue


        url = _allowed_naver_webtoon_url(
            row.get(
                column
            )
        )


        if url:

            return {

                "external_url":
                    url,

                "external_link_label":
                    "네이버웹툰에서 보기",

                "external_link_type":
                    "direct"
            }


    # =====================================================
    # titleId 컬럼 찾기
    # =====================================================

    possible_id_columns = [

        "titleId",

        "title_id",

        "titleid"
    ]


    for column in possible_id_columns:

        if column not in row.index:

            continue


        title_id = _clean_text(
            row.get(
                column
            )
        )


        if title_id:

            url = (

                "https://comic.naver.com/"
                "webtoon/list?titleId="
                +
                quote_plus(
                    title_id
                )
            )


            return {

                "external_url":
                    url,

                "external_link_label":
                    "네이버웹툰에서 보기",

                "external_link_type":
                    "direct"
            }


    # =====================================================
    # titleId / URL 없으면 제목 검색
    # =====================================================

    query = quote_plus(
        f"네이버웹툰 {title}"
    )


    search_url = (

        "https://search.naver.com/"
        "search.naver?query="
        +
        query
    )


    return {

        "external_url":
            search_url,

        "external_link_label":
            "웹툰 확인하기",

        "external_link_type":
            "search"
    }


# =========================================================
# CATEGORY EXTERNAL LINK
# =========================================================

def _build_external_link(
    category,
    row,
    title
):

    if category == "webtoon":

        return _build_webtoon_link(
            row,
            title
        )


    return {

        "external_url":
            "",

        "external_link_label":
            "",

        "external_link_type":
            ""
    }


# =========================================================
# ★ MAIN DATA LOADER
#
# total.py에서 이 함수를 import 합니다.
# =========================================================

def load_all_contents():

    contents = []

    item_id = 1


    # =====================================================
    # CATEGORY SETTINGS
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
    # CSV LOOP
    # =====================================================

    for (

        category_key,

        category_name,

        csv_name,

        primary_column,

        secondary_column,

        info_column

    ) in categories:


        # =================================================
        # CSV 위치
        # =================================================

        csv_path = _get_file_path(
            csv_name
        )


        if not csv_path:

            print(
                "[KCONTENT] CSV 없음:",
                csv_name
            )

            continue


        # =================================================
        # CSV 읽기
        # =================================================

        df = _read_csv(
            csv_path
        )


        if df is None:

            print(
                "[KCONTENT] CSV 읽기 실패:",
                csv_name
            )

            continue


        # =================================================
        # 필수 제목 컬럼 확인
        # =================================================

        if primary_column not in df.columns:

            print(
                "[KCONTENT] 제목 컬럼 없음:",
                csv_name,
                primary_column
            )

            continue


        # =================================================
        # 빈 제목 제거
        # =================================================

        df_clean = df.dropna(
            subset=[
                primary_column
            ]
        )


        # =================================================
        # 모든 콘텐츠 사용
        # =================================================

        for _, row in df_clean.iterrows():


            # =============================================
            # 제목
            # =============================================

            primary_value = _clean_text(
                row.get(
                    primary_column
                )
            )


            if not primary_value:

                continue


            secondary_value = ""


            if (
                secondary_column
                and
                secondary_column in df.columns
            ):

                secondary_value = _clean_text(
                    row.get(
                        secondary_column
                    )
                )


            if secondary_value:

                title = (
                    f"{primary_value}"
                    f" - "
                    f"{secondary_value}"
                )

            else:

                title = (
                    primary_value
                )


            # =============================================
            # 보조 정보
            # =============================================

            info_value = ""


            if info_column in df.columns:

                info_value = _clean_text(
                    row.get(
                        info_column
                    )
                )


            if not info_value:

                info_value = "N/A"


            sub_info = (
                f"정보: {info_value}"
            )


            # =============================================
            # 고정된 시뮬레이션 데이터 생성
            # =============================================

            seed = _stable_seed(
                f"{category_key}:{title}"
            )


            profile = _select_profile(
                seed
            )


            daily_data = generate_time_series(

                seed=seed,

                category=category_key,

                profile=profile
            )


            # =============================================
            # 이상감지
            # =============================================

            metrics = (
                engine.calculate_metrics(
                    daily_data
                )
            )


            if not metrics:

                continue


            # =============================================
            # 외부 링크
            # =============================================

            external_link = (
                _build_external_link(

                    category=category_key,

                    row=row,

                    title=title
                )
            )


            # =============================================
            # CONTENT OBJECT
            # =============================================

            item = {

                "id":
                    item_id,

                "category":
                    category_key,

                "category_name":
                    category_name,

                "title":
                    title,

                "sub_info":
                    sub_info,

                "daily_data":
                    daily_data,

                "data_source_note":
                    (
                        "CSV 콘텐츠 메타데이터 + "
                        "재현 가능한 30일 시뮬레이션 관심도 지수"
                    ),

                "trend_profile":
                    profile,

                **external_link,

                **metrics,
            }


            contents.append(
                item
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
            1
    }


    contents.sort(

        key=lambda item: (

            -signal_priority.get(
                item.get(
                    "signal"
                ),
                0
            ),

            -item.get(
                "trend_score",
                0
            ),

            -item.get(
                "anomaly_days",
                item.get(
                    "persistence_days",
                    0
                )
            ),

            -item.get(
                "z_score",
                0
            ),

            -item.get(
                "increase_rate",
                0
            ),

            item.get(
                "id",
                0
            )
        )
    )


    # =====================================================
    # DEBUG
    # =====================================================

    print(
        "[KCONTENT] 전체 콘텐츠:",
        len(
            contents
        )
    )


    print(
        "[KCONTENT] HIGH:",
        sum(
            1
            for item in contents
            if item.get(
                "signal"
            )
            ==
            "HIGH"
        )
    )


    print(
        "[KCONTENT] MEDIUM:",
        sum(
            1
            for item in contents
            if item.get(
                "signal"
            )
            ==
            "MEDIUM"
        )
    )


    print(
        "[KCONTENT] LOW:",
        sum(
            1
            for item in contents
            if item.get(
                "signal"
            )
            ==
            "LOW"
        )
    )


    return contents