import numpy as np
import pandas as pd


class TrendAnomalyEngine:
  """드라마 및 트렌드 데이터의 이상 징후(Anomaly)를 감지하고

  Z-Score 및 펄스 점수를 계산하는 엔진 클래스입니다.
  """

  def __init__(self, df=None):
    self.df = df

  def calculate_anomaly(self, values):
    """주어진 시계열 수치 리스트/배열에서 이상 감지 지표를 계산합니다."""
    return self.calculate_metrics(values)

  def calculate_metrics(self, values):
    """기존 코드(mock_data.py 또는 total.py)에서 호출하는

    메서드 이름 호환을 위한 함수입니다.
    """
    if len(values) < 2:
      return {
          "base_avg": 0,
          "recent_avg": 0,
          "change_rate": 0,
          "z_score": 0,
          "pulse_score": 50,
          "grade": "LOW",
      }

    values = np.array(values, dtype=float)
    baseline = values[:-7] if len(values) >= 30 else values[: max(1, len(values) - 7)]
    recent = values[-7:]

    base_mean = np.mean(baseline) if len(baseline) > 0 else np.mean(values)
    base_std = np.std(baseline) if len(baseline) > 1 else 1.0
    if base_std == 0:
      base_std = 1.0

    recent_mean = np.mean(recent)
    z_score = (recent_mean - base_mean) / base_std
    change_rate = (
        ((recent_mean - base_mean) / base_mean) * 100 if base_mean > 0 else 0
    )

    pulse_score = min(100, max(10, int(50 + z_score * 10)))

    if z_score >= 2.5 or change_rate >= 100:
      grade = "HIGH"
    elif z_score >= 1.5 or change_rate >= 50:
      grade = "MEDIUM"
    else:
      grade = "LOW"

    return {
        "base_avg": round(float(base_mean), 1),
        "recent_avg": round(float(recent_mean), 1),
        "change_rate": round(float(change_rate), 1),
        "z_score": round(float(z_score), 2),
        "pulse_score": pulse_score,
        "grade": grade,
    }