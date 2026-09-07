import hashlib
import os
from urllib.parse import quote_plus, urlparse

import numpy as np
import pandas as pd

from analysis.drama.anomaly import TrendAnomalyEngine


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(
    os.path.join(
        BASE_DIR,
        "..",
        ".."
    )
)

engine = TrendAnomalyEngine()


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


def _stable_seed(text):
    """같은 콘텐츠는 새로고침해도 같은 결과가 나오도록 고정 seed 생성."""

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return int(
        digest[:8],
        16
    )


def _select_profile(seed):
    """
    이상감지 데모용 프로필 분포.

    전체 콘텐츠 대부분은 일반 범위(LOW)에 두고,
    일부만 MEDIUM/HIGH 후보가 되도록 구성합니다.

    - HIGH   약 8%
    - MEDIUM 약 20%
    - LOW    약 72%

    같은 콘텐츠는 stable seed를 사용하므로
    새로고침해도 같은 프로필을 유지합니다.
    """

    bucket = seed % 100

    if bucket < 8:
        return "HIGH"

    if bucket < 28:
        return "MEDIUM"

    return "LOW"


def generate_time_series(
    is_spike=False,
    seed=None,
    category="content",
    profile=None
):
    """
    재현 가능한 30일 관심도 지수 생성.

    실제 네이버/구글 검색량이 아니라
    이상감지 흐름 시연용 시뮬레이션 지수입니다.
    """

    if seed is None:
        seed = 0

    rng = np.random.default_rng(
        seed
    )

    base_level = {
        "music": 120,
        "drama": 100,
        "webtoon": 85,
    }.get(
        category,
        100
    )

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

    if profile is None:
        profile = (
            "HIGH"
            if is_spike
            else "LOW"
        )

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


def _read_csv(csv_path):
    for encoding in (
        "cp949",
        "utf-8-sig",
        "utf-8"
    ):
        try:
            return pd.read_csv(
                csv_path,
                encoding=encoding
            )

        except UnicodeDecodeError:
            continue

        except Exception:
            continue

    return None


def _clean_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value).strip()


def _allowed_naver_webtoon_url(value):
    """
    CSV에 URL이 있을 때
    네이버웹툰 계열 주소만 외부 링크로 사용.
    """

    url = _clean_text(value)

    if not url:
        return ""

    try:
        parsed = urlparse(url)
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

    if host not in {
        "comic.naver.com",
        "m.comic.naver.com"
    }:
        return ""

    return url


def _webtoon_external_link(
    row,
    title
):
    """
    웹툰 제목별 외부 링크.

    1. CSV URL이 있으면 직접 작품 페이지
    2. titleId가 있으면 작품 페이지 생성
    3. 없으면 제목별 네이버 검색
    """

    for column in (
        "url",
        "URL",
        "link",
        "Link",
        "webtoon_url",
        "webtoonUrl",
        "detail_url",
        "href"
    ):
        if column not in row.index:
            continue

        direct_url = (
            _allowed_naver_webtoon_url(
                row.get(column)
            )
        )

        if direct_url:
            return {
                "external_url":
                    direct_url,
                "external_link_label":
                    "네이버웹툰에서 보기",
                "external_link_type":
                    "direct"
            }

    for column in (
        "titleId",
        "title_id",
        "titleid"
    ):
        if column not in row.index:
            continue

        title_id = _clean_text(
            row.get(column)
        )

        if title_id:
            return {
                "external_url":
                    (
                        "https://comic.naver.com/"
                        "webtoon/list?titleId="
                        f"{quote_plus(title_id)}"
                    ),
                "external_link_label":
                    "네이버웹툰에서 보기",
                "external_link_type":
                    "direct"
            }

    # URL/titleId가 없을 때 제목마다 다른 검색 주소 생성
    query = quote_plus(
        f"네이버웹툰 {title}"
    )

    return {
        "external_url":
            (
                "https://search.naver.com/"
                f"search.naver?query={query}"
            ),
        "external_link_label":
            "웹툰 확인하기",
        "external_link_type":
            "search"
    }


def _external_link_info(
    category,
    row,
    title
):
    if category == "webtoon":
        return _webtoon_external_link(
            row,
            title
        )

    return {
        "external_url": "",
        "external_link_label": "",
        "external_link_type": ""
    }


def load_all_contents():
    contents = []
    item_id = 1

    categories = [
        (
            "music",
            "아이돌",
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

        df = _read_csv(
            csv_path
        )

        if df is None:
            continue

        if col1 not in df.columns:
            continue

        # CSV 전체 후보 사용
        df_clean = df.dropna(
            subset=[
                col1
            ]
        )

        for _, row in df_clean.iterrows():

            primary = _clean_text(
                row.get(col1)
            )

            if not primary:
                continue

            if (
                col2
                and col2 in df.columns
            ):
                secondary = _clean_text(
                    row.get(col2)
                )
            else:
                secondary = ""

            if secondary:
                title = (
                    f"{primary} - {secondary}"
                )
            else:
                title = primary

            if col_sub in df.columns:
                sub_value = _clean_text(
                    row.get(col_sub)
                )
            else:
                sub_value = ""

            if not sub_value:
                sub_value = "N/A"

            sub_info = (
                f"정보: {sub_value}"
            )

            seed = _stable_seed(
                f"{cat_key}:{title}"
            )

            profile = _select_profile(
                seed
            )

            daily_data = generate_time_series(
                seed=seed,
                category=cat_key,
                profile=profile
            )

            metrics = (
                engine.calculate_metrics(
                    daily_data
                )
            )

            if not metrics:
                continue

            external_link = (
                _external_link_info(
                    category=cat_key,
                    row=row,
                    title=title
                )
            )

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
            )

            item_id += 1

    signal_priority = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1
    }

    contents.sort(
        key=lambda item: (
            -signal_priority.get(
                item.get("signal"),
                0
            ),
            -item.get(
                "trend_score",
                0
            ),
            -item.get(
                "anomaly_days",
                0
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

    return contents
