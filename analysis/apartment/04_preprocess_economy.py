import pandas as pd
from pathlib import Path


# ==================================================
# 1. 파일 경로
# ==================================================

APART_PATH = "data/raw/Apart Deal.csv"
RATE_PATH = "data/raw/base_rate.csv"

OUTPUT_PATH = "data/processed/economy_monthly.csv"


# ==================================================
# 2. 아파트 실거래 데이터 불러오기
# ==================================================

print("=" * 60)
print("경제 데이터 전처리 시작")
print("=" * 60)

print("\n[1] 아파트 실거래 데이터 불러오는 중...")

apart = pd.read_csv(
    APART_PATH,
    low_memory=False
)

print("아파트 원본 크기:")
print(apart.shape)

print("\n컬럼:")
print(apart.columns.tolist())


# ==================================================
# 3. 거래일 날짜형 변환
# ==================================================

apart["거래일"] = pd.to_datetime(
    apart["거래일"],
    format="mixed",
    errors="coerce"
)

print("\n거래일 범위:")
print(
    apart["거래일"].min(),
    "~",
    apart["거래일"].max()
)


# ==================================================
# 4. 거래금액 숫자형 변환
# ==================================================
#
# 예:
# "26,700" -> 26700
#
# 단위는 원본 데이터 기준 만원
# ==================================================

apart["거래금액"] = (
    apart["거래금액"]
    .astype(str)
    .str.replace(",", "", regex=False)
    .str.strip()
)

apart["거래금액"] = pd.to_numeric(
    apart["거래금액"],
    errors="coerce"
)


# ==================================================
# 5. 전용면적 숫자형 변환
# ==================================================

apart["전용면적"] = pd.to_numeric(
    apart["전용면적"],
    errors="coerce"
)


# ==================================================
# 6. 분석에 필요한 결측치 제거
# ==================================================

before = len(apart)

apart = apart.dropna(
    subset=[
        "거래일",
        "거래금액",
        "전용면적",
        "지역코드"
    ]
).copy()

apart = apart[
    apart["전용면적"] > 0
].copy()

after = len(apart)

print("\n전처리 전 거래 건수:", before)
print("전처리 후 거래 건수:", after)
print("제외된 거래 건수:", before - after)


# ==================================================
# 7. ㎡당 거래가격 계산
# ==================================================
#
# 아파트마다 전용면적이 다르기 때문에
# 단순 거래금액이 아니라 ㎡당 가격을 사용
# ==================================================

apart["Price_per_m2"] = (
    apart["거래금액"]
    / apart["전용면적"]
)


# ==================================================
# 8. 월 단위 날짜 만들기
# ==================================================

apart["Date"] = (
    apart["거래일"]
    .dt.to_period("M")
    .dt.to_timestamp()
)


# ==================================================
# 9. 지역코드 정리
# ==================================================

apart["Region_code"] = (
    pd.to_numeric(
        apart["지역코드"],
        errors="coerce"
    )
    .astype("Int64")
    .astype(str)
)


# ==================================================
# 10. 시도 코드 / 시도명 만들기
# ==================================================
#
# 예:
# 11110 -> 11 -> 서울특별시
# 26110 -> 26 -> 부산광역시
# ==================================================

apart["Sido_code"] = (
    apart["Region_code"]
    .str[:2]
)


sido_map = {
    "11": "서울특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "29": "광주광역시",
    "30": "대전광역시",
    "31": "울산광역시",
    "36": "세종특별자치시",
    "41": "경기도",
    "42": "강원도",
    "43": "충청북도",
    "44": "충청남도",
    "45": "전라북도",
    "46": "전라남도",
    "47": "경상북도",
    "48": "경상남도",
    "50": "제주특별자치도"
}


apart["Region"] = (
    apart["Sido_code"]
    .map(sido_map)
)


print("\n[2] 시도 변환 결과:")

print(
    apart[
        [
            "Region_code",
            "Sido_code",
            "Region"
        ]
    ]
    .drop_duplicates()
    .sort_values("Region_code")
    .head(30)
    .to_string(index=False)
)


print("\n시도 변환 실패 건수:")
print(
    apart["Region"]
    .isna()
    .sum()
)


print("\n시도별 거래 건수:")

print(
    apart["Region"]
    .value_counts()
)


# ==================================================
# 11. 시도 × 월 단위 집계
# ==================================================
#
# Median_price_per_m2:
#   해당 시도/월의 ㎡당 거래가격 중앙값
#
# Transaction_count:
#   해당 시도/월의 거래 건수
# ==================================================

monthly_apart = (
    apart
    .dropna(
        subset=["Region"]
    )
    .groupby(
        [
            "Date",
            "Region"
        ],
        as_index=False
    )
    .agg(
        Median_price_per_m2=(
            "Price_per_m2",
            "median"
        ),
        Transaction_count=(
            "Price_per_m2",
            "size"
        )
    )
)


print("\n[3] 아파트 시도×월 집계 완료")

print("집계 데이터 크기:")
print(monthly_apart.shape)

print("\n집계 데이터 예시:")

print(
    monthly_apart
    .head(20)
    .to_string(index=False)
)


# ==================================================
# 12. 기준금리 데이터 불러오기
# ==================================================

print("\n[4] 기준금리 데이터 불러오는 중...")

rate_raw = pd.read_csv(
    RATE_PATH,
    low_memory=False
)

print("기준금리 원본 크기:")
print(rate_raw.shape)


# ==================================================
# 13. 기준금리 Wide -> Long 변환
# ==================================================

id_columns = [
    "통계표",
    "계정항목",
    "단위",
    "변환"
]

rate = rate_raw.melt(
    id_vars=id_columns,
    var_name="Date",
    value_name="Base_rate"
)


# ==================================================
# 14. 기준금리 날짜 정리
# ==================================================

rate["Date"] = pd.to_datetime(
    rate["Date"],
    format="%Y/%m",
    errors="coerce"
)


# ==================================================
# 15. 기준금리 숫자형 변환
# ==================================================

rate["Base_rate"] = pd.to_numeric(
    rate["Base_rate"],
    errors="coerce"
)


rate = (
    rate[
        [
            "Date",
            "Base_rate"
        ]
    ]
    .dropna()
    .sort_values("Date")
    .reset_index(drop=True)
)


print("\n기준금리 정리 결과:")

print(
    rate
    .head(10)
    .to_string(index=False)
)

print("\n기준금리 기간:")
print(
    rate["Date"].min(),
    "~",
    rate["Date"].max()
)


# ==================================================
# 16. 아파트 + 기준금리 결합
# ==================================================

economy = monthly_apart.merge(
    rate,
    on="Date",
    how="inner"
)


# ==================================================
# 17. 최종 데이터 정렬
# ==================================================

economy = economy.sort_values(
    [
        "Region",
        "Date"
    ]
).reset_index(drop=True)


# ==================================================
# 18. 최종 데이터 확인
# ==================================================

print("\n" + "=" * 60)
print("경제 데이터 결합 완료")
print("=" * 60)

print("\n최종 데이터 크기:")
print(economy.shape)

print("\n최종 기간:")
print(
    economy["Date"].min(),
    "~",
    economy["Date"].max()
)

print("\n최종 지역 개수:")
print(
    economy["Region"].nunique()
)

print("\n최종 지역 목록:")

print(
    sorted(
        economy["Region"]
        .dropna()
        .unique()
    )
)

print("\n최종 데이터 예시:")

print(
    economy
    .head(30)
    .to_string(index=False)
)


# ==================================================
# 19. 저장
# ==================================================

Path(
    "data/processed"
).mkdir(
    parents=True,
    exist_ok=True
)

economy.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"
)


print("\n" + "=" * 60)
print("경제 데이터 전처리 완료!")
print("=" * 60)

print("저장 위치:")
print(OUTPUT_PATH)

