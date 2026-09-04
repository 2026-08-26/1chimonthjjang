import pandas as pd


# ==================================================
# 1. 전처리된 사회 데이터 불러오기
# ==================================================

df = pd.read_csv(
    "data/processed/social_monthly.csv",
    low_memory=False
)

# 날짜를 날짜형으로 변환
df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)


print("=" * 60)
print("사회 시그널 분석 시작")
print("=" * 60)

print("\n데이터 크기:")
print(df.shape)

print("\n분석 기간:")
print(df["Date"].min(), "~", df["Date"].max())

print("\n지역 개수:")
print(df["Region_ko"].nunique())


# ==================================================
# 2. 전국 데이터 제외
# ==================================================
# 전국은 개별 지역이 아니므로
# 지역별 이상현상 탐지에서는 제외

regional = df[
    df["Region_ko"] != "전국"
].copy()


# ==================================================
# 3. 사회 시그널 ① 인구 엇갈림
# ==================================================
#
# 자연증가 < 0
# → 출생보다 사망이 많음
#
# 순이동 > 0
# → 나간 사람보다 들어온 사람이 많음
#
# 즉:
# "자연적으로는 인구가 줄어드는데
#  외부에서는 사람이 들어오는 지역"
# ==================================================

population_cross = regional[
    (regional["Natural_growth"] < 0) &
    (regional["Net_migration"] > 0)
].copy()


# ==================================================
# 4. 사회 시그널 ② 인구 이중감소
# ==================================================
#
# 자연증가 < 0
# → 출생보다 사망이 많음
#
# 순이동 < 0
# → 들어온 사람보다 나간 사람이 많음
#
# 즉:
# "자연감소 + 순유출이 동시에 나타나는 지역"
# ==================================================

double_decline = regional[
    (regional["Natural_growth"] < 0) &
    (regional["Net_migration"] < 0)
].copy()


# ==================================================
# 5. 인구 엇갈림 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("① 인구 엇갈림")
print("=" * 60)

print("\n총 발생 건수:")
print(len(population_cross))

print("\n지역별 발생 횟수 TOP 10:")
print(
    population_cross["Region_ko"]
    .value_counts()
    .head(10)
)


# ==================================================
# 6. 인구 이중감소 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("② 인구 이중감소")
print("=" * 60)

print("\n총 발생 건수:")
print(len(double_decline))

print("\n지역별 발생 횟수 TOP 10:")
print(
    double_decline["Region_ko"]
    .value_counts()
    .head(10)
)


# ==================================================
# 7. 인구 엇갈림 실제 사례 확인
# ==================================================

print("\n" + "=" * 60)
print("인구 엇갈림 - 순유입 규모 TOP 10")
print("=" * 60)

cross_top10 = (
    population_cross[
        [
            "Date",
            "Region_ko",
            "Natural_growth",
            "Net_migration"
        ]
    ]
    .sort_values(
        "Net_migration",
        ascending=False
    )
    .head(10)
)

print(
    cross_top10.to_string(index=False)
)


# ==================================================
# 8. 인구 이중감소 강도 계산
# ==================================================
#
# 예:
# 자연증가 = -1000
# 순이동   = -2000
#
# 총 감소 규모 = 3000
#
# 일단 탐색용으로 단순 합산
# ==================================================

double_decline["Total_decline"] = (
    -double_decline["Natural_growth"]
    -double_decline["Net_migration"]
)


# ==================================================
# 9. 인구 이중감소 실제 사례 확인
# ==================================================

print("\n" + "=" * 60)
print("인구 이중감소 - 감소 규모 TOP 10")
print("=" * 60)

decline_top10 = (
    double_decline[
        [
            "Date",
            "Region_ko",
            "Natural_growth",
            "Net_migration",
            "Total_decline"
        ]
    ]
    .sort_values(
        "Total_decline",
        ascending=False
    )
    .head(10)
)

print(
    decline_top10.to_string(index=False)
)
# ==================================================
# 10. 전년 동월 대비 변화량 계산
# ==================================================
#
# 12개월 전 같은 지역의 값과 비교합니다.
#
# 예:
# 2021년 12월 경기도
#       ↕
# 2020년 12월 경기도
#
# 이렇게 비교하면 계절성의 영향을 어느 정도 줄일 수 있습니다.
# ==================================================

regional = regional.sort_values(
    ["Region_ko", "Date"]
).copy()


# 12개월 전 자연증가
regional["Natural_growth_prev_year"] = (
    regional
    .groupby("Region_ko")["Natural_growth"]
    .shift(12)
)


# 12개월 전 순이동
regional["Net_migration_prev_year"] = (
    regional
    .groupby("Region_ko")["Net_migration"]
    .shift(12)
)


# ==================================================
# 11. 전년 동월 대비 변화량
# ==================================================

regional["Natural_growth_change"] = (
    regional["Natural_growth"]
    - regional["Natural_growth_prev_year"]
)

regional["Net_migration_change"] = (
    regional["Net_migration"]
    - regional["Net_migration_prev_year"]
)


# ==================================================
# 12. 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("전년 동월 대비 변화량 계산 완료")
print("=" * 60)

print(
    regional[
        [
            "Date",
            "Region_ko",
            "Natural_growth",
            "Natural_growth_prev_year",
            "Natural_growth_change",
            "Net_migration",
            "Net_migration_prev_year",
            "Net_migration_change"
        ]
    ]
    .dropna()
    .tail(20)
    .to_string(index=False)
)
# ==================================================
# 13. 지역별 Z-score 계산 함수
# ==================================================
#
# Z-score:
# 해당 변화량이 그 지역의 평소 변화량에서
# 얼마나 멀리 떨어져 있는지를 계산합니다.
#
# 0 근처  = 평범
# +값 큼   = 평소보다 크게 증가
# -값 큼   = 평소보다 크게 감소
# ==================================================

def calculate_zscore(series):

    mean = series.mean()
    std = series.std()

    # 표준편차가 0이면 계산 불가능
    if std == 0:
        return pd.Series(0, index=series.index)

    return (series - mean) / std


# ==================================================
# 14. 자연증가 변화량 이상도
# ==================================================

regional["Natural_growth_z"] = (
    regional
    .groupby("Region_ko")["Natural_growth_change"]
    .transform(calculate_zscore)
)


# ==================================================
# 15. 순이동 변화량 이상도
# ==================================================

regional["Net_migration_z"] = (
    regional
    .groupby("Region_ko")["Net_migration_change"]
    .transform(calculate_zscore)
)


# ==================================================
# 16. Z-score 계산 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("지역별 이상도(Z-score) 계산 완료")
print("=" * 60)

print(
    regional[
        [
            "Date",
            "Region_ko",
            "Natural_growth_change",
            "Natural_growth_z",
            "Net_migration_change",
            "Net_migration_z"
        ]
    ]
    .dropna()
    .tail(20)
    .to_string(index=False)
)
# ==================================================
# 17. 시그널 ① 인구 엇갈림 후보
# ==================================================
#
# 현재 상태:
# 자연증가 < 0  → 자연감소
# 순이동 > 0    → 순유입
#
# 그리고 전년 동월 대비 변화 방향도
# 자연증가 악화 / 순이동 개선인 경우를 탐지
# ==================================================

cross_signal = regional[
    (regional["Natural_growth"] < 0) &
    (regional["Net_migration"] > 0) &
    (regional["Natural_growth_z"] < 0) &
    (regional["Net_migration_z"] > 0)
].copy()


# ==================================================
# 18. 인구 엇갈림 점수
# ==================================================
#
# 예:
# 자연증가 Z = -5.0
# 순이동 Z   = +2.3
#
# 점수 = 5.0 + 2.3 = 7.3
#
# 양쪽이 모두 평소보다 크게 엇갈릴수록
# 높은 점수를 받습니다.
# ==================================================

cross_signal["Signal_score"] = (
    -cross_signal["Natural_growth_z"]
    + cross_signal["Net_migration_z"]
)


# ==================================================
# 19. 인구 엇갈림 TOP 10
# ==================================================

cross_top = (
    cross_signal[
        [
            "Date",
            "Region_ko",
            "Natural_growth",
            "Net_migration",
            "Natural_growth_change",
            "Net_migration_change",
            "Natural_growth_z",
            "Net_migration_z",
            "Signal_score"
        ]
    ]
    .sort_values(
        "Signal_score",
        ascending=False
    )
    .head(10)
)


print("\n" + "=" * 60)
print("🔀 인구 엇갈림 최종 후보 TOP 10")
print("=" * 60)

print(
    cross_top.to_string(
        index=False
    )
)


# ==================================================
# 20. 시그널 ② 인구 이중감소 후보
# ==================================================
#
# 현재 상태:
# 자연증가 < 0 → 자연감소
# 순이동 < 0   → 순유출
#
# 변화 방향도:
# 자연증가 악화
# 순이동 악화
# ==================================================

decline_signal = regional[
    (regional["Natural_growth"] < 0) &
    (regional["Net_migration"] < 0) &
    (regional["Natural_growth_z"] < 0) &
    (regional["Net_migration_z"] < 0)
].copy()


# ==================================================
# 21. 인구 이중감소 점수
# ==================================================

decline_signal["Signal_score"] = (
    -decline_signal["Natural_growth_z"]
    -decline_signal["Net_migration_z"]
)


# ==================================================
# 22. 인구 이중감소 TOP 10
# ==================================================

decline_top = (
    decline_signal[
        [
            "Date",
            "Region_ko",
            "Natural_growth",
            "Net_migration",
            "Natural_growth_change",
            "Net_migration_change",
            "Natural_growth_z",
            "Net_migration_z",
            "Signal_score"
        ]
    ]
    .sort_values(
        "Signal_score",
        ascending=False
    )
    .head(10)
)


print("\n" + "=" * 60)
print("⚠ 인구 이중감소 최종 후보 TOP 10")
print("=" * 60)

print(
    decline_top.to_string(
        index=False
    )
)
# ==================================================
# 23. 최종 TOP 10 결과 CSV 저장
# ==================================================

cross_output = "result/social_cross_top10.csv"
decline_output = "result/social_decline_top10.csv"

cross_top.to_csv(
    cross_output,
    index=False,
    encoding="utf-8-sig"
)

decline_top.to_csv(
    decline_output,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 60)
print("사회 시그널 TOP 10 저장 완료")
print("=" * 60)

print("인구 엇갈림:", cross_output)
print("인구 이중감소:", decline_output)