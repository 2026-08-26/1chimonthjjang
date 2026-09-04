import pandas as pd
import numpy as np

# ==========================================
# 1. 데이터 불러오기
# ==========================================
data = pd.read_csv("data/processed/baseball_weather_2019.csv")

data["game_date"] = pd.to_datetime(data["game_date"])

print("===== 데이터 확인 =====")
print(data.shape)
print(data.columns.tolist())


# ==========================================
# 2. 실제 타수 있는 기록만 사용
# ==========================================
# AB=0인 경우 대주자/대수비 등일 수 있기 때문에
# 타격 분석에서는 제외
batting = data[data["AB"] > 0].copy()

print("\n===== 타격 기록 =====")
print("전체 기록:", len(data))
print("AB > 0 기록:", len(batting))
print("선수 수:", batting["player_name"].nunique())


# ==========================================
# 3. 경기별 타율 계산
# ==========================================
batting["game_avg"] = batting["H"] / batting["AB"]

print("\n===== 경기별 타율 =====")
print(
    batting[
        ["game_date", "player_name", "AB", "H", "game_avg"]
    ].head(10)
)


# ==========================================
# 4. 선수별 시즌 기준 성적 계산
# ==========================================
player_base = (
    batting.groupby("player_name")
    .agg(
        games=("gameinfo", "nunique"),
        total_AB=("AB", "sum"),
        total_H=("H", "sum"),
        total_RBI=("RBI", "sum")
    )
    .reset_index()
)

# 시즌 타율
# 경기별 타율의 평균을 내는 것이 아니라
# 전체 안타 / 전체 타수로 계산
player_base["season_avg"] = (
    player_base["total_H"] / player_base["total_AB"]
)

print("\n===== 선수별 기준 성적 =====")
print(
    player_base
    .sort_values("season_avg", ascending=False)
    .head(20)
)


# ==========================================
# 5. 기준 성적을 원래 데이터에 연결
# ==========================================
batting = batting.merge(
    player_base[
        ["player_name", "games", "total_AB", "season_avg"]
    ],
    on="player_name",
    how="left"
)


# ==========================================
# 6. 평소 타율 대비 경기 성적 변화
# ==========================================
batting["avg_diff"] = (
    batting["game_avg"] - batting["season_avg"]
)

print("\n===== 선수 평소 성적 대비 경기 성적 =====")

print(
    batting[
        [
            "game_date",
            "player_name",
            "AB",
            "H",
            "game_avg",
            "season_avg",
            "avg_diff",
            "temperature",
            "rainfall",
            "humidity",
            "wind_speed"
        ]
    ].head(20)
)
# ==========================================
# 7. 분석 가능한 선수만 선택
# ==========================================

# 시즌 100타수 이상 선수만 사용
analysis_data = batting[batting["total_AB"] >= 100].copy()

print("\n===== 분석 대상 필터링 =====")
print("필터링 전 선수 수:", batting["player_name"].nunique())
print("100타수 이상 선수 수:", analysis_data["player_name"].nunique())
print("분석 기록 수:", len(analysis_data))


# ==========================================
# 8. 날씨 범주 만들기
# ==========================================

# 기온
analysis_data["temp_group"] = pd.cut(
    analysis_data["temperature"],
    bins=[-np.inf, 15, 25, np.inf],
    labels=["추움", "보통", "더움"]
)

# 습도
analysis_data["humidity_group"] = pd.cut(
    analysis_data["humidity"],
    bins=[-np.inf, 50, 70, np.inf],
    labels=["건조", "보통", "습함"]
)

# 비
analysis_data["rain_group"] = np.where(
    analysis_data["rainfall"] > 0,
    "비",
    "비없음"
)


print("\n===== 날씨 범주 확인 =====")

print("\n[기온]")
print(analysis_data["temp_group"].value_counts())

print("\n[습도]")
print(analysis_data["humidity_group"].value_counts())

print("\n[강수]")
print(analysis_data["rain_group"].value_counts())


# ==========================================
# 9. 선수 × 기온별 성적
# ==========================================

temp_stats = (
    analysis_data
    .groupby(
        ["player_name", "temp_group"],
        observed=True
    )
    .agg(
        games=("gameinfo", "nunique"),
        AB=("AB", "sum"),
        H=("H", "sum"),
        RBI=("RBI", "sum"),
        season_avg=("season_avg", "first"),
        avg_diff_mean=("avg_diff", "mean")
    )
    .reset_index()
)

# 해당 날씨에서 실제 타율
temp_stats["weather_avg"] = (
    temp_stats["H"] / temp_stats["AB"]
)

# 시즌 타율과 차이
temp_stats["weather_diff"] = (
    temp_stats["weather_avg"]
    - temp_stats["season_avg"]
)


print("\n===== 기온에 따른 선수 성적 =====")
print(
    temp_stats
    .sort_values("weather_diff", ascending=False)
    .head(20)
)


# ==========================================
# 10. 선수 × 습도별 성적
# ==========================================

humidity_stats = (
    analysis_data
    .groupby(
        ["player_name", "humidity_group"],
        observed=True
    )
    .agg(
        games=("gameinfo", "nunique"),
        AB=("AB", "sum"),
        H=("H", "sum"),
        season_avg=("season_avg", "first")
    )
    .reset_index()
)

humidity_stats["weather_avg"] = (
    humidity_stats["H"] / humidity_stats["AB"]
)

humidity_stats["weather_diff"] = (
    humidity_stats["weather_avg"]
    - humidity_stats["season_avg"]
)


print("\n===== 습도에 따른 선수 성적 =====")
print(
    humidity_stats
    .sort_values("weather_diff", ascending=False)
    .head(20)
)


# ==========================================
# 11. 선수 × 비 여부별 성적
# ==========================================

rain_stats = (
    analysis_data
    .groupby(
        ["player_name", "rain_group"]
    )
    .agg(
        games=("gameinfo", "nunique"),
        AB=("AB", "sum"),
        H=("H", "sum"),
        season_avg=("season_avg", "first")
    )
    .reset_index()
)

rain_stats["weather_avg"] = (
    rain_stats["H"] / rain_stats["AB"]
)

rain_stats["weather_diff"] = (
    rain_stats["weather_avg"]
    - rain_stats["season_avg"]
)


print("\n===== 비 여부에 따른 선수 성적 =====")
print(
    rain_stats
    .sort_values("weather_diff", ascending=False)
    .head(20)
)
# ==========================================
# 12. 신뢰 가능한 이상 신호 만들기
# ==========================================

# 조건별 최소 타수
MIN_CONDITION_AB = 30


def make_signal(df, condition_col):

    # 해당 날씨에서 30타수 이상인 경우만 사용
    signal = df[df["AB"] >= MIN_CONDITION_AB].copy()

    # 표본 크기 가중치
    # 타수가 많을수록 신뢰도를 조금 더 높임
    signal["sample_weight"] = np.sqrt(signal["AB"])

    # 이상 신호 점수
    signal["signal_score"] = (
        signal["weather_diff"] *
        signal["sample_weight"]
    )

    # 절대값도 생성
    # 잘한 선수 / 못한 선수 모두 탐지하기 위해 사용
    signal["signal_strength"] = (
        signal["signal_score"].abs()
    )

    return signal


temp_signal = make_signal(
    temp_stats,
    "temp_group"
)

humidity_signal = make_signal(
    humidity_stats,
    "humidity_group"
)

rain_signal = make_signal(
    rain_stats,
    "rain_group"
)


# ==========================================
# 13. 기온 이상 신호 TOP
# ==========================================

print("\n===== 🔥 기온 이상 신호 TOP 15 =====")

print(
    temp_signal
    .sort_values(
        "signal_strength",
        ascending=False
    )
    .head(15)[
        [
            "player_name",
            "temp_group",
            "games",
            "AB",
            "season_avg",
            "weather_avg",
            "weather_diff",
            "signal_score"
        ]
    ]
)

# ==========================================
# 14. 습도 이상 신호 TOP
# ==========================================

print("\n===== 💧 습도 이상 신호 TOP 15 =====")

print(
    humidity_signal
    .sort_values(
        "signal_strength",
        ascending=False
    )
    .head(15)[
        [
            "player_name",
            "humidity_group",
            "games",
            "AB",
            "season_avg",
            "weather_avg",
            "weather_diff",
            "signal_score"
        ]
    ]
)


# =========================================================
# 🌧 비 이상 신호
# =========================================================

# signal_score의 절댓값 = 이상 신호의 강도
rain_signal["signal_strength"] = rain_signal["signal_score"].abs()

print("\n===== 🌧 비 이상 신호 TOP 15 =====")

print(
    rain_signal
    .sort_values("signal_strength", ascending=False)
    .head(15)[
        [
            "player_name",
            "rain_group",
            "games",
            "AB",
            "season_avg",
            "weather_avg",
            "weather_diff",
            "signal_score"
        ]
    ]
)


# =========================================================
# 🌧 비 오는 날만 따로 추출
# =========================================================

rain_only = rain_signal[
    rain_signal["rain_group"] == "비"
].copy()

print("\n===== 🌧 비 오는 날 특이 선수 TOP 15 =====")

print(
    rain_only
    .sort_values("signal_strength", ascending=False)
    .head(15)[
        [
            "player_name",
            "games",
            "AB",
            "season_avg",
            "weather_avg",
            "weather_diff",
            "signal_score"
        ]
    ]
)



# ==========================================
# 15. 비 이상 신호 TOP
# ==========================================

# ==========================================
# 분석 결과 CSV 저장
# ==========================================

temp_signal.to_csv(
    "data/processed/temp_signal.csv",
    index=False,
    encoding="utf-8-sig"
)

humidity_signal.to_csv(
    "data/processed/humidity_signal.csv",
    index=False,
    encoding="utf-8-sig"
)

rain_signal.to_csv(
    "data/processed/rain_signal.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n===== 분석 결과 저장 완료 =====")