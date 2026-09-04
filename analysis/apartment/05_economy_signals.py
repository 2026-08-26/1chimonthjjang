import pandas as pd
import numpy as np
from pathlib import Path


# ==================================================
# 1. 파일 경로
# ==================================================

INPUT_PATH = "data/processed/economy_monthly.csv"

RATE_OUTPUT_PATH = "result/economy_rate_reverse_top10.csv"
CROSS_OUTPUT_PATH = "result/economy_price_volume_cross_top10.csv"


# ==================================================
# 2. 데이터 불러오기
# ==================================================

print("=" * 60)
print("경제 시그널 탐지 시작")
print("=" * 60)

df = pd.read_csv(
    INPUT_PATH
)

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

df = df.sort_values(
    [
        "Region",
        "Date"
    ]
).reset_index(drop=True)


print("\n데이터 크기:")
print(df.shape)

print("\n기간:")
print(
    df["Date"].min(),
    "~",
    df["Date"].max()
)

print("\n지역 개수:")
print(
    df["Region"].nunique()
)


# ==================================================
# 3. 전년 동월 값 만들기
# ==================================================
#
# 계절성 영향을 줄이기 위해
# 바로 전 달이 아니라 전년 같은 달과 비교합니다.
#
# 예:
# 2022년 3월
#     ↓
# 2021년 3월과 비교
# ==================================================

df["Price_prev_year"] = (
    df
    .groupby("Region")["Median_price_per_m2"]
    .shift(12)
)

df["Transaction_prev_year"] = (
    df
    .groupby("Region")["Transaction_count"]
    .shift(12)
)

df["Base_rate_prev_year"] = (
    df
    .groupby("Region")["Base_rate"]
    .shift(12)
)


# ==================================================
# 4. 전년 동월 대비 변화 계산
# ==================================================

df["Price_yoy_pct"] = (
    (
        df["Median_price_per_m2"]
        / df["Price_prev_year"]
    )
    - 1
) * 100


df["Transaction_yoy_pct"] = (
    (
        df["Transaction_count"]
        / df["Transaction_prev_year"]
    )
    - 1
) * 100


df["Base_rate_change"] = (
    df["Base_rate"]
    - df["Base_rate_prev_year"]
)


# ==================================================
# 5. 무한값 제거
# ==================================================

df = df.replace(
    [
        np.inf,
        -np.inf
    ],
    np.nan
)


# ==================================================
# 6. 지역별 가격 변화 z-score
# ==================================================
#
# 지역마다 평소 가격 변동폭이 다르기 때문에
# 각 지역의 평소 변화와 비교해서
# 이번 상승이 얼마나 이례적인지 계산합니다.
# ==================================================

df["Price_yoy_mean"] = (
    df
    .groupby("Region")["Price_yoy_pct"]
    .transform("mean")
)

df["Price_yoy_std"] = (
    df
    .groupby("Region")["Price_yoy_pct"]
    .transform("std")
)


df["Price_z"] = (
    (
        df["Price_yoy_pct"]
        - df["Price_yoy_mean"]
    )
    / df["Price_yoy_std"]
)


# ==================================================
# 7. 지역별 거래량 변화 z-score
# ==================================================

df["Transaction_yoy_mean"] = (
    df
    .groupby("Region")["Transaction_yoy_pct"]
    .transform("mean")
)

df["Transaction_yoy_std"] = (
    df
    .groupby("Region")["Transaction_yoy_pct"]
    .transform("std")
)


df["Transaction_z"] = (
    (
        df["Transaction_yoy_pct"]
        - df["Transaction_yoy_mean"]
    )
    / df["Transaction_yoy_std"]
)


# ==================================================
# 8. SIGNAL 1
#    기준금리 ↑ + 아파트 가격 ↑
# ==================================================
#
# 의미:
# 기준금리가 전년보다 높은데
# 같은 기간 아파트 ㎡당 중앙가격도 상승
#
# "금리가 올랐는데 왜 가격이 올랐지?"
# 라는 취재 질문을 만드는 패턴
#
# 인과관계를 주장하는 것이 아니라
# 직관과 엇갈리는 움직임을 탐지합니다.
# ==================================================

rate_reverse = df[
    (df["Base_rate_change"] > 0)
    &
    (df["Price_yoy_pct"] > 0)
    &
    (df["Price_z"] > 0)
].copy()


# 신호 점수
#
# 가격 상승이 해당 지역의 평소보다
# 얼마나 이례적인지 + 금리 상승폭
#
rate_reverse["Signal_score"] = (
    rate_reverse["Price_z"]
    +
    rate_reverse["Base_rate_change"]
)


rate_reverse = (
    rate_reverse
    .sort_values(
        "Signal_score",
        ascending=False
    )
    .reset_index(drop=True)
)


rate_top10 = (
    rate_reverse
    .head(10)
    .copy()
)


print("\n" + "=" * 60)
print("SIGNAL 1 : 기준금리 ↑ + 가격 ↑ TOP 10")
print("=" * 60)

print(
    rate_top10[
        [
            "Date",
            "Region",
            "Price_prev_year",
            "Median_price_per_m2",
            "Price_yoy_pct",
            "Base_rate_prev_year",
            "Base_rate",
            "Base_rate_change",
            "Price_z",
            "Signal_score"
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# 9. SIGNAL 2
#    가격 ↑ + 거래량 ↓
# ==================================================
#
# 의미:
#
# 아파트 가격은 전년보다 올랐지만
# 거래 건수는 전년보다 감소
#
# "가격은 오르는데 거래는 얼어붙은 지역"
# 을 찾는 시그널
# ==================================================

price_volume_cross = df[
    (df["Price_yoy_pct"] > 0)
    &
    (df["Transaction_yoy_pct"] < 0)
    &
    (df["Price_z"] > 0)
    &
    (df["Transaction_z"] < 0)
].copy()


# 신호 점수
#
# 가격 상승 이상치가 클수록 +
# 거래량 감소 이상치가 클수록 +
#
price_volume_cross["Signal_score"] = (
    price_volume_cross["Price_z"]
    -
    price_volume_cross["Transaction_z"]
)


price_volume_cross = (
    price_volume_cross
    .sort_values(
        "Signal_score",
        ascending=False
    )
    .reset_index(drop=True)
)


cross_top10 = (
    price_volume_cross
    .head(10)
    .copy()
)


print("\n" + "=" * 60)
print("SIGNAL 2 : 가격 ↑ + 거래량 ↓ TOP 10")
print("=" * 60)

print(
    cross_top10[
        [
            "Date",
            "Region",
            "Price_prev_year",
            "Median_price_per_m2",
            "Price_yoy_pct",
            "Transaction_prev_year",
            "Transaction_count",
            "Transaction_yoy_pct",
            "Price_z",
            "Transaction_z",
            "Signal_score"
        ]
    ]
    .to_string(index=False)
)


# ==================================================
# 10. 결과 저장
# ==================================================

Path(
    "result"
).mkdir(
    parents=True,
    exist_ok=True
)


rate_top10.to_csv(
    RATE_OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"
)


cross_top10.to_csv(
    CROSS_OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"
)


print("\n" + "=" * 60)
print("경제 시그널 탐지 완료")
print("=" * 60)

print("\n저장 완료:")
print(RATE_OUTPUT_PATH)
print(CROSS_OUTPUT_PATH)