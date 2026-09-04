import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ==================================================
# 1. 파일 경로
# ==================================================

RATE_PATH = "result/economy_rate_reverse_top10.csv"
CROSS_PATH = "result/economy_price_volume_cross_top10.csv"

OUTPUT_DIR = Path("result/economy_tables")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. 한글 폰트
# ==================================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ==================================================
# 3. 색상
# ==================================================

BACKGROUND = "#0F1720"
HEADER = "#17212D"
ROW = "#111C27"
EDGE = "#334155"

TEXT = "#F8FAFC"
MUTED = "#CBD5E1"

RED = "#FF6B4A"
BLUE = "#4DA3FF"


# ==================================================
# 4. 데이터 불러오기
# ==================================================

rate = pd.read_csv(RATE_PATH)
cross = pd.read_csv(CROSS_PATH)

rate["Date"] = pd.to_datetime(rate["Date"])
cross["Date"] = pd.to_datetime(cross["Date"])


# ==================================================
# 5. SIGNAL 1 표 데이터 정리
# ==================================================

rate_table = pd.DataFrame({
    "순위": range(1, len(rate) + 1),

    "날짜": rate["Date"].dt.strftime("%Y-%m"),

    "지역": rate["Region"],

    "전년 가격\n(만원/㎡)":
        rate["Price_prev_year"]
        .map(lambda x: f"{x:,.1f}"),

    "현재 가격\n(만원/㎡)":
        rate["Median_price_per_m2"]
        .map(lambda x: f"{x:,.1f}"),

    "가격 변화":
        rate["Price_yoy_pct"]
        .map(lambda x: f"+{x:.1f}%"),

    "전년 금리":
        rate["Base_rate_prev_year"]
        .map(lambda x: f"{x:.1f}%"),

    "현재 금리":
        rate["Base_rate"]
        .map(lambda x: f"{x:.1f}%"),

    "금리 변화":
        rate["Base_rate_change"]
        .map(lambda x: f"+{x:.1f}%p"),

    "신호 점수":
        rate["Signal_score"]
        .map(lambda x: f"{x:.2f}")
})


# ==================================================
# 6. SIGNAL 1 표 그리기
# ==================================================

fig, ax = plt.subplots(
    figsize=(18, 8)
)

fig.patch.set_facecolor(BACKGROUND)
ax.set_facecolor(BACKGROUND)
ax.axis("off")


# 제목
fig.text(
    0.05,
    0.93,
    "SIGNAL 1  |  기준금리 ↑ + 가격 ↑ TOP 10",
    fontsize=24,
    fontweight="bold",
    color=TEXT
)

fig.text(
    0.05,
    0.875,
    "금리가 전년보다 높아졌는데도 아파트 가격이 함께 상승한 지역",
    fontsize=13,
    color=MUTED
)


table = ax.table(
    cellText=rate_table.values,
    colLabels=rate_table.columns,
    cellLoc="center",
    colLoc="center",
    bbox=[
        0.02,
        0.05,
        0.96,
        0.74
    ]
)


table.auto_set_font_size(False)
table.set_fontsize(11)


# 셀 스타일
for (row, col), cell in table.get_celld().items():

    cell.set_edgecolor(EDGE)
    cell.set_linewidth(0.8)

    if row == 0:

        cell.set_facecolor(HEADER)

        cell.get_text().set_color(TEXT)
        cell.get_text().set_fontweight("bold")

    else:

        cell.set_facecolor(ROW)
        cell.get_text().set_color(TEXT)


# 가격 변화 열 강조
price_col = list(
    rate_table.columns
).index("가격 변화")


for row in range(
    1,
    len(rate_table) + 1
):

    table[
        row,
        price_col
    ].get_text().set_color(RED)

    table[
        row,
        price_col
    ].get_text().set_fontweight("bold")


# 신호점수 강조
score_col = list(
    rate_table.columns
).index("신호 점수")


for row in range(
    1,
    len(rate_table) + 1
):

    table[
        row,
        score_col
    ].get_text().set_color(RED)

    table[
        row,
        score_col
    ].get_text().set_fontweight("bold")


rate_output = (
    OUTPUT_DIR
    / "economy_rate_reverse_top10_table.png"
)


plt.savefig(
    rate_output,
    dpi=200,
    bbox_inches="tight",
    facecolor=BACKGROUND
)

plt.close()


# ==================================================
# 7. SIGNAL 2 표 데이터 정리
# ==================================================

cross_table = pd.DataFrame({
    "순위": range(1, len(cross) + 1),

    "날짜": cross["Date"].dt.strftime("%Y-%m"),

    "지역": cross["Region"],

    "전년 가격\n(만원/㎡)":
        cross["Price_prev_year"]
        .map(lambda x: f"{x:,.1f}"),

    "현재 가격\n(만원/㎡)":
        cross["Median_price_per_m2"]
        .map(lambda x: f"{x:,.1f}"),

    "가격 변화":
        cross["Price_yoy_pct"]
        .map(lambda x: f"+{x:.1f}%"),

    "전년 거래량":
        cross["Transaction_prev_year"]
        .map(lambda x: f"{int(x):,}"),

    "현재 거래량":
        cross["Transaction_count"]
        .map(lambda x: f"{int(x):,}"),

    "거래량 변화":
        cross["Transaction_yoy_pct"]
        .map(lambda x: f"{x:.1f}%"),

    "신호 점수":
        cross["Signal_score"]
        .map(lambda x: f"{x:.2f}")
})


# ==================================================
# 8. SIGNAL 2 표 그리기
# ==================================================

fig, ax = plt.subplots(
    figsize=(18, 8)
)

fig.patch.set_facecolor(BACKGROUND)
ax.set_facecolor(BACKGROUND)
ax.axis("off")


fig.text(
    0.05,
    0.93,
    "SIGNAL 2  |  가격 ↑ + 거래량 ↓ TOP 10",
    fontsize=24,
    fontweight="bold",
    color=TEXT
)

fig.text(
    0.05,
    0.875,
    "아파트 가격은 상승했지만 거래 건수는 감소한 지역",
    fontsize=13,
    color=MUTED
)


table = ax.table(
    cellText=cross_table.values,
    colLabels=cross_table.columns,
    cellLoc="center",
    colLoc="center",
    bbox=[
        0.02,
        0.05,
        0.96,
        0.74
    ]
)


table.auto_set_font_size(False)
table.set_fontsize(11)


for (row, col), cell in table.get_celld().items():

    cell.set_edgecolor(EDGE)
    cell.set_linewidth(0.8)

    if row == 0:

        cell.set_facecolor(HEADER)

        cell.get_text().set_color(TEXT)
        cell.get_text().set_fontweight("bold")

    else:

        cell.set_facecolor(ROW)
        cell.get_text().set_color(TEXT)


# 가격 변화 빨간색
price_col = list(
    cross_table.columns
).index("가격 변화")


# 거래량 변화 파란색
volume_col = list(
    cross_table.columns
).index("거래량 변화")


# 신호 점수 파란색
score_col = list(
    cross_table.columns
).index("신호 점수")


for row in range(
    1,
    len(cross_table) + 1
):

    table[
        row,
        price_col
    ].get_text().set_color(RED)

    table[
        row,
        price_col
    ].get_text().set_fontweight("bold")

    table[
        row,
        volume_col
    ].get_text().set_color(BLUE)

    table[
        row,
        volume_col
    ].get_text().set_fontweight("bold")

    table[
        row,
        score_col
    ].get_text().set_color(BLUE)

    table[
        row,
        score_col
    ].get_text().set_fontweight("bold")


cross_output = (
    OUTPUT_DIR
    / "economy_price_volume_cross_top10_table.png"
)


plt.savefig(
    cross_output,
    dpi=200,
    bbox_inches="tight",
    facecolor=BACKGROUND
)

plt.close()


# ==================================================
# 9. 완료
# ==================================================

print("=" * 60)
print("경제 TOP10 표 이미지 생성 완료!")
print("=" * 60)

print("\n저장 위치:")
print(rate_output)
print(cross_output)