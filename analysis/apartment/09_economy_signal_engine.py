import os
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

INPUT_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "economy_monthly.csv"
)

OUTPUT_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "all_economy_signals.csv"
)


# =========================================================
# Z-SCORE 계산 함수
# =========================================================

def zscore(series):

    std = series.std()

    if pd.isna(std) or std == 0:
        return pd.Series(0, index=series.index)

    return (series - series.mean()) / std


# =========================================================
# 시그널 행 생성 함수
# =========================================================

def make_signal_rows(
    df,
    mask,
    signal_type,
    signal_name,
    score_series,
    reason
):

    temp = df.loc[mask].copy()

    if temp.empty:
        return pd.DataFrame()

    temp["signal_type"] = signal_type
    temp["signal_name"] = signal_name

    temp["Signal_score"] = (
        score_series.loc[temp.index]
        .astype(float)
        .round(3)
    )

    temp["reason"] = reason

    return temp


# =========================================================
# 데이터 불러오기
# =========================================================

df = pd.read_csv(INPUT_PATH)

df["Date"] = pd.to_datetime(df["Date"])

df = df.sort_values(
    ["Region", "Date"]
).reset_index(drop=True)


# =========================================================
# 전년 동월 값
# =========================================================

df["Price_prev"] = (
    df.groupby("Region")["Median_price_per_m2"]
    .shift(12)
)

df["Transaction_prev"] = (
    df.groupby("Region")["Transaction_count"]
    .shift(12)
)

df["Base_rate_prev"] = (
    df.groupby("Region")["Base_rate"]
    .shift(12)
)


# =========================================================
# 전년 동월 대비 변화
# =========================================================

df["Price_yoy_pct"] = (
    (
        df["Median_price_per_m2"]
        - df["Price_prev"]
    )
    / df["Price_prev"]
    * 100
)

df["Transaction_yoy_pct"] = (
    (
        df["Transaction_count"]
        - df["Transaction_prev"]
    )
    / df["Transaction_prev"]
    * 100
)

df["Base_rate_change"] = (
    df["Base_rate"]
    - df["Base_rate_prev"]
)


# =========================================================
# 같은 월 지역 간 Z-SCORE
# =========================================================

df["Price_z"] = (
    df.groupby("Date")["Price_yoy_pct"]
    .transform(zscore)
)

df["Transaction_z"] = (
    df.groupby("Date")["Transaction_yoy_pct"]
    .transform(zscore)
)


signals = []


# =========================================================
# SIGNAL 1
# 금리 ↑ + 주택가격 ↑
#
# 단순 동반 상승이 아니라
# 가격 상승 강도가 전국 비교에서 충분히 큰 경우
# =========================================================

mask = (
    df["Price_prev"].notna()
    & (df["Base_rate_change"] > 0)
    & (df["Price_yoy_pct"] > 0)
    & (df["Price_z"] >= 1.0)
)

score = (
    df["Price_z"]
    + df["Base_rate_change"]
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "rate_price_reverse",
        "금리 ↑ + 주택가격 ↑",
        score,
        "금리가 상승한 기간에도 주택가격 상승폭이 같은 시점의 다른 지역보다 크게 나타남"
    )
)


# =========================================================
# SIGNAL 2
# 가격 ↑ + 거래량 ↓
# =========================================================

mask = (
    df["Price_prev"].notna()
    & df["Transaction_prev"].notna()
    & (df["Price_yoy_pct"] > 0)
    & (df["Transaction_yoy_pct"] < 0)
    & (df["Price_z"] > 0)
    & (df["Transaction_z"] < 0)
)

score = (
    df["Price_z"]
    - df["Transaction_z"]
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "price_volume_cross",
        "가격 ↑ + 거래량 ↓",
        score,
        "주택가격은 상승했지만 거래량은 감소하는 엇갈린 흐름이 나타남"
    )
)


# =========================================================
# SIGNAL 3
# 주택가격 급등
# =========================================================

mask = (
    df["Price_prev"].notna()
    & (df["Price_yoy_pct"] > 0)
    & (df["Price_z"] >= 2)
)

score = (
    df["Price_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "price_surge",
        "주택가격 급등",
        score,
        "전년 동월 대비 주택가격 상승폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# SIGNAL 4
# 주택가격 급락
# =========================================================

mask = (
    df["Price_prev"].notna()
    & (df["Price_yoy_pct"] < 0)
    & (df["Price_z"] <= -2)
)

score = (
    df["Price_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "price_drop",
        "주택가격 급락",
        score,
        "전년 동월 대비 주택가격 하락폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# SIGNAL 5
# 거래량 급증
# =========================================================

mask = (
    df["Transaction_prev"].notna()
    & (df["Transaction_yoy_pct"] > 0)
    & (df["Transaction_z"] >= 2)
)

score = (
    df["Transaction_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "transaction_surge",
        "거래량 급증",
        score,
        "전년 동월 대비 거래량 증가폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# SIGNAL 6
# 거래량 급감
# =========================================================

mask = (
    df["Transaction_prev"].notna()
    & (df["Transaction_yoy_pct"] < 0)
    & (df["Transaction_z"] <= -2)
)

score = (
    df["Transaction_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "transaction_drop",
        "거래량 급감",
        score,
        "전년 동월 대비 거래량 감소폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# 모든 경제 시그널 합치기
# =========================================================

signals = [
    signal
    for signal in signals
    if not signal.empty
]

if not signals:

    print("탐지된 경제 시그널이 없습니다.")

    raise SystemExit


result = pd.concat(
    signals,
    ignore_index=True
)


# =========================================================
# 필요한 컬럼 정리
# =========================================================

result = result[
    [
        "Date",
        "Region",

        "signal_type",
        "signal_name",

        "Price_prev",
        "Median_price_per_m2",
        "Price_yoy_pct",

        "Transaction_prev",
        "Transaction_count",
        "Transaction_yoy_pct",

        "Base_rate_prev",
        "Base_rate",
        "Base_rate_change",

        "Price_z",
        "Transaction_z",

        "Signal_score",
        "reason"
    ]
]


# =========================================================
# 각 시그널 종류 안에서 순위
# =========================================================

result["rank_in_type"] = (
    result
    .groupby("signal_type")["Signal_score"]
    .rank(
        ascending=False,
        method="first"
    )
    .astype(int)
)


# =========================================================
# 위험도 등급
# =========================================================

def severity(score):

    if score >= 4:
        return "HIGH"

    elif score >= 2:
        return "MEDIUM"

    return "LOW"


result["severity"] = (
    result["Signal_score"]
    .apply(severity)
)


# =========================================================
# 전체 점수순 정렬
# =========================================================

result = result.sort_values(
    [
        "Signal_score",
        "Date"
    ],
    ascending=[
        False,
        False
    ]
)


# =========================================================
# CSV 저장
# =========================================================

os.makedirs(
    os.path.dirname(OUTPUT_PATH),
    exist_ok=True
)

result.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"
)


# =========================================================
# 터미널 결과 출력
# =========================================================

print()
print("=" * 70)
print("경제 시그널 탐지 완료")
print("=" * 70)

print()

print(
    result
    .groupby(
        [
            "signal_type",
            "signal_name"
        ]
    )
    .size()
)

print()

print("-" * 70)
print("전체 탐지 건수")
print("-" * 70)

print(
    f"{len(result):,}건"
)

print()

print("-" * 70)
print("상위 20개 시그널")
print("-" * 70)

print(
    result[
        [
            "Date",
            "Region",
            "signal_name",
            "Signal_score",
            "severity"
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print()
print(
    f"저장 완료: {OUTPUT_PATH}"
)