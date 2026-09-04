import datetime
import json
import os
import random
from anomaly import TrendAnomalyEngine
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

engine = TrendAnomalyEngine()


def _get_file_path(filename):
    candidate_paths = [
        os.path.join(PROJECT_ROOT, "data", "raw", filename),
        os.path.join(PROJECT_ROOT, "data", filename),
        os.path.join("data", "raw", filename),
        os.path.join(BASE_DIR, filename),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            return path
    return None


def generate_time_series(is_spike=False):
    base = np.random.normal(loc=100, scale=15, size=23)
    if is_spike:
        recent = np.random.normal(loc=320, scale=40, size=7)
    else:
        recent = np.random.normal(loc=110, scale=20, size=7)
    return np.concatenate([base, recent]).tolist()


def load_all_contents():
    contents = []
    item_id = 1

    categories = [
        ("music", "노래", "kpopidolsv3.csv", "Group", "Stage Name", "Company"),
        ("drama", "드라마", "kdrama.csv", "Name", None, "Original Network"),
        ("webtoon", "웹툰", "naver.csv", "title", None, "author"),
    ]

    for cat_key, cat_name, csv_name, col1, col2, col_sub in categories:
        csv_path = _get_file_path(csv_name)
        if not csv_path:
            continue

        try:
            df = pd.read_csv(csv_path, encoding="cp949")
        except Exception:
            try:
                df = pd.read_csv(csv_path, encoding="utf-8")
            except Exception:
                continue

        df_clean = df.dropna(subset=[col1]).head(15)
        for _, row in df_clean.iterrows():
            if col2 and pd.notna(row.get(col2)):
                title = f"{row[col1]} - {row[col2]}"
            else:
                title = str(row[col1])

            sub_val = str(row.get(col_sub, "N/A"))
            sub_info = f"정보: {sub_val}"

            is_spike = random.random() < 0.4
            daily_data = generate_time_series(is_spike)
            metrics = engine.calculate_metrics(daily_data)

            contents.append(
                {
                    "id": item_id,
                    "category": cat_key,
                    "category_name": cat_name,
                    "title": title,
                    "sub_info": sub_info,
                    "daily_data": daily_data,
                    "yt_views_inc": round(metrics["increase_rate"] * 0.75, 1),
                    "yt_comments_inc": round(
                        metrics["increase_rate"] * 0.68, 1
                    ),
                    **metrics,
                }
            )
            item_id += 1

    contents.sort(key=lambda x: x["trend_score"], reverse=True)
    return contents