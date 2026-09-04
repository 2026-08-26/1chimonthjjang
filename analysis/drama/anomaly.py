import numpy as np


class TrendAnomalyEngine:

    def __init__(
        self, high_threshold=150, medium_threshold=50, z_threshold=1.96
    ):
        self.high_threshold = high_threshold  # +150% 이상 HIGH
        self.medium_threshold = medium_threshold  # +50% 이상 MEDIUM
        self.z_threshold = z_threshold  # Z-score 기준값

    def calculate_metrics(self, daily_values):
        """30일 일별 검색량/관심도 배열을 받아 지표를 계산합니다.

        [0:23] = 과거 23일, [23:30] = 최근 7일
        """
        arr = np.array(daily_values)
        if len(arr) < 30:
            return {}

        past_30_avg = np.mean(arr[:23])
        recent_7_avg = np.mean(arr[23:])
        std_dev = np.std(arr[:23]) if np.std(arr[:23]) > 0 else 1.0

        # 1. 단순 변화율 (%)
        increase_rate = (
            ((recent_7_avg - past_30_avg) / past_30_avg) * 100
            if past_30_avg > 0
            else 0
        )

        # 2. Z-Score (표준화 점수)
        z_score = (recent_7_avg - past_30_avg) / std_dev

        # 3. 트렌드 종합 점수 (0 ~ 100점 스케일링)
        raw_score = 50 + (increase_rate / 5) + (z_score * 5)
        trend_score = int(min(max(raw_score, 10), 99))

        # 4. 신호 등급 분류
        if increase_rate >= self.high_threshold or z_score >= 2.5:
            signal = "HIGH"
        elif increase_rate >= self.medium_threshold or z_score >= 1.5:
            signal = "MEDIUM"
        else:
            signal = "LOW"

        return {
            "past_30_avg": round(past_30_avg, 1),
            "recent_7_avg": round(recent_7_avg, 1),
            "increase_rate": round(increase_rate, 1),
            "z_score": round(z_score, 2),
            "trend_score": trend_score,
            "signal": signal,
        }