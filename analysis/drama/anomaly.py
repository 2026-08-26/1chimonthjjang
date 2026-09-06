import numpy as np


class TrendAnomalyEngine:
    """
    DATA TIP-OFF K콘텐츠 이상감지 엔진.

    30일 관심도 시계열을
    - 기준 구간: 앞 23일
    - 최근 구간: 마지막 7일
    로 나누어 비교합니다.

    핵심 판단 축
    1) 변화의 크기: increase_rate
    2) 통계적 이례성: z_score
    3) 지속성: anomaly_days / max_consecutive_anomaly_days

    단순히 "몇 % 올랐다" 하나만으로 HIGH를 판정하지 않습니다.
    """

    def __init__(
        self,
        high_threshold=150,
        medium_threshold=50,
        z_threshold=1.96,
        anomaly_sigma=1.0,
        low_base_threshold=1.0,
    ):
        self.high_threshold = float(high_threshold)
        self.medium_threshold = float(medium_threshold)
        self.z_threshold = float(z_threshold)
        self.anomaly_sigma = float(anomaly_sigma)
        self.low_base_threshold = float(low_base_threshold)

    def calculate_metrics(self, daily_values):
        """30일 배열을 기준 23일 + 최근 7일로 나눠 지표를 계산합니다."""

        try:
            arr = np.asarray(daily_values, dtype=float)
        except (TypeError, ValueError):
            return {}

        if arr.ndim != 1:
            arr = arr.reshape(-1)

        if len(arr) < 30:
            return {}

        arr = arr[:30]

        if not np.all(np.isfinite(arr)):
            return {}

        if np.any(arr < 0):
            return {}

        baseline = arr[:23]
        recent = arr[23:30]

        baseline_avg = float(np.mean(baseline))
        recent_7_avg = float(np.mean(recent))
        baseline_std = float(np.std(baseline))

        if not np.isfinite(baseline_std) or baseline_std <= 0:
            baseline_std = 1.0

        if baseline_avg > 0:
            interest_ratio = recent_7_avg / baseline_avg
            relative_level_pct = interest_ratio * 100
            increase_rate = (
                (recent_7_avg - baseline_avg)
                / baseline_avg
                * 100
            )
        else:
            interest_ratio = 0.0
            relative_level_pct = 0.0
            increase_rate = 0.0

        z_score = (
            recent_7_avg - baseline_avg
        ) / baseline_std

        recent_daily_z = (
            recent - baseline_avg
        ) / baseline_std

        anomaly_threshold = (
            baseline_avg
            + self.anomaly_sigma * baseline_std
        )

        anomaly_mask = (
            recent > anomaly_threshold
        )

        anomaly_days = int(
            np.sum(anomaly_mask)
        )

        persistence_rate = (
            anomaly_days / 7 * 100
        )

        max_consecutive_anomaly_days = (
            self._max_consecutive_true(
                anomaly_mask
            )
        )

        # 종합 이상감지 점수
        # 변화 크기 40 + 통계적 이례성 35 + 지속성 25
        positive_increase = max(
            increase_rate,
            0.0
        )

        positive_z = max(
            z_score,
            0.0
        )

        change_score = min(
            positive_increase / 150.0,
            1.0
        ) * 40.0

        z_component = min(
            positive_z / 4.0,
            1.0
        ) * 35.0

        persistence_component = (
            anomaly_days / 7.0
        ) * 25.0

        raw_score = (
            change_score
            + z_component
            + persistence_component
        )

        trend_score = int(
            round(
                min(
                    max(raw_score, 0),
                    99
                )
            )
        )

        # 단일 지표가 아니라 종합점수 + 지속성 + 변화/이례성 조건
        high_support = (
            increase_rate >= 50
            or z_score >= 2.5
        )

        medium_support = (
            increase_rate >= 20
            or z_score >= 1.5
        )

        if (
            trend_score >= 75
            and anomaly_days >= 4
            and high_support
        ):
            signal = "HIGH"

        elif (
            trend_score >= 45
            and anomaly_days >= 2
            and medium_support
        ):
            signal = "MEDIUM"

        else:
            signal = "LOW"

        signal_label = {
            "HIGH": "우선 취재",
            "MEDIUM": "관찰 필요",
            "LOW": "일반 범위",
        }[signal]

        percentage_reliable = (
            baseline_avg
            >= self.low_base_threshold
        )

        percentage_note = (
            ""
            if percentage_reliable
            else "기준 평균이 매우 작아 증감률 해석에 주의가 필요합니다."
        )

        signal_reason = self._build_signal_reason(
            baseline_avg=baseline_avg,
            recent_7_avg=recent_7_avg,
            interest_ratio=interest_ratio,
            increase_rate=increase_rate,
            z_score=z_score,
            anomaly_days=anomaly_days,
            max_consecutive_anomaly_days=max_consecutive_anomaly_days,
            signal=signal,
            percentage_reliable=percentage_reliable,
        )

        return {
            # 기존 연결부 호환
            "past_30_avg": round(baseline_avg, 1),

            # 원 지표
            "baseline_avg": round(baseline_avg, 1),
            "recent_7_avg": round(recent_7_avg, 1),

            # 변화 크기
            "increase_rate": round(increase_rate, 1),

            # 호환/설명용 (화면 핵심 카드에서는 중복이라 숨김)
            "interest_ratio": round(interest_ratio, 2),
            "relative_level_pct": round(relative_level_pct, 1),

            # 통계적 이례성
            "z_score": round(z_score, 2),

            # 지속성
            "anomaly_days": anomaly_days,
            "persistence_days": anomaly_days,
            "persistence_rate": round(persistence_rate, 1),
            "max_consecutive_anomaly_days":
                max_consecutive_anomaly_days,

            # 그래프/설명용
            "baseline_std": round(baseline_std, 2),
            "anomaly_threshold": round(anomaly_threshold, 1),
            "anomaly_sigma": self.anomaly_sigma,
            "recent_daily_z": [
                round(float(value), 2)
                for value in recent_daily_z
            ],

            # 종합 판정
            "trend_score": trend_score,
            "signal": signal,
            "signal_label": signal_label,
            "signal_reason": signal_reason,

            # 퍼센트 안전장치
            "percentage_reliable": percentage_reliable,
            "percentage_note": percentage_note,
        }

    def _max_consecutive_true(self, values):
        max_count = 0
        current = 0

        for value in values:
            if bool(value):
                current += 1
                max_count = max(
                    max_count,
                    current
                )
            else:
                current = 0

        return int(max_count)

    def _build_signal_reason(
        self,
        baseline_avg,
        recent_7_avg,
        interest_ratio,
        increase_rate,
        z_score,
        anomaly_days,
        max_consecutive_anomaly_days,
        signal,
        percentage_reliable,
    ):
        if signal == "HIGH":
            conclusion = (
                "변화 크기·통계적 이례성·지속성이 함께 확인돼 "
                "우선 취재 후보로 분류했습니다."
            )

        elif signal == "MEDIUM":
            conclusion = (
                "일부 이상징후가 확인돼 추가 관찰과 "
                "원인 확인이 필요한 후보로 분류했습니다."
            )

        else:
            conclusion = (
                "현재 설정된 종합 기준에서는 "
                "일반 변동 범위에 가까운 상태입니다."
            )

        reason = (
            f"최근 7일 평균 관심도 지수는 {recent_7_avg:.1f}pt로 "
            f"기준 23일 평균 {baseline_avg:.1f}pt 대비 "
            f"{increase_rate:+.1f}% 변했습니다. "
            f"이는 평소의 약 {interest_ratio:.2f}배 수준이며, "
            f"Z-score는 {z_score:.2f}입니다. "
            f"최근 7일 중 {anomaly_days}일이 평소 변동 범위를 벗어났고, "
            f"최대 {max_consecutive_anomaly_days}일 연속으로 "
            f"이상 움직임이 이어졌습니다. "
            f"{conclusion}"
        )

        if not percentage_reliable:
            reason += (
                " 다만 기준값이 매우 작아 "
                "퍼센트 증감률은 보조적으로 해석해야 합니다."
            )

        return reason
