import numpy as np


class TrendAnomalyEngine:

    def __init__(
        self, high_threshold=150, medium_threshold=50, z_threshold=1.96
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.z_threshold = z_threshold

    def calculate_metrics(self, daily_values):
        """
        30일 일별 관심도 데이터를 받아 이상감지 지표를 계산합니다.

        [0:23]  = 이전 23일 기준 구간
        [23:30] = 최근 7일 분석 구간

        기존 코드와의 호환성을 위해 past_30_avg 키는 유지합니다.
        실제 의미는 '이전 23일 평균'입니다.
        """

        try:
            arr = np.asarray(daily_values, dtype=float)
        except (TypeError, ValueError):
            return {}

        # 최소 30일 데이터가 필요함
        if len(arr) < 30:
            return {}

        # 정확히 30일까지만 사용
        arr = arr[:30]

        # NaN, inf 등 잘못된 값 검사
        if not np.all(np.isfinite(arr)):
            return {}

        baseline = arr[:23]
        recent = arr[23:30]

        baseline_avg = float(np.mean(baseline))
        recent_7_avg = float(np.mean(recent))

        baseline_std = float(np.std(baseline))

        # 표준편차가 0이면 Z-score 계산 오류 방지
        if baseline_std <= 0:
            baseline_std = 1.0

        # ---------------------------------------
        # 1. 최근 7일 관심도 변화율
        # ---------------------------------------
        increase_rate = (
            ((recent_7_avg - baseline_avg) / baseline_avg) * 100
            if baseline_avg > 0
            else 0.0
        )

        # ---------------------------------------
        # 2. Z-score
        # ---------------------------------------
        z_score = (recent_7_avg - baseline_avg) / baseline_std

        # ---------------------------------------
        # 3. 트렌드 종합 점수
        # 10 ~ 99 범위
        # ---------------------------------------
        raw_score = 50 + (increase_rate / 5) + (z_score * 5)

        trend_score = int(
            round(
                min(
                    max(raw_score, 10),
                    99
                )
            )
        )

        # ---------------------------------------
        # 4. 이상징후 등급
        # ---------------------------------------
        if increase_rate >= self.high_threshold or z_score >= 2.5:
            signal = "HIGH"

        elif increase_rate >= self.medium_threshold or z_score >= 1.5:
            signal = "MEDIUM"

        else:
            signal = "LOW"

        signal_label = {
            "HIGH": "급상승",
            "MEDIUM": "주의",
            "LOW": "정상/유지",
        }[signal]

        # 왜 해당 신호가 나왔는지 설명
        signal_reason = self._build_signal_reason(
            signal=signal,
            increase_rate=increase_rate,
            z_score=z_score,
        )

        return {
            # 기존 코드와 연결을 유지하기 위한 값
            "past_30_avg": round(baseline_avg, 1),
            "recent_7_avg": round(recent_7_avg, 1),
            "increase_rate": round(increase_rate, 1),
            "z_score": round(z_score, 2),
            "trend_score": trend_score,
            "signal": signal,

            # 상세 페이지 설명용 추가 데이터
            "baseline_avg": round(baseline_avg, 1),
            "signal_label": signal_label,
            "signal_reason": signal_reason,
        }

    def _build_signal_reason(
        self,
        signal,
        increase_rate,
        z_score
    ):
        """
        HIGH / MEDIUM / LOW 판정 이유를
        사용자가 이해하기 쉬운 문장으로 생성합니다.
        """

        if signal == "HIGH":

            if (
                increase_rate >= self.high_threshold
                and z_score >= 2.5
            ):
                basis = (
                    "증가율과 Z-score가 모두 "
                    "HIGH 기준을 충족"
                )

            elif increase_rate >= self.high_threshold:
                basis = (
                    f"증가율이 HIGH 기준 "
                    f"(+{self.high_threshold}% 이상)을 충족"
                )

            else:
                basis = (
                    "Z-score가 HIGH 기준 "
                    "(2.5 이상)을 충족"
                )

        elif signal == "MEDIUM":

            if increase_rate >= self.medium_threshold:
                basis = (
                    f"증가율이 MEDIUM 기준 "
                    f"(+{self.medium_threshold}% 이상)을 충족"
                )

            else:
                basis = (
                    "Z-score가 MEDIUM 기준 "
                    "(1.5 이상)을 충족"
                )

        else:
            basis = (
                "증가율과 Z-score가 "
                "급상승 기준 미만"
            )

        return (
            f"최근 7일 평균 변화율 {increase_rate:+.1f}%, "
            f"Z-score {z_score:.2f}로 "
            f"{basis}했습니다."
        )