import pandas as pd

# 전처리 끝난 야구 데이터
baseball = pd.read_csv("data/processed/baseball_2019_merged.csv")

# 날씨 원본 데이터
weather = pd.read_csv(
    "data/raw/edit_weather_2019.csv",
    encoding="cp949"
)

print("===== 야구 데이터 =====")
print(baseball.shape)
print(baseball.columns.tolist())
print(baseball.head())

print("\n===== 날씨 데이터 =====")
print(weather.shape)
print(weather.columns.tolist())
print(weather.head())

print("\n===== 날씨 데이터 정보 =====")
weather.info()

print("\n===== 날씨 지점 종류 =====")
print(weather["지점명"].unique())

print("\n지점 수:", weather["지점명"].nunique())

print("\n===== 지점별 데이터 수 =====")
print(weather["지점명"].value_counts())

# ==========================================
# 1. gameinfo에서 홈팀 추출
# ==========================================

# 예: 20190402KTOB0
# 날짜 8자리 뒤:
# KT = 원정팀
# OB = 홈팀
# 마지막 0 = 경기 구분
baseball["home_team"] = baseball["gameinfo"].str[10:12]

print("\n===== 홈팀 추출 확인 =====")
print(
    baseball[
        ["gameinfo", "team", "opponent", "home_team"]
    ].head(20)
)

print("\n===== 홈팀 종류 =====")
print(baseball["home_team"].unique())

# ==========================================
# 2. 홈팀 → 경기 지역 매핑
# ==========================================

stadium_region = {
    "OB": "서울",   # 두산 - 잠실
    "LG": "서울",   # LG - 잠실
    "WO": "서울",   # 키움 - 고척
    "SK": "인천",   # SK - 문학
    "KT": "수원",   # KT - 수원
    "HH": "대전",   # 한화 - 대전
    "SS": "대구",   # 삼성 - 대구
    "NC": "창원",   # NC - 창원
    "HT": "광주",   # KIA - 광주
    "LT": "부산"    # 롯데 - 사직
}

baseball["region"] = baseball["home_team"].map(stadium_region)

print("\n===== 경기 지역 연결 확인 =====")
print(
    baseball[
        ["gameinfo", "team", "opponent", "home_team", "region"]
    ].drop_duplicates().head(20)
)

print("\n지역 연결 실패:")
print(baseball["region"].isna().sum())


# ==========================================
# 3. 날씨 날짜/시간 처리
# ==========================================

weather["datetime"] = pd.to_datetime(weather["일시"])

weather["game_date"] = weather["datetime"].dt.normalize()
weather["hour"] = weather["datetime"].dt.hour

# 야구 데이터 날짜도 datetime으로 통일
baseball["game_date"] = pd.to_datetime(baseball["game_date"]).dt.normalize()

print("\n===== 날씨 날짜/시간 변환 확인 =====")
print(
    weather[
        ["지점명", "일시", "datetime", "game_date", "hour"]
    ].head(10)
)
# ==========================================
# 4. 지역 + 날짜별 날씨 요약
# ==========================================

daily_weather = (
    weather
    .groupby(["지점명", "game_date"])
    .agg({
        "기온(°C)": "mean",
        "강수량(mm)": "sum",
        "풍속(m/s)": "mean",
        "습도(%)": "mean",
        "현지기압(hPa)": "mean",
        "지면온도(°C)": "mean"
    })
    .reset_index()
)

# 컬럼 이름을 분석하기 쉽게 변경
daily_weather = daily_weather.rename(columns={
    "지점명": "region",
    "기온(°C)": "temperature",
    "강수량(mm)": "rainfall",
    "풍속(m/s)": "wind_speed",
    "습도(%)": "humidity",
    "현지기압(hPa)": "pressure",
    "지면온도(°C)": "ground_temp"
})

print("\n===== 날짜 + 지역별 날씨 =====")
print(daily_weather.head(20))

print("\n날씨 요약 데이터 크기:")
print(daily_weather.shape)


# ==========================================
# 5. 야구 + 날씨 MERGE
# ==========================================

final_data = baseball.merge(
    daily_weather,
    on=["game_date", "region"],
    how="left"
)

print("\n===== 야구 + 날씨 최종 연결 =====")

print(
    final_data[
        [
            "game_date",
            "gameinfo",
            "player_name",
            "team",
            "opponent",
            "region",
            "H",
            "AB",
            "RBI",
            "temperature",
            "rainfall",
            "humidity",
            "wind_speed"
        ]
    ].head(30)
)


# ==========================================
# 6. 연결 상태 검사
# ==========================================

print("\n===== 날씨 연결 상태 =====")
print("전체 선수 기록:", len(final_data))
print(
    "날씨 연결 성공:",
    final_data["temperature"].notna().sum()
)
print(
    "날씨 연결 실패:",
    final_data["temperature"].isna().sum()
)

print("\n날씨 연결 실패 날짜:")
print(
    final_data.loc[
        final_data["temperature"].isna(),
        ["game_date", "region"]
    ].drop_duplicates()
)


# ==========================================
# 7. 최종 저장
# ==========================================

final_data.to_csv(
    "data/processed/baseball_weather_2019.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n저장 완료!")
print("data/processed/baseball_weather_2019.csv")