import pandas as pd


# =========================
# 1. 데이터 불러오기
# =========================

player = pd.read_csv(
    "data/raw/Regular_Season_Batter.csv"
)

player_day = pd.read_csv(
    "data/raw/Regular_Season_Batter_Day_by_Day_b4.csv"
)


# =========================
# 2. 2019년만 추출
# =========================

player_2019 = player[player["year"] == 2019].copy()

player_day_2019 = player_day[
    player_day["year"] == 2019
].copy()


print("2019 시즌 선수 수:", len(player_2019))
print("2019 선수 경기 기록 수:", len(player_day_2019))


# =========================
# 3. 선수의 소속팀 가져오기
# =========================

player_team = player_2019[
    ["batter_id", "batter_name", "year", "team"]
].copy()


# 선수 날짜별 데이터에 소속팀 추가
player_day_2019 = player_day_2019.merge(
    player_team,
    on=["batter_id", "batter_name", "year"],
    how="left"
)


print("\n===== 소속팀 추가 결과 =====")

print(
    player_day_2019[
        [
            "batter_name",
            "year",
            "date",
            "team",
            "opposing_team",
            "AB",
            "H",
            "HR",
            "RBI"
        ]
    ].head(20)
)


# =========================
# 4. 팀이 제대로 붙었는지 확인
# =========================

print("\n팀 정보 없는 행:")
print(player_day_2019["team"].isna().sum())

print("\n팀 종류:")
print(player_day_2019["team"].value_counts())
print("시즌별 데이터 연도:")
print(sorted(player["year"].unique()))

print("\n날짜별 데이터 연도:")
print(sorted(player_day["year"].unique()))

print("\n시즌별 데이터 최대 연도:", player["year"].max())
print("날짜별 데이터 최대 연도:", player_day["year"].max())