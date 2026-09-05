import numpy as np


class TrendAnomalyEngine:

    def __init__(
        self,
        high_threshold=150,
        medium_threshold=50,
        z_threshold=1.96
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.z_threshold = z_threshold


    def calculate_metrics(self, daily_values):
        """
        30일 관심도 데이터를 분석합니다.

        앞 23일  : 기준 구간
        뒤 7일   : 최근 구간
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


        # 처음 30개만 사용
        arr = arr[:30]


        # NaN / 무한대 체크
        if not np.all(
            np.isfinite(arr)
        ):
            return {}


        # ==========================================
        # 기준 23일 / 최근 7일
        # ==========================================

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


        # ==========================================
        # 1. 관심도 변화율
        # ==========================================

        if baseline_avg > 0:

            increase_rate = (
                (
                    recent_7_avg
                    - baseline_avg
                )
                / baseline_avg
                * 100
            )

        else:

            increase_rate = 0.0


        # ==========================================
        # 2. Z-score
        # ==========================================

        z_score = (
            recent_7_avg
            - baseline_avg
        ) / baseline_std


        # ==========================================
        # 3. 신호 분류
        # ==========================================

        if (
            increase_rate >= self.high_threshold
            or z_score >= 4.5
        ):
            signal = "HIGH"

        elif (
            increase_rate >= self.medium_threshold
            or z_score >= 1.5
        ):
            signal = "MEDIUM"

        else:
            signal = "LOW"


        # ==========================================
        # 4. 트렌드 점수
        #
        # 기존 방식은 강한 신호가 전부 99점에
        # 몰리는 문제가 있었음.
        #
        # 증가율 + Z-score를 0~99 범위로
        # 조금 더 자연스럽게 분산합니다.
        # ==========================================

        positive_increase = max(
            increase_rate,
            0
        )

        positive_z = max(
            z_score,
            0
        )


        increase_component = min(
            positive_increase,
            220
        ) / 220 * 60


        z_component = min(
            positive_z,
            7
        ) / 7 * 34


        raw_score = (
            5
            + increase_component
            + z_component
        )


        trend_score = int(
            round(
                min(
                    max(
                        raw_score,
                        5
                    ),
                    99
                )
            )
        )


        # ==========================================
        # 기자에게 보여줄 이상감지 설명
        # ==========================================

        if signal == "HIGH":

            signal_reason = (
                "기준 구간과 비교해 매우 큰 관심도 변화가 "
                "탐지되어 우선 취재가 필요한 후보입니다."
            )

        elif signal == "MEDIUM":

            signal_reason = (
                "평소보다 의미 있는 관심도 변화가 감지되어 "
                "추가 모니터링과 취재 확인이 필요한 후보입니다."
            )

        else:

            signal_reason = (
                "현재 변화폭은 비교적 안정적인 범위이지만 "
                "추가 변화 여부를 지속적으로 확인할 수 있습니다."
            )


        # ==========================================
        # 결과
        # ==========================================

        return {

            # 기존 코드 호환성 때문에 이름 유지
            "past_30_avg": round(
                baseline_avg,
                1
            ),

            # 의미를 더 명확하게 쓰고 싶을 때 사용
            "baseline_avg": round(
                baseline_avg,
                1
            ),

            "recent_7_avg": round(
                recent_7_avg,
                1
            ),

            "increase_rate": round(
                increase_rate,
                1
            ),

            "z_score": round(
                z_score,
                2
            ),

            "trend_score": trend_score,

            "signal": signal,

            "signal_reason": signal_reason,
        }