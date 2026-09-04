import pandas as pd


# =========================
# 1. 데이터 불러오기
# =========================

# 팀별 경기 기록
team = pd.read_csv(
    "data/raw/edit_baseball_2019 (1).csv"
)

# 날씨
weather = pd.read_csv(
    "data/raw/edit_weather_2019.csv",
    encoding="cp949"
)

# 선수 시즌별 기록
player = pd.read_csv(
    "data/raw/Regular_Season_Batter.csv"
)

# 선수 날짜별 경기 기록
player_day = pd.read_csv(
    "data/raw/Regular_Season_Batter_Day_by_Day_b4.csv"
)


# =========================
# 2. 데이터 확인
# =========================

print("\n========== 1. 팀별 경기 데이터 ==========")
print(team.head())
print("\n컬럼:")
print(team.columns)
print("크기:", team.shape)


print("\n========== 2. 날씨 데이터 ==========")
print(weather.head())
print("\n컬럼:")
print(weather.columns)
print("크기:", weather.shape)


print("\n========== 3. 선수 시즌별 데이터 ==========")
print(player.head())
print("\n컬럼:")
print(player.columns)
print("크기:", player.shape)


print("\n========== 4. 선수 날짜별 데이터 ==========")
print(player_day.head())
print("\n컬럼:")
print(player_day.columns)
print("크기:", player_day.shape)