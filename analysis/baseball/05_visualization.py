import pandas as pd
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. 한글 폰트 설정
# ==========================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ==========================================
# 2. 분석 결과 CSV 불러오기
# ==========================================

temp = pd.read_csv("data/processed/temp_signal.csv")
humidity = pd.read_csv("data/processed/humidity_signal.csv")
rain = pd.read_csv("data/processed/rain_signal.csv")

print("===== CSV 불러오기 완료 =====")
print("기온:", temp.shape)
print("습도:", humidity.shape)
print("비:", rain.shape)


# ==========================================
# 3. 그래프 저장 폴더 생성
# ==========================================

os.makedirs("static/images", exist_ok=True)


# ==========================================
# 4. 🌡 기온 이상 신호 TOP 10
# ==========================================

temp_top = (
    temp
    .assign(signal_strength=temp["signal_score"].abs())
    .sort_values("signal_strength", ascending=False)
    .head(10)
    .sort_values("weather_diff")
)

labels = (
    temp_top["player_name"]
    + " ("
    + temp_top["temp_group"]
    + ")"
)

plt.figure(figsize=(10, 6))

plt.barh(
    labels,
    temp_top["weather_diff"]
)

plt.axvline(0, linewidth=1)

plt.title("기온에 따른 선수 타율 이상 신호 TOP 10")
plt.xlabel("평소 타율 대비 변화")
plt.ylabel("선수")

plt.tight_layout()

plt.savefig(
    "static/images/temp_signal.png",
    dpi=150,
    bbox_inches="tight"
)

plt.show()
plt.close()


# ==========================================
# 5. 💧 습도 이상 신호 TOP 10
# ==========================================

humidity_top = (
    humidity
    .assign(signal_strength=humidity["signal_score"].abs())
    .sort_values("signal_strength", ascending=False)
    .head(10)
    .sort_values("weather_diff")
)

labels = (
    humidity_top["player_name"]
    + " ("
    + humidity_top["humidity_group"]
    + ")"
)

plt.figure(figsize=(10, 6))

plt.barh(
    labels,
    humidity_top["weather_diff"]
)

plt.axvline(0, linewidth=1)

plt.title("습도에 따른 선수 타율 이상 신호 TOP 10")
plt.xlabel("평소 타율 대비 변화")
plt.ylabel("선수")

plt.tight_layout()

plt.savefig(
    "static/images/humidity_signal.png",
    dpi=150,
    bbox_inches="tight"
)

plt.show()
plt.close()


# ==========================================
# 6. 🌧 비 오는 날 이상 신호 TOP 10
# ==========================================

rain_only = rain[rain["rain_group"] == "비"].copy()

rain_top = (
    rain_only
    .assign(signal_strength=rain_only["signal_score"].abs())
    .sort_values("signal_strength", ascending=False)
    .head(10)
    .sort_values("weather_diff")
)

plt.figure(figsize=(10, 6))

plt.barh(
    rain_top["player_name"],
    rain_top["weather_diff"]
)

plt.axvline(0, linewidth=1)

plt.title("비 오는 날 선수 타율 이상 신호 TOP 10")
plt.xlabel("평소 타율 대비 변화")
plt.ylabel("선수")

plt.tight_layout()

plt.savefig(
    "static/images/rain_signal.png",
    dpi=150,
    bbox_inches="tight"
)

plt.show()
plt.close()


# ==========================================
# 7. 이대호 습도별 타율 비교
# ==========================================

lee = humidity[
    humidity["player_name"] == "이대호"
].copy()

# 평소 타율
season_avg = lee["season_avg"].iloc[0]

# 평소 데이터 추가
normal_row = pd.DataFrame({
    "humidity_group": ["평소"],
    "weather_avg": [season_avg]
})

lee_chart = pd.concat([
    lee[["humidity_group", "weather_avg"]],
    normal_row
])

# 원하는 순서
order = ["건조", "평소", "보통", "습함"]

lee_chart["order"] = lee_chart["humidity_group"].map(
    {name: i for i, name in enumerate(order)}
)

lee_chart = lee_chart.sort_values("order")


plt.figure(figsize=(8, 5))

bars = plt.bar(
    lee_chart["humidity_group"],
    lee_chart["weather_avg"]
)

plt.title("이대호 - 습도에 따른 타율 변화")
plt.xlabel("습도 조건")
plt.ylabel("타율")

plt.ylim(0, max(lee_chart["weather_avg"]) + 0.1)


# 막대 위에 타율 표시
for bar, value in zip(bars, lee_chart["weather_avg"]):

    plt.text(
        bar.get_x() + bar.get_width() / 2,
        value + 0.01,
        f"{value:.3f}",
        ha="center"
    )


plt.tight_layout()

plt.savefig(
    "static/images/lee_daeho_humidity.png",
    dpi=150,
    bbox_inches="tight"
)

plt.show()
plt.close()


print("\n===== 시각화 완료 =====")
print("static/images 폴더에 그래프 4개 저장 완료")