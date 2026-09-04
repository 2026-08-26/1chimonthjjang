class BaseballAIAgent:

    def generate_report(self, item):
        """야구 이상신호 데이터를 받아 기자용 취재 리포트 생성"""

        player = item.get("player_name", "선수")
        weather_type = item.get("weather_type", "날씨")
        weather_group = item.get("weather_group", "")

        season_avg = float(item.get("season_avg", 0))
        weather_avg = float(item.get("weather_avg", 0))
        weather_diff = float(item.get("weather_diff", 0))
        signal_score = float(item.get("signal_score", 0))

        games = int(item.get("games", 0))
        ab = int(item.get("AB", 0))

        # 상승 / 하락 판단
        if weather_diff > 0:
            direction = "상승"
            performance = "강한"
        else:
            direction = "하락"
            performance = "약한"

        # 변화율 계산
        if season_avg != 0:
            change_rate = (weather_diff / season_avg) * 100
        else:
            change_rate = 0

        # 이상신호 강도
        abs_score = abs(signal_score)

        if abs_score >= 0.8:
            signal_level = "HIGH"
        elif abs_score >= 0.5:
            signal_level = "MEDIUM"
        else:
            signal_level = "LOW"

        # 날씨별 취재 포인트
        if weather_type == "기온":
            weather_question = (
                f"{weather_group} 기온에서 타구 속도나 장타율 등 "
                "다른 공격 지표에서도 같은 변화가 나타나는가?"
            )

            weather_data = (
                "경기별 실제 기온, 타구·장타 지표 및 경기장 정보"
            )

        elif weather_type == "습도":
            weather_question = (
                f"{weather_group} 환경에서 타격뿐 아니라 "
                "장타 생산성에도 동일한 변화가 나타나는가?"
            )

            weather_data = (
                "경기별 습도, 장타율 및 타구 관련 데이터"
            )

        else:
            weather_question = (
                "비가 내린 경기의 그라운드 상태나 경기 지연이 "
                "타격 성과와 함께 움직였는가?"
            )

            weather_data = (
                "강수량, 경기 지연 여부 및 경기장 상태 데이터"
            )

        return {
            "title": f"{player} 날씨 이상신호",

            "briefing": (
                f"<strong>{player}</strong> 선수는 "
                f"<strong>{weather_group}</strong> 조건에서 "
                f"타율 <strong>{weather_avg:.3f}</strong>을 기록했습니다. "
                f"시즌 평균 {season_avg:.3f} 대비 "
                f"<strong>{abs(change_rate):.1f}% {direction}</strong>한 결과입니다. "
                f"해당 조건의 표본은 {games}경기 {ab}타수이며, "
                f"이상신호는 <strong>{signal_level}</strong> 수준으로 탐지되었습니다."
            ),

            "article_ideas": [
                (
                    f"'{weather_group}에 {performance} {player}?' "
                    f"평균 대비 타율 {abs(change_rate):.1f}% {direction}"
                ),

                (
                    f"날씨가 타자의 경기력과 함께 움직일까? "
                    f"{player}의 {weather_group} 경기 데이터 분석"
                ),

                (
                    f"시즌 평균을 벗어난 {player}, "
                    f"{weather_type} 조건에서 나타난 이상신호"
                )
            ],

            "questions": [
                (
                    f"{player}의 {weather_group} 경기 성적 변화가 "
                    "다른 시즌에서도 반복되는가?"
                ),

                weather_question,

                (
                    "상대 투수, 구장, 홈·원정 등 다른 요인을 "
                    "통제해도 같은 패턴이 유지되는가?"
                )
            ],

            "verification_data": [
                weather_data,

                "상대 선발투수 및 투수 유형 데이터",

                "홈·원정, 경기장, 최근 타격 컨디션 및 다년도 기록"
            ],

            "signal_level": signal_level
        }