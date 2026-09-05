import os
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

INPUT_PATH = os.path.join(
    PROJECT_ROOT,
    "data",
    "processed",
    "social_monthly.csv"
)

OUTPUT_PATH = os.path.join(
    PROJECT_ROOT,
    "result",
    "all_social_signals.csv"
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
    ["Region_ko", "Date"]
).reset_index(drop=True)


# =========================================================
# 전년 동월 값 계산
# =========================================================

df["Natural_growth_prev"] = (
    df.groupby("Region_ko")["Natural_growth"]
    .shift(12)
)

df["Net_migration_prev"] = (
    df.groupby("Region_ko")["Net_migration"]
    .shift(12)
)


# =========================================================
# 전년 동월 대비 변화량
# =========================================================

df["Natural_growth_change"] = (
    df["Natural_growth"]
    - df["Natural_growth_prev"]
)

df["Net_migration_change"] = (
    df["Net_migration"]
    - df["Net_migration_prev"]
)


# =========================================================
# 같은 월의 지역 간 Z-SCORE 계산
# =========================================================

df["Natural_growth_z"] = (
    df.groupby("Date")["Natural_growth"]
    .transform(zscore)
)

df["Net_migration_z"] = (
    df.groupby("Date")["Net_migration"]
    .transform(zscore)
)

df["Natural_growth_change_z"] = (
    df.groupby("Date")["Natural_growth_change"]
    .transform(zscore)
)

df["Net_migration_change_z"] = (
    df.groupby("Date")["Net_migration_change"]
    .transform(zscore)
)


signals = []


# =========================================================
# SIGNAL 1
# 자연감소 ↓ + 순이동 ↑
# =========================================================

mask = (
    (df["Natural_growth"] < 0)
    & (df["Net_migration"] > 0)
    & (df["Natural_growth_z"] < 0)
    & (df["Net_migration_z"] > 0)
)

score = (
    -df["Natural_growth_z"]
    + df["Net_migration_z"]
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "social_cross_inflow",
        "자연감소 ↓ + 순이동 ↑",
        score,
        "자연적 인구감소가 나타나는 동시에 순유입이 나타난 지역"
    )
)


# =========================================================
# SIGNAL 2
# 자연감소 ↓ + 순이동 ↓
# =========================================================

mask = (
    (df["Natural_growth"] < 0)
    & (df["Net_migration"] < 0)
    & (df["Natural_growth_z"] < 0)
    & (df["Net_migration_z"] < 0)
)

score = (
    -df["Natural_growth_z"]
    - df["Net_migration_z"]
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "social_double_decline",
        "자연감소 ↓ + 순이동 ↓",
        score,
        "자연감소와 순유출이 동시에 강하게 나타난 지역"
    )
)


# =========================================================
# SIGNAL 3
# 순이동 급증
# =========================================================

mask = (
    df["Net_migration_prev"].notna()
    & (df["Net_migration_change"] > 0)
    & (df["Net_migration_change_z"] >= 2)
)

score = (
    df["Net_migration_change_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "migration_surge",
        "순이동 급증",
        score,
        "전년 동월 대비 순이동 증가폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# SIGNAL 4
# 순이동 급감
# =========================================================

mask = (
    df["Net_migration_prev"].notna()
    & (df["Net_migration_change"] < 0)
    & (df["Net_migration_change_z"] <= -2)
)

score = (
    df["Net_migration_change_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        mask,
        "migration_drop",
        "순이동 급감",
        score,
        "전년 동월 대비 순이동 감소폭이 같은 시점의 다른 지역보다 매우 크게 나타남"
    )
)


# =========================================================
# SIGNAL 5
# 순이동 방향 반전
#
# 단순히 - → + / + → - 가 된 모든 경우가 아니라
# 변화 강도까지 충분히 큰 경우만 탐지
# =========================================================

reversal_mask = (
    df["Net_migration_prev"].notna()
    & (
        (
            (df["Net_migration_prev"] < 0)
            & (df["Net_migration"] > 0)
        )
        |
        (
            (df["Net_migration_prev"] > 0)
            & (df["Net_migration"] < 0)
        )
    )
    & (
        df["Net_migration_change_z"].abs() >= 1.5
    )
)

score = (
    df["Net_migration_change_z"].abs()
    + df["Net_migration_z"].abs()
)

signals.append(
    make_signal_rows(
        df,
        reversal_mask,
        "migration_reverse",
        "순이동 방향 반전",
        score,
        "전년 동월과 비교해 순유입·순유출 방향이 반대로 바뀌었고 변화 강도도 크게 나타남"
    )
)


# =========================================================
# 모든 사회 시그널 합치기
# =========================================================

signals = [
    signal
    for signal in signals
    if not signal.empty
]

if not signals:

    print("탐지된 사회 시그널이 없습니다.")

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
        "Region_ko",

        "signal_type",
        "signal_name",

        "Natural_growth_prev",
        "Natural_growth",
        "Natural_growth_change",

        "Net_migration_prev",
        "Net_migration",
        "Net_migration_change",

        "Natural_growth_z",
        "Net_migration_z",
        "Natural_growth_change_z",
        "Net_migration_change_z",

        "Signal_score",
        "reason"
    ]
]


# =========================================================
# 각 시그널 종류 안에서 순위 계산
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
print("사회 시그널 탐지 완료")
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
            "Region_ko",
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