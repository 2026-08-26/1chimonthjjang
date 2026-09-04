import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


# ==================================================
# 1. 분석 결과 불러오기
# ==================================================

cross_top = pd.read_csv(
    "result/social_cross_top10.csv"
)

decline_top = pd.read_csv(
    "result/social_decline_top10.csv"
)

social = pd.read_csv(
    "data/processed/social_monthly.csv"
)

social["Date"] = pd.to_datetime(
    social["Date"],
    errors="coerce"
)

cross_top["Date"] = pd.to_datetime(
    cross_top["Date"],
    errors="coerce"
)

decline_top["Date"] = pd.to_datetime(
    decline_top["Date"],
    errors="coerce"
)


# ==================================================
# 2. TOP 1 자동 선택
# ==================================================

cross_top1 = cross_top.iloc[0]
decline_top1 = decline_top.iloc[0]

print("인구 엇갈림 1위:")
print(cross_top1[["Date", "Region_ko", "Signal_score"]])

print("\n인구 이중감소 1위:")
print(decline_top1[["Date", "Region_ko", "Signal_score"]])


# ==================================================
# 3. 저장 폴더
# ==================================================

output_dir = Path(
    "result/social_charts"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True
)


# ==================================================
# 4. 한글 폰트
# ==================================================

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


# ==================================================
# 5. 디자인
# ==================================================

BACKGROUND = "#F7F9FC"
TEXT = "#172033"
MUTED = "#667085"
GRID = "#D9E0EA"

PREVIOUS = "#5B7CFA"
CURRENT = "#FF6B4A"


# ==================================================
# 6. 숫자 라벨
# ==================================================

def add_value_labels(
    ax,
    bars,
    values
):

    for bar, value in zip(
        bars,
        values
    ):

        height = bar.get_height()

        ax.annotate(
            f"{int(value):,}",
            (
                bar.get_x()
                + bar.get_width() / 2,
                height
            ),
            xytext=(
                0,
                8 if value >= 0 else -8
            ),
            textcoords="offset points",
            ha="center",
            va=(
                "bottom"
                if value >= 0
                else "top"
            ),
            fontsize=11,
            fontweight="bold",
            color=TEXT
        )


# ==================================================
# 7. 그래프 생성 함수
# ==================================================

def make_signal_chart(
    signal_row,
    signal_name,
    subtitle,
    filename
):

    region = signal_row["Region_ko"]
    current_date = signal_row["Date"]

    previous_date = (
        current_date
        - pd.DateOffset(years=1)
    )


    current = social[
        (social["Region_ko"] == region)
        &
        (social["Date"] == current_date)
    ]

    previous = social[
        (social["Region_ko"] == region)
        &
        (social["Date"] == previous_date)
    ]


    if current.empty or previous.empty:

        print(
            f"데이터 없음: {region}"
        )

        return


    current_values = [
        current["Natural_growth"].iloc[0],
        current["Net_migration"].iloc[0]
    ]

    previous_values = [
        previous["Natural_growth"].iloc[0],
        previous["Net_migration"].iloc[0]
    ]


    labels = [
        "자연증가",
        "순이동"
    ]

    x = np.arange(
        len(labels)
    )

    width = 0.30


    fig, ax = plt.subplots(
        figsize=(12, 7)
    )

    fig.patch.set_facecolor(
        BACKGROUND
    )

    ax.set_facecolor(
        BACKGROUND
    )


    bars_previous = ax.bar(
        x - width / 2,
        previous_values,
        width,
        label="전년 동월",
        color=PREVIOUS,
        zorder=3
    )


    bars_current = ax.bar(
        x + width / 2,
        current_values,
        width,
        label="탐지 시점",
        color=CURRENT,
        zorder=3
    )


    ax.axhline(
        y=0,
        color=TEXT,
        linewidth=1.2,
        alpha=0.75,
        zorder=2
    )


    ax.yaxis.grid(
        True,
        color=GRID,
        linewidth=0.8,
        alpha=0.8,
        zorder=1
    )

    ax.xaxis.grid(False)


    for side in [
        "top",
        "right",
        "left"
    ]:

        ax.spines[
            side
        ].set_visible(False)


    ax.spines[
        "bottom"
    ].set_color(GRID)


    ax.set_xticks(x)

    ax.set_xticklabels(
        labels,
        fontsize=13,
        fontweight="bold",
        color=TEXT
    )


    ax.tick_params(
        axis="y",
        labelsize=10,
        colors=MUTED
    )


    ax.set_ylabel(
        "인원(명)",
        fontsize=11,
        color=MUTED
    )

    ax.set_xlabel("")


    add_value_labels(
        ax,
        bars_previous,
        previous_values
    )

    add_value_labels(
        ax,
        bars_current,
        current_values
    )


    title = (
        f"{region} "
        f"{signal_name}"
    )


    fig.text(
        0.08,
        0.93,
        title,
        fontsize=22,
        fontweight="bold",
        color=TEXT
    )


    fig.text(
        0.08,
        0.885,
        subtitle,
        fontsize=11.5,
        color=MUTED
    )


    ax.legend(
        loc="upper right",
        frameon=False,
        fontsize=10.5,
        ncol=2,
        bbox_to_anchor=(
            1.0,
            1.08
        )
    )


    summary = (
        f"핵심 제보  |  "
        f"자연증가 "
        f"{int(previous_values[0]):,} → "
        f"{int(current_values[0]):,}명"
        f"   ·   "
        f"순이동 "
        f"{int(previous_values[1]):,} → "
        f"{int(current_values[1]):,}명"
    )


    fig.text(
        0.08,
        0.055,
        summary,
        fontsize=12.5,
        color=TEXT,
        bbox=dict(
            boxstyle="round,pad=0.7",
            facecolor="white",
            edgecolor=GRID,
            linewidth=1
        )
    )


    plt.subplots_adjust(
        left=0.09,
        right=0.96,
        top=0.80,
        bottom=0.18
    )


    save_path = (
        output_dir
        / filename
    )


    plt.savefig(
        save_path,
        dpi=220,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    plt.close()


    print(
        "그래프 저장 완료:",
        save_path
    )


# ==================================================
# 8. 인구 엇갈림 TOP 1 자동 그래프
# ==================================================

make_signal_chart(
    signal_row=cross_top1,
    signal_name="인구 엇갈림 시그널",
    subtitle=(
        "자연감소 방향과 "
        "순이동 방향이 "
        "강하게 엇갈린 사례"
    ),
    filename="social_cross_top1.png"
)


# ==================================================
# 9. 인구 이중감소 TOP 1 자동 그래프
# ==================================================

make_signal_chart(
    signal_row=decline_top1,
    signal_name="인구 이중감소 시그널",
    subtitle=(
        "자연감소와 순유출이 "
        "동시에 악화된 사례"
    ),
    filename="social_decline_top1.png"
)


print(
    "\n사회 시그널 자동 그래프 생성 완료!"
)