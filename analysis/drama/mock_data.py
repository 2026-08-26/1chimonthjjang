import os
import random
import numpy as np
import pandas as pd
from anomaly import TrendAnomalyEngine

# 현재 파일 위치: 1chimonthjjang/analysis/drama
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 상위 폴더들을 탐색하여 최상위 루트(1chimonthjjang) 계산
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

engine = TrendAnomalyEngine()


def _get_file_path(filename):
    """CSV 파일의 위치를 다각도로 탐색하여 찾습니다."""
    candidate_paths = [
        # 1. 1chimonthjjang/data/raw/
        os.path.join(PROJECT_ROOT, "data", "raw", filename),
        # 2. 1chimonthjjang/data/
        os.path.join(PROJECT_ROOT, "data", filename),
        # 3. 1chimonthjjang/python/data/raw/
        os.path.join(PROJECT_ROOT, "python", "data", "raw", filename),
        # 4. 상대 경로 data/raw/
        os.path.join("data", "raw", filename),
        # 5. 상대 경로 data/
        os.path.join("data", filename),
        # 6. 현재 폴더
        os.path.join(BASE_DIR, filename),
    ]

    for path in candidate_paths:
        if os.path.exists(path):
            print(f"✅ CSV 파일 감지 성공: {path}")
            return path

    print(f"⚠️ [경고] {filename} 파일을 찾을 수 없습니다.")
    return None


def generate_time_series(is_spike=False):
    """30일 치 일별 검색량 시뮬레이션 데이터 생성"""
    base = np.random.normal(loc=100, scale=15, size=23)
    if is_spike:
        recent = np.random.normal(loc=320, scale=40, size=7)  # 최근 7일 급상승
    else:
        recent = np.random.normal(loc=110, scale=20, size=7)
    return np.concatenate([base, recent]).tolist()


def load_all_contents():
    contents = []
    item_id = 1

    # 1. 노래 (K-Pop)
    kpop_path = _get_file_path("kpopidolsv3.csv")
    if kpop_path:
        try:
            df = pd.read_csv(kpop_path, encoding="cp949")
        except Exception:
            df = pd.read_csv(kpop_path, encoding="utf-8")

        df_clean = df.dropna(subset=["Group", "Stage Name"]).head(15)
        for _, row in df_clean.iterrows():
            is_spike = random.random() < 0.4
            daily_data = generate_time_series(is_spike)
            metrics = engine.calculate_metrics(daily_data)

            contents.append(
                {
                    "id": item_id,
                    "category": "music",
                    "category_name": "노래",
                    "title": f"{row['Group']} - {row['Stage Name']}",
                    "sub_info": f"소속사: {row.get('Company', '기획사 정보없음')}",
                    "daily_data": daily_data,
                    "yt_views_inc": round(metrics["increase_rate"] * 0.75, 1),
                    "yt_comments_inc": round(
                        metrics["increase_rate"] * 0.68, 1
                    ),
                    **metrics,
                }
            )
            item_id += 1

    # 2. 드라마 (K-Drama)
    kdrama_path = _get_file_path("kdrama.csv")
    if kdrama_path:
        try:
            df = pd.read_csv(kdrama_path, encoding="cp949")
        except Exception:
            df = pd.read_csv(kdrama_path, encoding="utf-8")

        for _, row in df.head(15).iterrows():
            is_spike = random.random() < 0.4
            daily_data = generate_time_series(is_spike)
            metrics = engine.calculate_metrics(daily_data)

            contents.append(
                {
                    "id": item_id,
                    "category": "drama",
                    "category_name": "드라마",
                    "title": str(row["Name"]),
                    "sub_info": f"방송사: {row.get('Original Network', 'N/A')} | 장르: {row.get('Genre', 'N/A')}",
                    "daily_data": daily_data,
                    "yt_views_inc": round(metrics["increase_rate"] * 0.8, 1),
                    "yt_comments_inc": round(
                        metrics["increase_rate"] * 0.7, 1
                    ),
                    **metrics,
                }
            )
            item_id += 1

    # 3. 웹툰 (Naver)
    naver_path = _get_file_path("naver.csv")
    if naver_path:
        try:
            df = pd.read_csv(naver_path, encoding="cp949")
        except Exception:
            df = pd.read_csv(naver_path, encoding="utf-8")

        for _, row in df.head(15).iterrows():
            is_spike = random.random() < 0.4
            daily_data = generate_time_series(is_spike)
            metrics = engine.calculate_metrics(daily_data)

            contents.append(
                {
                    "id": item_id,
                    "category": "webtoon",
                    "category_name": "웹툰",
                    "title": str(row["title"]),
                    "sub_info": f"작가: {row.get('author', 'N/A')} | 장르: {row.get('genre', 'N/A')}",
                    "daily_data": daily_data,
                    "yt_views_inc": round(metrics["increase_rate"] * 0.6, 1),
                    "yt_comments_inc": round(
                        metrics["increase_rate"] * 0.5, 1
                    ),
                    **metrics,
                }
            )
            item_id += 1

    # 트렌드 점수 높은 순 정렬
    contents.sort(key=lambda x: x["trend_score"], reverse=True)
    return contents