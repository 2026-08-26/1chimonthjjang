import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Blueprint, abort, jsonify, render_template, request

from stock_ai_agent import StockAIAgent


# =========================================================
# BLUEPRINT / PATH
# =========================================================

stock_bp = Blueprint("stock", __name__)
stock_ai_agent = StockAIAgent()

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "result" / "stock"

SIGNAL_PATH = DATA / "all_stock_signals.csv"
RAW_STOCK_PATH = ROOT / "data" / "raw" / "stock" / "krx_all_stocks_1y.csv"


# =========================================================
# CSV HELPERS
# =========================================================

@lru_cache(maxsize=8)
def _read(path, modified):
    """
    파일 수정 시간이 바뀌면 자동으로 새 캐시 키를 사용합니다.
    종목코드는 앞자리 0이 사라지지 않도록 문자열로 읽습니다.
    """
    path = Path(path)

    header = pd.read_csv(
        path,
        nrows=0,
        encoding="utf-8-sig",
    )

    dtype_map = {}

    if "code" in header.columns:
        dtype_map["code"] = str

    if "종목코드" in header.columns:
        dtype_map["종목코드"] = str

    return pd.read_csv(
        path,
        dtype=dtype_map,
        encoding="utf-8-sig",
    ).fillna("")


def _read_path(path, required=True):
    path = Path(path)

    if not path.exists():
        if required:
            abort(
                503,
                description=(
                    "주식 분석 파일이 없습니다. "
                    "result/stock/all_stock_signals.csv 파일을 확인해주세요."
                ),
            )

        return pd.DataFrame()

    return _read(
        str(path),
        path.stat().st_mtime_ns,
    ).copy()


def read_signals():
    """
    현재 주식 화면의 기준 파일.

    stock_daily.csv가 없어도
    all_stock_signals.csv만 있으면 목록/상세/API가 동작합니다.
    """
    df = _read_path(
        SIGNAL_PATH,
        required=True,
    )

    required_columns = {
        "date",
        "market",
        "code",
    }

    missing = required_columns - set(df.columns)

    if missing:
        abort(
            503,
            description=(
                "all_stock_signals.csv 형식이 올바르지 않습니다. "
                f"누락 컬럼: {', '.join(sorted(missing))}"
            ),
        )

    df["date"] = (
        df["date"]
        .astype(str)
        .str.strip()
    )

    df["market"] = (
        df["market"]
        .astype(str)
        .str.strip()
    )

    df["code"] = (
        df["code"]
        .astype(str)
        .str.strip()
        .str.zfill(6)
    )

    return df


def read_raw_stock():
    """
    상세 그래프용 실제 KRX 원본 데이터.

    원본 파일이 없더라도 주식 목록 페이지와 상세 기본 정보는
    all_stock_signals.csv만으로 계속 동작합니다.
    """
    df = _read_path(
        RAW_STOCK_PATH,
        required=False,
    )

    if df.empty:
        return df

    if "종목코드" in df.columns:
        df["종목코드"] = (
            df["종목코드"]
            .astype(str)
            .str.strip()
            .str.zfill(6)
        )

    if "시장" in df.columns:
        df["시장"] = (
            df["시장"]
            .astype(str)
            .str.strip()
        )

    if "날짜" in df.columns:
        df["날짜"] = (
            df["날짜"]
            .astype(str)
            .str.strip()
        )

    return df


def records(df):
    return json.loads(
        df.to_json(
            orient="records",
            force_ascii=False,
        )
    )


def _truthy(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    text = str(value).strip().lower()

    return text not in {
        "",
        "0",
        "0.0",
        "false",
        "none",
        "nan",
        "no",
    }


def labels(row):
    names = []

    for key, title in (
        ("volume_signal", "거래량 급증"),
        ("price_signal", "5거래일 가격 급변"),
        ("concentration_signal", "거래대금 쏠림"),
    ):
        if _truthy(row.get(key)):
            names.append(title)

    return names


def _numeric_sort(df):
    """
    signal_count → score 순으로 안전하게 정렬합니다.
    """
    result = df.copy()
    sort_columns = []
    ascending = []

    if "signal_count" in result.columns:
        result["_signal_count_sort"] = pd.to_numeric(
            result["signal_count"],
            errors="coerce",
        ).fillna(0)

        sort_columns.append(
            "_signal_count_sort"
        )
        ascending.append(False)

    if "score" in result.columns:
        result["_score_sort"] = pd.to_numeric(
            result["score"],
            errors="coerce",
        ).fillna(0)

        sort_columns.append(
            "_score_sort"
        )
        ascending.append(False)

    if sort_columns:
        result = result.sort_values(
            sort_columns,
            ascending=ascending,
        )

    return result


# =========================================================
# STOCK INDEX
# =========================================================

@stock_bp.route("/stock")
def index():
    signals = read_signals()

    dates = sorted(
        [
            value
            for value in signals["date"].unique().tolist()
            if str(value).strip()
        ],
        reverse=True,
    )

    if not dates:
        abort(
            503,
            description="주식 이상신호 날짜 데이터가 없습니다.",
        )

    selected = request.args.get(
        "date",
        dates[0],
    )

    market = request.args.get(
        "market",
        "ALL",
    )

    if selected not in dates:
        abort(400)

    if market not in {
        "ALL",
        "KOSPI",
        "KOSDAQ",
    }:
        abort(400)

    selected_rows = signals[
        signals["date"].eq(selected)
    ].copy()

    if market != "ALL":
        selected_rows = selected_rows[
            selected_rows["market"].eq(market)
        ].copy()

    selected_rows = _numeric_sort(
        selected_rows
    )

    items = records(
        selected_rows.head(10)
    )

    for item in items:
        item["labels"] = labels(item)

    return render_template(
        "stock/index.html",
        items=items,
        dates=dates,
        selected=selected,
        market=market,
        count=len(selected_rows),
    )


# =========================================================
# STOCK DETAIL
# =========================================================

def _build_history_from_raw(
    market,
    code,
    date,
):
    raw = read_raw_stock()

    required = {
        "날짜",
        "시장",
        "종목코드",
    }

    if (
        raw.empty
        or
        not required.issubset(
            raw.columns
        )
    ):
        return pd.DataFrame()

    selected = raw[
        raw["시장"].eq(market)
        &
        raw["종목코드"].eq(code)
        &
        raw["날짜"].le(date)
    ].copy()

    if selected.empty:
        return pd.DataFrame()

    selected = selected.sort_values(
        "날짜"
    )

    column_map = {
        "날짜": "date",
        "시가": "open",
        "고가": "high",
        "저가": "low",
        "종가": "close",
        "거래량": "volume",
    }

    history = pd.DataFrame()

    for source, target in column_map.items():
        if source in selected.columns:
            history[target] = selected[source]

    if "date" not in history.columns:
        return pd.DataFrame()

    for column in (
        "open",
        "high",
        "low",
        "close",
        "volume",
    ):
        if column not in history.columns:
            history[column] = None

        history[column] = pd.to_numeric(
            history[column],
            errors="coerce",
        )

    return history[
        [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    ]


def _build_history_from_signals(
    signals,
    market,
    code,
    date,
):
    """
    KRX 원본 파일이 없을 때 사용하는 안전한 fallback.
    이상신호가 있었던 날짜만 표시됩니다.
    """
    history = signals[
        signals["market"].eq(market)
        &
        signals["code"].eq(code)
        &
        signals["date"].le(date)
    ].copy()

    if history.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ]
        )

    history = history.sort_values(
        "date"
    )

    for column in (
        "close",
        "volume",
    ):
        if column not in history.columns:
            history[column] = None

        history[column] = pd.to_numeric(
            history[column],
            errors="coerce",
        )

    for column in (
        "open",
        "high",
        "low",
    ):
        history[column] = None

    return history[
        [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    ]


@stock_bp.route(
    "/stock/<market>/<code>/<date>"
)
def detail(
    market,
    code,
    date,
):
    market = str(market).strip()
    code = str(code).strip().zfill(6)
    date = str(date).strip()

    signals = read_signals()

    found = signals[
        signals["market"].eq(market)
        &
        signals["code"].eq(code)
        &
        signals["date"].eq(date)
    ]

    if found.empty:
        abort(404)

    item = records(
        found.head(1)
    )[0]

    item["labels"] = labels(item)

    # stock_daily.csv에 의존하지 않고,
    # 실제 KRX 원본 데이터에서 상세 그래프 이력을 만듭니다.
    history_df = _build_history_from_raw(
        market=market,
        code=code,
        date=date,
    )

    # 원본 파일을 못 찾는 경우에도 상세 페이지 자체는 살립니다.
    if history_df.empty:
        history_df = _build_history_from_signals(
            signals=signals,
            market=market,
            code=code,
            date=date,
        )

    history = records(
        history_df
    )

    questions = [
        "같은 시기 실적 발표나 주요 계약·투자 공시가 있었나?",
        "주식분할·병합·유상증자·거래 재개가 수치에 영향을 줬나?",
        "투자자별 매매 동향과 업종 흐름에서도 같은 변화가 확인되나?",
    ]

    return render_template(
        "stock/detail.html",
        item=item,
        history=history,
        questions=questions,
    )


# =========================================================
# STOCK AI REPORT
# =========================================================

@stock_bp.route(
    "/api/stock-report/<market>/<code>/<date>",
    methods=["POST"],
)
def stock_report(
    market,
    code,
    date,
):
    market = str(market).strip()
    code = str(code).strip().zfill(6)
    date = str(date).strip()

    signals = read_signals()

    found = signals[
        signals["market"].eq(market)
        &
        signals["code"].eq(code)
        &
        signals["date"].eq(date)
    ]

    if found.empty:
        return jsonify(
            {
                "error":
                    "주식 시그널을 찾을 수 없습니다."
            }
        ), 404

    item = records(
        found.head(1)
    )[0]

    item["labels"] = labels(item)

    payload = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    if not isinstance(
        payload,
        dict,
    ):
        return jsonify(
            {
                "error":
                    "잘못된 요청입니다."
            }
        ), 400

    report = stock_ai_agent.generate_report(
        item,
        include_news=(
            payload.get(
                "include_news"
            )
            is True
        ),
    )

    from web.article_draft import attach_draft
    import re
    metrics=[]
    for fact in report['facts']:
        match=re.match(r'^(.*?)\s+([+-]?[\d,.]+(?:%|원|배|주))$',fact)
        if match:
            metrics.append({'label':match[1],'value':match[2]})
    report.update(region=item['name'],period=item['date'],metrics=metrics)
    return jsonify(attach_draft(report, '주가·거래량 변화'))


@stock_bp.post('/api/stock-draft')
def stock_draft():
    from web.article_draft import draft_response
    return draft_response()
