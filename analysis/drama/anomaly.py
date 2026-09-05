import numpy as np


class TrendAnomalyEngine:

    def __init__(
        self,
        high_threshold=90,
        medium_threshold=30,
        z_threshold=1.5,
        high_z_threshold=3.5
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.z_threshold = z_threshold
        self.high_z_threshold = high_z_threshold


    def calculate_metrics(self, daily_values):
        """
        30일 관심도 데이터를 분석합니다.

        앞 23일 : 기준 구간
        뒤 7일  : 최근 관찰 구간

        반환값
        ------------------
        baseline_avg
        past_30_avg
        recent_7_avg
        increase_rate
        interest_ratio
        z_score
        trend_score
        signal
        signal_label
        signal_reason
        """

        try:

            arr = np.asarray(
                daily_values,
                dtype=float
            )

        except (TypeError, ValueError):

            return {}


        # 최소 30개 데이터 필요
        if len(arr) < 30:

            return {}


        arr = arr[:30]


        # NaN / 무한대 방지
        if not np.all(
            np.isfinite(arr)
        ):

            return {}


        # ==================================================
        # 기준 23일 / 최근 7일
        # ==================================================

        baseline = arr[:23]

        recent = arr[23:30]


        baseline_avg = float(
            np.mean(baseline)
        )


        recent_7_avg = float(
            np.mean(recent)
        )


        baseline_std = float(
            np.std(baseline)
        )


        if baseline_std <= 0:

            baseline_std = 1.0


        # ==================================================
        # 1. 관심도 변화율
        # ==================================================

        increase_rate = (

            (
                (
                    recent_7_avg
                    - baseline_avg
                )

                / baseline_avg
            )

            * 100

            if baseline_avg > 0

            else 0.0
        )


        # ==================================================
        # 2. 평소 대비 몇 배 수준인가
        # ==================================================

        interest_ratio = (

            recent_7_avg
            / baseline_avg

            if baseline_avg > 0

            else 1.0
        )


        # ==================================================
        # 3. Z-score
        #
        # 기준 구간의 표준편차를 기준으로
        # 최근 평균이 얼마나 멀리 벗어났는지 계산
        # ==================================================

        z_score = (

            recent_7_avg
            - baseline_avg

        ) / baseline_std


        # ==================================================
        # 4. 이상신호 등급
        # ==================================================

        if (

            increase_rate
            >= self.high_threshold

            or

            z_score
            >= self.high_z_threshold
        ):

            signal = "HIGH"


        elif (

            increase_rate
            >= self.medium_threshold

            or

            z_score
            >= self.z_threshold
        ):

            signal = "MEDIUM"


        else:

            signal = "LOW"


        # ==================================================
        # 5. 탐지 점수
        #
        # 증가율 + Z-score를 결합
        #
        # 기존처럼 HIGH가 전부 99점에 몰리지 않도록
        # 점수를 자연스럽게 분산
        # ==================================================

        positive_increase = max(
            increase_rate,
            0.0
        )


        positive_z = max(
            z_score,
            0.0
        )


        increase_component = (

            min(
                positive_increase,
                150.0
            )

            / 150.0

            * 55.0
        )


        z_component = (

            min(
                positive_z,
                6.0
            )

            / 6.0

            * 35.0
        )


        raw_score = (

            10.0

            + increase_component

            + z_component
        )


        trend_score = int(

            round(

                min(

                    max(
                        raw_score,
                        10.0
                    ),

                    99.0
                )
            )
        )


        # ==================================================
        # 등급과 점수가 너무 어색하지 않도록 보정
        # ==================================================

        if signal == "HIGH":

            trend_score = max(
                trend_score,
                70
            )


        elif signal == "MEDIUM":

            trend_score = min(

                max(
                    trend_score,
                    40
                ),

                69
            )


        else:

            trend_score = min(
                trend_score,
                39
            )


        # ==================================================
        # 화면 표시용 이름
        # ==================================================

        signal_label = {

            "HIGH":
                "급상승",

            "MEDIUM":
                "주의",

            "LOW":
                "정상/유지",

        }[signal]


        # ==================================================
        # 왜 포착됐는지 설명
        # ==================================================

        signal_reason = (
            self._build_signal_reason(

                signal=signal,

                increase_rate=
                    increase_rate,

                interest_ratio=
                    interest_ratio,

                z_score=
                    z_score
            )
        )


        # ==================================================
        # 결과
        # ==================================================

        return {

            # 기존 코드 호환
            "past_30_avg":
                round(
                    baseline_avg,
                    1
                ),

            # 의미가 명확한 이름
            "baseline_avg":
                round(
                    baseline_avg,
                    1
                ),

            "recent_7_avg":
                round(
                    recent_7_avg,
                    1
                ),

            "increase_rate":
                round(
                    increase_rate,
                    1
                ),

            "interest_ratio":
                round(
                    interest_ratio,
                    2
                ),

            "z_score":
                round(
                    z_score,
                    2
                ),

            "trend_score":
                trend_score,

            "signal":
                signal,

            "signal_label":
                signal_label,

            "signal_reason":
                signal_reason,
        }


    # ======================================================
    # 이상감지 이유 자동 설명
    # ======================================================

    def _build_signal_reason(
        self,
        signal,
        increase_rate,
        interest_ratio,
        z_score
    ):

        if signal == "HIGH":

            return (

                f"최근 7일 평균 관심도가 "
                f"기준 구간의 "
                f"{interest_ratio:.2f}배 수준으로 변했고 "

                f"변화율 "
                f"{increase_rate:+.1f}%, "

                f"Z-score "
                f"{z_score:.2f}가 나타났습니다. "

                "평소 패턴에서 크게 벗어난 움직임으로 "
                "우선 취재 확인이 필요한 후보입니다."
            )


        if signal == "MEDIUM":

            return (

                f"최근 7일 평균 관심도가 "
                f"기준 구간의 "
                f"{interest_ratio:.2f}배 수준이며 "

                f"변화율 "
                f"{increase_rate:+.1f}%, "

                f"Z-score "
                f"{z_score:.2f}가 나타났습니다. "

                "평소보다 의미 있는 변화가 감지되어 "
                "추가 관찰이 필요한 후보입니다."
            )


        return (

            f"최근 7일 평균 관심도는 "
            f"기준 구간의 "
            f"{interest_ratio:.2f}배 수준이며 "

            f"변화율 "
            f"{increase_rate:+.1f}%, "

            f"Z-score "
            f"{z_score:.2f}입니다. "

            "현재는 일반적인 변동 범위로 분류됩니다."
        )