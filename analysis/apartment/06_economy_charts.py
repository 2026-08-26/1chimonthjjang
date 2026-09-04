import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path


# ==================================================
# 1. 파일 경로
# ==================================================

MONTHLY_PATH = "data/processed/economy_monthly.csv"

RATE_SIGNAL_PATH = "result/economy_rate_reverse_top10.csv"
CROSS_SIGNAL_PATH = "result/economy_price_volume_cross_top10.csv"

OUTPUT_DIR = Path("result/economy_charts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. 한글 폰트 설정
# ==================================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ==================================================
# 3. 디자인 설정
# ==================================================

BACKGROUND = "#0F1720"
PANEL = "#17212D"
TEXT = "#F8FAFC"
MUTED = "#AAB4C3"
GRID = "#334155"

PREVIOUS = "#5B7CFA"
CURRENT = "#FF6B4A"

POSITIVE = "#FF6B4A"
NEGATIVE = "#4DA3FF"


# ==================================================
# 4. 데이터 불러오기
# ==================================================

monthly = pd.read_csv(MONTHLY_PATH)

monthly["Date"] = pd.to_datetime(
    monthly["Date"],
    errors="coerce"
)


rate_top = pd.read_csv(RATE_SIGNAL_PATH)

rate_top["Date"] = pd.to_datetime(
    rate_top["Date"],
    errors="coerce"
)


cross_top = pd.read_csv(CROSS_SIGNAL_PATH)

cross_top["Date"] = pd.to_datetime(
    cross_top["Date"],
    errors="coerce"
)


# ==================================================
# 5. TOP1 자동 선택
# ==================================================

rate_case = rate_top.iloc[0]
cross_case = cross_top.iloc[0]


print("=" * 60)
print("경제 그래프 생성 시작")
print("=" * 60)

print("\nRATE REVERSE TOP1")
print(
    rate_case[
        [
            "Date",
            "Region",
            "Price_yoy_pct",
            "Base_rate_change",
            "Signal_score"
        ]
    ]
)

print("\nPRICE-VOLUME CROSS TOP1")
print(
    cross_case[
        [
            "Date",
            "Region",
            "Price_yoy_pct",
            "Transaction_yoy_pct",
            "Signal_score"
        ]
    ]
)


# ==================================================
# 6. 공통 함수
# ==================================================

def style_axis(ax):

    ax.set_facecolor(PANEL)

    ax.tick_params(
        colors=MUTED,
        labelsize=11
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.grid(
        axis="y",
        color=GRID,
        alpha=0.45,
        linestyle="--",
        linewidth=0.8
    )

    ax.set_axisbelow(True)


def add_bar_labels(
    ax,
    bars,
    labels
):

    for bar, label in zip(
        bars,
        labels
    ):

        height = bar.get_height()

        if height >= 0:
            y = height
            va = "bottom"
            offset = 5

        else:
            y = height
            va = "top"
            offset = -5

        ax.annotate(
            label,
            xy=(
                bar.get_x()
                + bar.get_width() / 2,
                y
            ),
            xytext=(0, offset),
            textcoords="offset points",
            ha="center",
            va=va,
            fontsize=13,
            fontweight="bold",
            color=TEXT
        )


def add_tip_box(
    fig,
    title,
    text
):

    box = FancyBboxPatch(
        (0.06, 0.035),
        0.88,
        0.10,
        transform=fig.transFigure,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        facecolor=PANEL,
        edgecolor=GRID,
        linewidth=1.2
    )

    fig.patches.append(box)

    fig.text(
        0.085,
        0.105,
        title,
        color=TEXT,
        fontsize=13,
        fontweight="bold"
    )

    fig.text(
        0.085,
        0.061,
        text,
        color=MUTED,
        fontsize=11
    )


# ==================================================
# 7. SIGNAL 1
#    기준금리 ↑ + 가격 ↑
# ==================================================

region = rate_case["Region"]
date = rate_case["Date"]

previous_price = float(
    rate_case["Price_prev_year"]
)

current_price = float(
    rate_case["Median_price_per_m2"]
)

price_change = float(
    rate_case["Price_yoy_pct"]
)

previous_rate = float(
    rate_case["Base_rate_prev_year"]
)

current_rate = float(
    rate_case["Base_rate"]
)

rate_change = float(
    rate_case["Base_rate_change"]
)

score = float(
    rate_case["Signal_score"]
)


fig = plt.figure(
    figsize=(14, 8),
    facecolor=BACKGROUND
)


# --------------------------------------------------
# 제목
# --------------------------------------------------

fig.text(
    0.06,
    0.93,
    "SIGNAL 1  |  기준금리 ↑ + 아파트 가격 ↑",
    fontsize=23,
    fontweight="bold",
    color=TEXT
)

fig.text(
    0.06,
    0.885,
    f"{date.strftime('%Y년 %m월')} · {region}",
    fontsize=14,
    color=MUTED
)

fig.text(
    0.94,
    0.925,
    f"신호 점수  {score:.2f}",
    fontsize=13,
    fontweight="bold",
    color=POSITIVE,
    ha="right"
)


# --------------------------------------------------
# 가격 그래프
# --------------------------------------------------

ax1 = fig.add_axes(
    [0.07, 0.28, 0.40, 0.49]
)

style_axis(ax1)

bars1 = ax1.bar(
    [
        "전년 동월",
        "현재"
    ],
    [
        previous_price,
        current_price
    ]
)

bars1[0].set_color(PREVIOUS)
bars1[1].set_color(CURRENT)


ax1.set_title(
    "아파트 ㎡당 중앙가격",
    fontsize=16,
    fontweight="bold",
    color=TEXT,
    pad=18
)

ax1.set_ylabel(
    "만원 / ㎡",
    color=MUTED,
    fontsize=11
)


add_bar_labels(
    ax1,
    bars1,
    [
        f"{previous_price:,.1f}",
        f"{current_price:,.1f}"
    ]
)


ax1.text(
    0.5,
    0.93,
    f"+{price_change:.1f}%",
    transform=ax1.transAxes,
    ha="center",
    fontsize=16,
    fontweight="bold",
    color=POSITIVE
)


# --------------------------------------------------
# 금리 그래프
# --------------------------------------------------

ax2 = fig.add_axes(
    [0.54, 0.28, 0.39, 0.49]
)

style_axis(ax2)

bars2 = ax2.bar(
    [
        "전년 동월",
        "현재"
    ],
    [
        previous_rate,
        current_rate
    ]
)

bars2[0].set_color(PREVIOUS)
bars2[1].set_color(CURRENT)


ax2.set_title(
    "한국은행 기준금리",
    fontsize=16,
    fontweight="bold",
    color=TEXT,
    pad=18
)

ax2.set_ylabel(
    "%",
    color=MUTED,
    fontsize=11
)


add_bar_labels(
    ax2,
    bars2,
    [
        f"{previous_rate:.1f}%",
        f"{current_rate:.1f}%"
    ]
)


ax2.text(
    0.5,
    0.93,
    f"+{rate_change:.1f}%p",
    transform=ax2.transAxes,
    ha="center",
    fontsize=16,
    fontweight="bold",
    color=POSITIVE
)


# --------------------------------------------------
# 핵심 제보 문구
# --------------------------------------------------

tip_text = (
    f"기준금리가 {previous_rate:.1f}% → {current_rate:.1f}%로 높아진 같은 시기, "
    f"{region}의 아파트 ㎡당 중앙가격은 "
    f"{previous_price:,.1f} → {current_price:,.1f}만원으로 "
    f"{price_change:.1f}% 상승했습니다."
)

add_tip_box(
    fig,
    "💡 핵심 제보",
    tip_text
)


rate_output = (
    OUTPUT_DIR
    / "economy_rate_reverse_top1.png"
)

plt.savefig(
    rate_output,
    dpi=200,
    bbox_inches="tight",
    facecolor=BACKGROUND
)

plt.close()


# ==================================================
# 8. SIGNAL 2
#    가격 ↑ + 거래량 ↓
# ==================================================

region = cross_case["Region"]
date = cross_case["Date"]

previous_price = float(
    cross_case["Price_prev_year"]
)

current_price = float(
    cross_case["Median_price_per_m2"]
)

price_change = float(
    cross_case["Price_yoy_pct"]
)

previous_transactions = int(
    cross_case["Transaction_prev_year"]
)

current_transactions = int(
    cross_case["Transaction_count"]
)

transaction_change = float(
    cross_case["Transaction_yoy_pct"]
)

score = float(
    cross_case["Signal_score"]
)


fig = plt.figure(
    figsize=(14, 8),
    facecolor=BACKGROUND
)


# --------------------------------------------------
# 제목
# --------------------------------------------------

fig.text(
    0.06,
    0.93,
    "SIGNAL 2  |  가격 ↑ + 거래량 ↓",
    fontsize=23,
    fontweight="bold",
    color=TEXT
)

fig.text(
    0.06,
    0.885,
    f"{date.strftime('%Y년 %m월')} · {region}",
    fontsize=14,
    color=MUTED
)

fig.text(
    0.94,
    0.925,
    f"신호 점수  {score:.2f}",
    fontsize=13,
    fontweight="bold",
    color=NEGATIVE,
    ha="right"
)


# --------------------------------------------------
# 가격 그래프
# --------------------------------------------------

ax1 = fig.add_axes(
    [0.07, 0.28, 0.40, 0.49]
)

style_axis(ax1)

bars1 = ax1.bar(
    [
        "전년 동월",
        "현재"
    ],
    [
        previous_price,
        current_price
    ]
)

bars1[0].set_color(PREVIOUS)
bars1[1].set_color(CURRENT)


ax1.set_title(
    "아파트 ㎡당 중앙가격",
    fontsize=16,
    fontweight="bold",
    color=TEXT,
    pad=18
)

ax1.set_ylabel(
    "만원 / ㎡",
    color=MUTED,
    fontsize=11
)


add_bar_labels(
    ax1,
    bars1,
    [
        f"{previous_price:,.1f}",
        f"{current_price:,.1f}"
    ]
)


ax1.text(
    0.5,
    0.93,
    f"+{price_change:.1f}%",
    transform=ax1.transAxes,
    ha="center",
    fontsize=16,
    fontweight="bold",
    color=POSITIVE
)


# --------------------------------------------------
# 거래량 그래프
# --------------------------------------------------

ax2 = fig.add_axes(
    [0.54, 0.28, 0.39, 0.49]
)

style_axis(ax2)

bars2 = ax2.bar(
    [
        "전년 동월",
        "현재"
    ],
    [
        previous_transactions,
        current_transactions
    ]
)

bars2[0].set_color(PREVIOUS)
bars2[1].set_color(NEGATIVE)


ax2.set_title(
    "아파트 거래량",
    fontsize=16,
    fontweight="bold",
    color=TEXT,
    pad=18
)

ax2.set_ylabel(
    "건",
    color=MUTED,
    fontsize=11
)


add_bar_labels(
    ax2,
    bars2,
    [
        f"{previous_transactions:,}건",
        f"{current_transactions:,}건"
    ]
)


ax2.text(
    0.5,
    0.93,
    f"{transaction_change:.1f}%",
    transform=ax2.transAxes,
    ha="center",
    fontsize=16,
    fontweight="bold",
    color=NEGATIVE
)


# --------------------------------------------------
# 핵심 제보 문구
# --------------------------------------------------

tip_text = (
    f"{region}의 아파트 ㎡당 중앙가격은 전년 동월보다 "
    f"{price_change:.1f}% 상승했지만, 거래량은 "
    f"{previous_transactions:,}건 → {current_transactions:,}건으로 "
    f"{abs(transaction_change):.1f}% 감소했습니다."
)

add_tip_box(
    fig,
    "💡 핵심 제보",
    tip_text
)


cross_output = (
    OUTPUT_DIR
    / "economy_price_volume_cross_top1.png"
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

print("\n" + "=" * 60)
print("경제 그래프 생성 완료!")
print("=" * 60)

print("\n저장 위치:")
print(rate_output)
print(cross_output)