class BaseballAIAgent:

    def generate_report(self, item):

        player = item.get("player_name", item.get("선수명", "알 수 없는 선수"))
        weather_type = item.get("weather_type", "날씨")
        weather_group = item.get("weather_group", "특정 조건")

        signal_score = float(item.get("signal_score", 0))

        # 컬럼명이 조금 달라도 대응
        normal_avg = item.get(
            "normal_avg",
            item.get("평소타율", item.get("overall_avg", 0))
        )

        condition_avg = item.get(
            "condition_avg",
            item.get("조건타율", item.get("group_avg", 0))
        )

        try:
            normal_avg = float(normal_avg)
        except:
            normal_avg = 0

        try:
            condition_avg = float(condition_avg)
        except:
            condition_avg = 0


        # 상승 / 하락 판단
        if signal_score > 0:
            direction = "상승"
            direction_text = "평소보다 좋은 타격 성적"
        else:
            direction = "하락"
            direction_text = "평소보다 낮은 타격 성적"


        # 이상도 등급
        strength = abs(signal_score)

        if strength >= 0.15:
            level = "HIGH"
        elif strength >= 0.08:
            level = "MEDIUM"
        else:
            level = "LOW"


        # 날씨별 취재 질문
        if weather_type == "기온":

            question = (
                f"{weather_group} 환경이 타자의 타격 성과에 "
                "실제로 영향을 미쳤는지 확인할 필요가 있는가?"
            )

            extra_data = [
                "경기별 실제 기온 및 체감온도",
                "홈/원정 경기 여부",
                "상대 투수 및 구장별 타격 기록"
            ]

        elif weather_type == "습도":

            question = (
                f"{weather_group} 습도에서 타격 성적 변화가 "
                "반복적으로 나타나는가?"
            )

            extra_data = [
                "경기별 평균 습도",
                "구장별 습도 차이",
                "타구 속도 및 장타율 변화"
            ]

        else:

            question = (
                "비가 오는 경기에서 해당 선수의 성적 변화가 "
                "반복적으로 나타나는가?"
            )

            extra_data = [
                "경기 당일 강수량",
                "우천 중단 여부 및 경기 지연 시간",
                "비가 오지 않은 경기와의 성적 비교"
            ]


        return {

            "title": player,

            "briefing": (
                f"<strong>{player}</strong> 선수는 "
                f"<strong>{weather_type} - {weather_group}</strong> 조건에서 "
                f"{direction_text}을 보였습니다. "
                f"평소 타율 대비 변화 신호는 "
                f"<strong>{signal_score:+.3f}</strong>이며 "
                f"이상 신호 강도는 <strong>{level}</strong> 등급으로 탐지되었습니다."
            ),

            "article_ideas": [
                f"'{player}', {weather_group}에서 타격 성적 {direction}…날씨 영향일까?",
                f"데이터로 본 {player}: {weather_type} 변화와 타격 성적의 관계",
                f"{weather_group}에 강한/약한 타자? {player}의 경기 기록 분석"
            ],

            "questions": [
                question,
                "이 현상이 한 시즌에만 나타난 우연인지 여러 시즌에서도 반복되는가?",
                "구장, 상대 투수, 홈·원정 효과를 제거한 뒤에도 같은 패턴이 나타나는가?"
            ],

            "verification_data": extra_data
        }