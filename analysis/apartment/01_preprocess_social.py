import pandas as pd


# ==================================================
# 1. 데이터 불러오기
# ==================================================

population = pd.read_csv(
    "data/raw/Korean_demographics.csv",
    low_memory=False
)

migration = pd.read_csv(
    "data/raw/population_migration.csv",
    low_memory=False
)


# ==================================================
# 2. 인구 데이터 날짜 변환
# ==================================================

population["Date"] = pd.to_datetime(
    population["Date"],
    errors="coerce"
)

print("인구 데이터 기간")
print(population["Date"].min(), "~", population["Date"].max())


# ==================================================
# 3. 인구이동 데이터에서 순이동만 선택
# ==================================================

migration_net = migration[
    migration["항목"].astype(str).str.contains("순이동", na=False)
].copy()

print("\n순이동 데이터 행 수:", len(migration_net))

print("\n순이동 지역 확인")
print(migration_net[
    ["행정구역(시군구)별", "항목"]
].to_string(index=False))


# ==================================================
# 4. 필요 없는 열 제거
# ==================================================

migration_net = migration_net.drop(
    columns=["단위", "Unnamed: 273"],
    errors="ignore"
)


# ==================================================
# 5. 가로형 → 세로형 변환
# ==================================================

migration_long = migration_net.melt(
    id_vars=["행정구역(시군구)별", "항목"],
    var_name="Date",
    value_name="Net_migration"
)


# ==================================================
# 6. 날짜 문자열 정리
#
# 예:
# "2000.01 월" → "2000.01" → 날짜
# ==================================================

migration_long["Date"] = (
    migration_long["Date"]
    .astype(str)
    .str.replace(" 월", "", regex=False)
    .str.strip()
)

migration_long["Date"] = pd.to_datetime(
    migration_long["Date"],
    format="%Y.%m",
    errors="coerce"
)


# ==================================================
# 7. 순이동 숫자형 변환
# ==================================================

migration_long["Net_migration"] = pd.to_numeric(
    migration_long["Net_migration"],
    errors="coerce"
)


# ==================================================
# 8. 컬럼명 변경
# ==================================================

migration_long = migration_long.rename(
    columns={
        "행정구역(시군구)별": "Region_ko"
    }
)

migration_long = migration_long[
    ["Date", "Region_ko", "Net_migration"]
]


# ==================================================
# 9. 변환 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("변환된 인구이동 데이터")
print("=" * 60)

print("\n크기:")
print(migration_long.shape)

print("\n앞 20행:")
print(migration_long.head(20).to_string(index=False))

print("\n기간:")
print(
    migration_long["Date"].min(),
    "~",
    migration_long["Date"].max()
)

print("\n지역:")
print(migration_long["Region_ko"].unique())
# ==================================================
# 10. 인구 데이터 지역명 한글로 통일
# ==================================================

region_map = {
    "Whole country": "전국",

    "Seoul": "서울특별시",
    "Busan": "부산광역시",
    "Daegu": "대구광역시",
    "Incheon": "인천광역시",
    "Gwangju": "광주광역시",
    "Daejeon": "대전광역시",
    "Ulsan": "울산광역시",
    "Sejong": "세종특별자치시",

    "Gyeonggi-do": "경기도",
    "Gangwon-do": "강원특별자치도",

    "Chungcheongbuk-do": "충청북도",
    "Chungcheongnam-do": "충청남도",

    "Jeollabuk-do": "전북특별자치도",
    "Jeollanam-do": "전라남도",

    "Gyeongsangbuk-do": "경상북도",
    "Gyeongsangnam-do": "경상남도",

    "Jeju": "제주특별자치도"
}


population["Region_ko"] = population["Region"].map(region_map)


# ==================================================
# 11. 지역명 변환 실패 확인
# ==================================================

print("\n" + "=" * 60)
print("지역명 변환 확인")
print("=" * 60)

failed_regions = population.loc[
    population["Region_ko"].isna(),
    "Region"
].unique()

print("변환 실패 지역:")
print(failed_regions)

# ==================================================
# 12. 인구 데이터에서 필요한 컬럼만 선택
# ==================================================

population_clean = population[
    [
        "Date",
        "Region_ko",
        "Birth",
        "Birth_rate",
        "Death",
        "Death_rate",
        "Marriage",
        "Marriage_rate",
        "Natural_growth",
        "Natural_growth_rate"
    ]
].copy()


# ==================================================
# 13. 인구 + 인구이동 데이터 결합
# ==================================================

social = pd.merge(
    population_clean,
    migration_long,
    on=["Date", "Region_ko"],
    how="left"
)


# ==================================================
# 14. 결합 결과 확인
# ==================================================

print("\n" + "=" * 60)
print("사회 데이터 결합 결과")
print("=" * 60)

print("\n크기:")
print(social.shape)

print("\n앞 10행:")
print(social.head(10).to_string(index=False))

print("\n순이동 결측치 개수:")
print(social["Net_migration"].isna().sum())

print("\n결합된 기간:")
print(
    social["Date"].min(),
    "~",
    social["Date"].max()
)

print("\n지역 개수:")
print(social["Region_ko"].nunique())

# ==================================================
# 순이동 결측치 원인 확인
# ==================================================

missing = social[
    social["Net_migration"].isna()
].copy()

print("\n" + "=" * 60)
print("순이동 결측치 원인 확인")
print("=" * 60)

print("\n결측치 총 개수:")
print(len(missing))

print("\n결측치가 발생한 날짜:")
print(
    missing["Date"]
    .drop_duplicates()
    .sort_values()
    .to_string(index=False)
)

print("\n날짜별 결측 지역 개수:")
print(
    missing.groupby("Date")["Region_ko"]
    .count()
    .to_string()
)

print("\n지역별 결측치 개수:")
print(
    missing.groupby("Region_ko")
    .size()
    .sort_values(ascending=False)
    .to_string()
)
# ==================================================
# 17. 순이동 데이터가 없는 행 제외
# ==================================================

print("\n결측치 제거 전:", social.shape)

social = social.dropna(
    subset=["Net_migration"]
).copy()

print("결측치 제거 후:", social.shape)

print(
    "남은 순이동 결측치:",
    social["Net_migration"].isna().sum()
)
social = social.sort_values(
    ["Region_ko", "Date"]
).reset_index(drop=True)

output_path = "data/processed/social_monthly.csv"

social.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig"
)

print("\n저장 완료:")
print(output_path)

print("\n최종 데이터 크기:")
print(social.shape)

print("\n최종 기간:")
print(
    social["Date"].min(),
    "~",
    social["Date"].max()
)