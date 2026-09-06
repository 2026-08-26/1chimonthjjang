from collections import Counter
from pathlib import Path
import hashlib
from urllib.parse import quote

import pandas as pd
from flask import Blueprint, render_template

from analysis.drama.mock_data import load_all_contents, generate_time_series
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
# PATH
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

STOCK_SIGNAL_PATH = (
    PROJECT_ROOT
    / "result"
    / "stock"
    / "all_stock_signals.csv"
)

BASEBALL_FILES = {
    "기온": PROJECT_ROOT / "data" / "processed" / "temp_signal.csv",
    "습도": PROJECT_ROOT / "data" / "processed" / "humidity_signal.csv",
    "강수": PROJECT_ROOT / "data" / "processed" / "rain_signal.csv",
}


# =========================================================
# COMMON HELPERS
# =========================================================

def _safe_float(value, default=0.0):
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _truthy(value):
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value != 0

    text = str(value).strip().lower()

    return text not in {
        "",
        "0",
        "false",
        "none",
        "nan",
        "no",
    }


def _first_value(row, keys, fallback=""):
    for key in keys:
        if key not in row:
            continue

        value = row.get(key)

        if value is None:
            continue

        text = str(value).strip()

        if text and text.lower() not in {"nan", "none"}:
            return text

    return fallback


def _short_label(value, max_length=24):
    text = str(value or "").strip()

    if len(text) <= max_length:
        return text

    return text[: max_length - 1].rstrip() + "…"


def _stable_content_seed(category, title):
    """mock_data.py와 같은 방식으로 콘텐츠별 고정 seed를 만듭니다."""
    key = f"{category}:{title}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _ensure_kcontent_daily_data(item):
    """
    K콘텐츠 메인 선그래프용 30일 시계열을 보장합니다.

    우선 load_all_contents()가 만든 daily_data를 사용하고,
    누락되었거나 30개 미만이면 같은 stable seed/profile로
    generate_time_series()를 다시 호출해 동일한 전처리 흐름으로 복구합니다.
    """
    raw = item.get("daily_data") or []
    clean = []

    for value in raw:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue

        if pd.isna(number):
            continue

        clean.append(round(number, 1))

    if len(clean) >= 30:
        return clean[:30]

    category = str(item.get("category", "content") or "content").strip()
    title = str(item.get("title", "콘텐츠") or "콘텐츠").strip()
    profile = str(
        item.get("trend_profile")
        or item.get("signal")
        or "LOW"
    ).upper()

    if profile not in {"HIGH", "MEDIUM", "LOW"}:
        profile = "LOW"

    try:
        regenerated = generate_time_series(
            seed=_stable_content_seed(category, title),
            category=category,
            profile=profile,
        )
    except Exception as e:
        print(
            "[HOME] K콘텐츠 30일 시계열 재생성 실패:",
            title,
            type(e).__name__,
        )
        return clean[:30]

    return [
        round(_safe_float(value), 1)
        for value in regenerated[:30]
    ]


def _flow_item(label, value, detail=""):
    return {
        "label": _short_label(label),
        "full_label": str(label or "").strip(),
        "value": round(_safe_float(value), 2),
        "detail": str(detail or "").strip(),
    }


def _breakdown_with_width(rows):
    clean = []

    for row in rows:
        name = str(row.get("name", "")).strip()
        count = _safe_int(row.get("count"), 0)

        if not name or count <= 0:
            continue

        clean.append({
            "name": name,
            "count": count,
        })

    clean.sort(
        key=lambda item: item["count"],
        reverse=True,
    )

    max_count = max(
        (item["count"] for item in clean),
        default=1,
    )

    for item in clean:
        item["width"] = round(
            item["count"] / max_count * 100,
            1,
        )

    return clean[:8]


# =========================================================
# K-CONTENT HOME TOP 5
# =========================================================

def load_kcontent_home_signals(limit=5):
    try:
        all_items = load_all_contents()
    except Exception as e:
        print(
            "[HOME] K콘텐츠 로딩 실패:",
            type(e).__name__,
        )
        return []

    signal_priority = {
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }

    sorted_items = sorted(
        all_items,
        key=lambda item: (
            signal_priority.get(item.get("signal"), 0),
            _safe_float(item.get("trend_score")),
            _safe_float(item.get("z_score")),
            _safe_float(item.get("increase_rate")),
        ),
        reverse=True,
    )

    result = []

    for rank, item in enumerate(
        sorted_items[:limit],
        start=1,
    ):
        item_id = item.get("id")
        z_score = _safe_float(item.get("z_score"))

        result.append({
            "category": "K콘텐츠",
            "region": item.get("category_name", "콘텐츠"),
            "signal_name": item.get("title", "콘텐츠"),
            "score": round(z_score, 2),
            "severity": item.get("signal", "LOW"),
            "signal_type": item.get("category", "content"),
            "detail_url": f"/detail/{item_id}",
            "item_id": item_id,
            "category_rank": rank,
            "trend_score": item.get("trend_score", 0),
            "z_score": round(z_score, 2),
            "increase_rate": item.get("increase_rate", 0),
            "stock_market": "",
            "stock_code": "",
            "stock_date": "",
        })

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
# STOCK DATA
# =========================================================

def _load_stock_signal_dataframe():
    path = STOCK_SIGNAL_PATH

    if not path.exists():
        print(
            "[HOME] 주식 시그널 파일 없음:",
            path,
        )
        return pd.DataFrame()

    try:
        header = pd.read_csv(
            path,
            nrows=0,
        )

        dtype_map = {}

        for code_column in ("code", "종목코드"):
            if code_column in header.columns:
                dtype_map[code_column] = str

        return pd.read_csv(
            path,
            dtype=dtype_map,
        ).fillna("")

    except Exception as e:
        print(
            "[HOME] 주식 데이터 로딩 실패:",
            type(e).__name__,
        )
        return pd.DataFrame()


def _latest_stock_rows():
    signals = _load_stock_signal_dataframe()

    if signals.empty:
        return pd.DataFrame(), ""

    if "date" not in signals.columns or "market" not in signals.columns:
        return pd.DataFrame(), ""

    signals = signals.copy()
    signals["date"] = signals["date"].astype(str).str.strip()

    dates = [
        value
        for value in signals["date"].tolist()
        if value
    ]

    if not dates:
        return pd.DataFrame(), ""

    latest_date = max(dates)

    selected = signals[
        signals["date"] == latest_date
    ].copy()

    if selected.empty:
        return selected, latest_date

    sort_columns = []
    ascending = []

    if "signal_count" in selected.columns:
        selected["_signal_count_sort"] = pd.to_numeric(
            selected["signal_count"],
            errors="coerce",
        ).fillna(0)
        sort_columns.append("_signal_count_sort")
        ascending.append(False)

    if "score" in selected.columns:
        selected["_score_sort"] = pd.to_numeric(
            selected["score"],
            errors="coerce",
        ).fillna(0)
        sort_columns.append("_score_sort")
        ascending.append(False)

    if sort_columns:
        selected = selected.sort_values(
            sort_columns,
            ascending=ascending,
        )

    return selected, latest_date


def load_stock_home_signals(limit=5):
    selected, _ = _latest_stock_rows()

    if selected.empty:
        return []

    if "code" in selected.columns:
        code_column = "code"
    elif "종목코드" in selected.columns:
        code_column = "종목코드"
    else:
        return []

    result = []

    for rank, row in enumerate(
        selected.head(limit).to_dict("records"),
        start=1,
    ):
        code = str(row.get(code_column, "")).strip()
        market = str(row.get("market", "")).strip()
        date = str(row.get("date", "")).strip()

        if not (code and market and date):
            continue

        stock_name = _first_value(
            row,
            (
                "name",
                "종목명",
                "stock_name",
                "company_name",
                "company",
                "종목",
            ),
            fallback=code,
        )

        signal_labels = []

        for key, title in (
            ("volume_signal", "거래량 급증"),
            ("price_signal", "5거래일 가격 급변"),
            ("concentration_signal", "거래대금 쏠림"),
        ):
            if _truthy(row.get(key)):
                signal_labels.append(title)

        signal_type = (
            " · ".join(signal_labels)
            if signal_labels
            else "주식 이상신호"
        )

        score = round(
            _safe_float(row.get("score")),
            2,
        )

        severity = _first_value(
            row,
            (
                "severity",
                "signal",
                "signal_level",
            ),
            fallback="",
        ).upper()

        if severity not in {"HIGH", "MEDIUM", "LOW"}:
            signal_count = _safe_int(row.get("signal_count"))

            if signal_count >= 3:
                severity = "HIGH"
            elif signal_count >= 2:
                severity = "MEDIUM"
            else:
                severity = "LOW"

        result.append({
            "category": "주식",
            "region": market,
            "signal_name": (
                f"{stock_name} · {signal_type}"
                if signal_labels
                else stock_name
            ),
            "score": score,
            "severity": severity,
            "signal_type": signal_type,
            "detail_url": (
                f"/stock/{quote(market, safe='')}/"
                f"{quote(code, safe='')}/"
                f"{quote(date, safe='')}"
            ),
            "item_id": "",
            "category_rank": rank,
            "stock_market": market,
            "stock_code": code,
            "stock_date": date,
        })

    return result


# =========================================================
# CATEGORY FLOW - SOCIAL / ECONOMY
# =========================================================

def _flow_from_dashboard_signals(items, category):
    rows = [
        item
        for item in items
        if item.get("category") == category
    ]

    rows = sorted(
        rows,
        key=lambda item: _safe_float(item.get("score")),
        reverse=True,
    )

    series = []

    for item in rows[:10]:
        series.append(
            _flow_item(
                item.get("signal_name", "시그널"),
                item.get("score", 0),
                item.get("region", ""),
            )
        )

    counter = Counter()

    for item in rows:
        group_name = str(
            item.get("signal_type")
            or item.get("signal_name")
            or "기타"
        ).strip()

        counter[group_name] += 1

    breakdown = _breakdown_with_width([
        {
            "name": name,
            "count": count,
        }
        for name, count in counter.items()
    ])

    return series, breakdown


# =========================================================
# CATEGORY FLOW - STOCK
# =========================================================

def _stock_flow():
    selected, latest_date = _latest_stock_rows()

    if selected.empty:
        return [], [], ""

    if "code" in selected.columns:
        code_column = "code"
    elif "종목코드" in selected.columns:
        code_column = "종목코드"
    else:
        code_column = None

    series = []

    for row in selected.head(10).to_dict("records"):
        code = (
            str(row.get(code_column, "")).strip()
            if code_column
            else ""
        )

        name = _first_value(
            row,
            (
                "name",
                "종목명",
                "stock_name",
                "company_name",
                "company",
                "종목",
            ),
            fallback=code or "종목",
        )

        market = str(row.get("market", "")).strip()

        series.append(
            _flow_item(
                name,
                row.get("score", 0),
                market,
            )
        )

    breakdown_rows = []

    for key, title in (
        ("volume_signal", "거래량 급증"),
        ("price_signal", "5거래일 가격 급변"),
        ("concentration_signal", "거래대금 쏠림"),
    ):
        if key not in selected.columns:
            continue

        count = sum(
            1
            for value in selected[key].tolist()
            if _truthy(value)
        )

        breakdown_rows.append({
            "name": title,
            "count": count,
        })

    breakdown = _breakdown_with_width(
        breakdown_rows
    )

    return series, breakdown, latest_date


# =========================================================
# CATEGORY FLOW - K-CONTENT
# =========================================================

def _kcontent_flow(all_items=None):
    """
    K콘텐츠 메인 영역은 "시간 흐름"이 아니라
    취재 후보 간 이상도 비교이므로 Z-score TOP 10 막대그래프로 보여줍니다.

    - 탐지 결과가 HIGH 또는 MEDIUM인 콘텐츠만 후보군에 포함
    - 후보군을 Z-score 기준으로 정렬
    - 그래프에는 TOP 10 표시
    - 오른쪽에는 TOP 10의 콘텐츠 유형 구성을 표시
    - 전체 HIGH/MEDIUM 후보 수는 별도 메타 정보로 노출

    이렇게 하면 전체 CSV 개수와 TOP 10 시각화가 섞이지 않습니다.
    """

    if all_items is None:
        try:
            all_items = load_all_contents()
        except Exception:
            all_items = []

    candidates = [
        item
        for item in all_items
        if str(item.get("signal", "")).upper() in {"HIGH", "MEDIUM"}
    ]

    sorted_items = sorted(
        candidates,
        key=lambda item: (
            _safe_float(item.get("z_score")),
            _safe_float(item.get("anomaly_days")),
            _safe_float(item.get("increase_rate")),
            _safe_float(item.get("trend_score")),
        ),
        reverse=True,
    )

    top_items = sorted_items[:10]

    series = []

    for item in top_items:
        # 전처리된 30일 관심도 지수를 그대로 사용하되,
        # 누락 시 동일 seed/profile로 안전하게 재생성합니다.
        daily_data = _ensure_kcontent_daily_data(item)

        series.append({
            "label": _short_label(item.get("title", "콘텐츠")),
            "full_label": str(item.get("title", "콘텐츠")).strip(),
            "value": round(_safe_float(item.get("z_score")), 2),
            "detail": (
                f"{item.get('category_name', 'K콘텐츠')} · "
                f"{item.get('signal', 'LOW')} · "
                f"증감률 {_safe_float(item.get('increase_rate')):+.1f}% · "
                f"이상 지속 {_safe_int(item.get('anomaly_days'))}/7일"
            ),
            "item_id": item.get("id"),
            "category_name": item.get("category_name", "K콘텐츠"),
            "signal": item.get("signal", "LOW"),
            "daily_data": daily_data,
            "baseline_avg": round(_safe_float(item.get("baseline_avg", item.get("past_30_avg", 0))), 1),
            "recent_7_avg": round(_safe_float(item.get("recent_7_avg", 0)), 1),
            "increase_rate": round(_safe_float(item.get("increase_rate", 0)), 1),
            "z_score": round(_safe_float(item.get("z_score", 0)), 2),
            "anomaly_days": _safe_int(item.get("anomaly_days", item.get("persistence_days", 0))),
            "baseline_std": round(_safe_float(item.get("baseline_std", 0)), 2),
            "anomaly_threshold": round(_safe_float(item.get("anomaly_threshold", 0)), 1),
            "data_source_note": str(item.get("data_source_note", "")).strip(),
        })

    # 오른쪽 패널은 전체 2,000여 건을 그대로 막대로 보여주지 않고,
    # 현재 그래프에 표시된 TOP 10의 유형 구성을 보여줍니다.
    # 전체 HIGH/MEDIUM 후보 수는 side_meta로 별도 표시합니다.
    top_counter = Counter(
        str(item.get("category_name", "기타"))
        for item in top_items
    )

    breakdown = _breakdown_with_width([
        {
            "name": name,
            "count": count,
        }
        for name, count in top_counter.items()
    ])

    return {
        "series": series,
        "breakdown": breakdown,
        "candidate_total": len(candidates),
        "all_total": len(all_items),
    }


# =========================================================
# CATEGORY FLOW - BASEBALL
# =========================================================

def _baseball_flow():
    candidates = []

    for weather_type, path in BASEBALL_FILES.items():
        if not path.exists():
            continue

        try:
            df = pd.read_csv(
                path,
                encoding="utf-8-sig",
            ).fillna("")
        except Exception as e:
            print(
                f"[HOME] 야구 {weather_type} 데이터 로딩 실패:",
                type(e).__name__,
            )
            continue

        if "signal_score" not in df.columns:
            continue

        score_series = pd.to_numeric(
            df["signal_score"],
            errors="coerce",
        ).fillna(0).abs()

        working = df.copy()
        working["_flow_score"] = score_series
        working["_weather_type"] = weather_type

        for row in working.to_dict("records"):
            player = _first_value(
                row,
                (
                    "player_name",
                    "선수",
                    "name",
                ),
                fallback="선수",
            )

            condition = _first_value(
                row,
                (
                    "temp_group",
                    "humidity_group",
                    "rain_group",
                    "weather_group",
                ),
                fallback=weather_type,
            )

            candidates.append({
                "label": f"{player} · {condition}",
                "detail": weather_type,
                "value": _safe_float(row.get("_flow_score")),
                "weather_type": weather_type,
            })

    candidates.sort(
        key=lambda item: item["value"],
        reverse=True,
    )

    series = [
        _flow_item(
            item["label"],
            item["value"],
            item["detail"],
        )
        for item in candidates[:10]
    ]

    # 임의 임계값을 만들지 않고 "상위 30개 후보 구성"을 보여줍니다.
    top_for_breakdown = candidates[:30]
    counter = Counter(
        item["weather_type"]
        for item in top_for_breakdown
    )

    breakdown = _breakdown_with_width([
        {
            "name": name,
            "count": count,
        }
        for name, count in counter.items()
    ])

    return series, breakdown


# =========================================================
# BUILD CATEGORY FLOW PAYLOAD
# =========================================================

def build_category_flow(base_top_signals):
    social_series, social_breakdown = _flow_from_dashboard_signals(
        base_top_signals,
        "사회",
    )

    economy_series, economy_breakdown = _flow_from_dashboard_signals(
        base_top_signals,
        "경제",
    )

    stock_series, stock_breakdown, stock_date = _stock_flow()

    try:
        kcontent_items = load_all_contents()
    except Exception as e:
        print(
            "[HOME] K콘텐츠 흐름 로딩 실패:",
            type(e).__name__,
        )
        kcontent_items = []

    content_flow = _kcontent_flow(
        kcontent_items
    )

    content_series = content_flow["series"]
    content_breakdown = content_flow["breakdown"]
    content_candidate_total = content_flow["candidate_total"]
    content_all_total = content_flow["all_total"]

    baseball_series, baseball_breakdown = _baseball_flow()

    return {
        "social": {
            "name": "사회",
            "chart_title": "사회 이상신호 프로필",
            "description": (
                "인구 이동·자연증감에서 포착된 메인 취재 후보를 "
                "Signal Score 순으로 확인합니다."
            ),
            "unit": "Signal Score",
            "side_title": "탐지 유형별 분포",
            "note": "사회 메인 탐지 후보 기준",
            "series": social_series,
            "breakdown": social_breakdown,
        },
        "economy": {
            "name": "경제",
            "chart_title": "경제 이상신호 프로필",
            "description": (
                "주택가격·거래량·금리에서 포착된 메인 취재 후보를 "
                "Signal Score 순으로 확인합니다."
            ),
            "unit": "Signal Score",
            "side_title": "탐지 유형별 분포",
            "note": "경제 메인 탐지 후보 기준",
            "series": economy_series,
            "breakdown": economy_breakdown,
        },
        "stock": {
            "name": "주식",
            "chart_title": "최신 거래일 상위 주식 시그널",
            "description": (
                "가격·거래량·거래대금 이상신호가 포착된 종목을 "
                "최신 거래일 기준으로 확인합니다."
            ),
            "unit": "Stock Score",
            "side_title": "탐지 유형별 분포",
            "note": (
                f"{stock_date} 최신 거래일 기준"
                if stock_date
                else "주식 분석 데이터 기준"
            ),
            "series": stock_series,
            "breakdown": stock_breakdown,
        },
        "content": {
            "name": "K콘텐츠",
            "chart_type": "bar",
            "chart_title": "K콘텐츠 Z-score TOP 10",
            "chart_heading": "이상도 상위 10개 콘텐츠",
            "description": (
                "막대그래프는 전처리 후 HIGH·MEDIUM 후보의 Z-score TOP10을 비교하고, "
                "선그래프는 선택한 콘텐츠의 기준 23일·최근 7일 관심도 흐름을 보여줍니다."
            ),
            "unit": "Z-score",
            "side_title": "TOP 10 콘텐츠 유형 구성",
            "side_meta": (
                f"전체 HIGH·MEDIUM 후보 {content_candidate_total}건 / "
                f"전체 콘텐츠 {content_all_total}건"
            ),
            "note": (
                "막대: Z-score 기반 후보 비교 · 선: 전처리된 30일 관심도 시계열 · "
                "CSV 콘텐츠 메타데이터 + 재현 가능한 시뮬레이션 관심도 지수"
            ),
            "series": content_series,
            "breakdown": content_breakdown,
        },
        "baseball": {
            "name": "야구",
            "chart_title": "야구 상위 이상신호 프로필",
            "description": (
                "기온·습도·강수 조건별 선수 기록 변화 중 "
                "신호 강도가 큰 후보를 확인합니다."
            ),
            "unit": "|Signal Score|",
            "side_title": "상위 후보의 기상 유형 구성",
            "note": "신호 강도 상위 30개 후보의 구성 기준",
            "series": baseball_series,
            "breakdown": baseball_breakdown,
        },
    }


# =========================================================
# HOME
# =========================================================

@home_v2_nav_bp.route("/home-v2-nav")
def home_v2_nav():
    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart,
    ) = load_dashboard_data()

    top_signals = list(
        top_signals or []
    )

    # 사회/경제 등 기존 팀 데이터는 먼저 보존합니다.
    base_top_signals = [
        dict(item)
        for item in top_signals
        if item.get("category") not in {"K콘텐츠", "주식"}
    ]

    stock_signals = load_stock_home_signals(limit=5)
    kcontent_signals = load_kcontent_home_signals(limit=5)
    baseball_signals = load_baseball_home_signals(limit=5)

    top_signals = list(base_top_signals)
    top_signals.extend(stock_signals)
    top_signals.extend(kcontent_signals)
    top_signals.extend(baseball_signals)

    print()
    print("======================================")
    print("[HOME] 메인페이지 데이터 확인")
    print("전체 시그널:", len(top_signals))
    print("K콘텐츠:", len(kcontent_signals))
    print("주식:", len(stock_signals))
    print("야구:", len(baseball_signals))

    category_flow = build_category_flow(
        base_top_signals
    )

    print()
    print("========================================")
    print("[HOME] 분야별 시그널 흐름 연결")


    for key in (
        "social",
        "economy",
        "stock",
        "content",
        "baseball",
    ):
        flow = category_flow[key]
        print(
            f"{flow['name']}:",
            len(flow["series"]),
            "개 프로필 /",
            len(flow["breakdown"]),
            "개 분포"
        )

    print("========================================")
    print()

    return render_template(
        "home/home_index_v2_nav.html",
        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart,
        category_flow=category_flow,
    )
