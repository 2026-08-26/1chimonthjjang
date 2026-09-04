from openai import OpenAI
from dotenv import load_dotenv
import os

# .env 파일 불러오기
load_dotenv()

# API KEY 가져오기
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def analyze_signal(
    player_name,
    weather,
    season_avg,
    weather_avg,
    weather_diff,
    games,
    ab,
    signal_score
):

    prompt = f"""
당신은 데이터 저널리즘 기자를 지원하는 AI 취재 Agent입니다.

다음은 KBO 선수 데이터에서 통계적으로 탐지된 이상 신호입니다.

선수: {player_name}
날씨 조건: {weather}
시즌 전체 타율: {season_avg:.3f}
해당 날씨 타율: {weather_avg:.3f}
타율 차이: {weather_diff:.3f}
해당 조건 경기 수: {games}
해당 조건 타수: {ab}
이상 신호 점수: {signal_score:.3f}

이 데이터를 기자의 취재 관점에서 분석하세요.

반드시 다음 형식으로 답변하세요.

[시그널 요약]
2~3문장으로 핵심 이상 현상을 설명하세요.

[취재 가치]
왜 기자가 추가로 확인해볼 가치가 있는지 설명하세요.

[추천 취재 질문]
기자가 실제 취재할 질문을 3개 제안하세요.

주의:
- 데이터만으로 인과관계를 단정하지 마세요.
- 날씨가 성적 변화의 원인이라고 단정하지 마세요.
- 표본 크기를 고려하세요.
- 통계적 이상 신호는 취재의 출발점이라는 관점에서 작성하세요.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text


# 연결 테스트
if __name__ == "__main__":

    result = analyze_signal(
        player_name="노진혁",
        weather="비",
        season_avg=0.271084,
        weather_avg=0.186047,
        weather_diff=-0.085038,
        games=25,
        ab=86,
        signal_score=-0.788608
    )

    print(result)