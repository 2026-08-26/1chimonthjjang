# analysis/drama/mock_data.py 예시 코드 중 load_all_contents 내부 리턴 딕셔너리 부분

def load_all_contents():
  # ... 기존 데이터 로드 및 처리 로직 ...

  items = []
  for idx, row in df.iterrows():
    # 수치 계산 또는 기존 값 가져오기
    base_avg = row.get("base_avg", 100)
    recent_avg = row.get("recent_avg", 150)

    # 💡 increase_rate가 없을 경우 계산해서 넣어주기 (KeyError 방지)
    if "increase_rate" in row:
      increase_rate = row["increase_rate"]
    else:
      increase_rate = (
          round(((recent_avg - base_avg) / base_avg) * 100, 1)
          if base_avg > 0
          else 0.0
      )

    item = {
        "id": int(row.get("id", idx)),
        "title": row.get("title", f"콘텐츠 {idx}"),
        "category": row.get("category", "drama"),
        "base_avg": base_avg,
        "recent_avg": recent_avg,
        "increase_rate": increase_rate,  # 👈 이 부분이 핵심입니다!
        "signal": row.get("signal", "MEDIUM"),
        "z_score": row.get("z_score", 2.0),
        "pulse_score": row.get("pulse_score", 75),
    }
    items.append(item)

  return items