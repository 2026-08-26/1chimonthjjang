import json
import os


class TrendAIAgent:

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate_report(self, item):
        if self.api_key:
            try:
                return self._call_llm_api(item)
            except Exception as e:
                print(f"⚠️ API 호출 실패. 기본 규칙 엔진으로 전환합니다: {e}")
                return self._generate_rule_based_report(item)
        else:
            return self._generate_rule_based_report(item)

    def _generate_rule_based_report(self, item):
        title = item.get("title", "알 수 없는 콘텐츠")
        category = item.get("category_name", "콘텐츠")
        cat_type = item.get("category", "")
        inc_rate = item.get("increase_rate", 0)
        signal = item.get("signal", "LOW")
        score = item.get("trend_score", 0)

        if cat_type == "music":
            domain_q = "음원 차트 상위권 진입 시점 및 숏폼(릴스/틱톡) 챌린지 유행 여부"
            domain_data = "음원 스트리밍 일간 이용자 수(DAU) 및 SNS 언급량 추이"
        elif cat_type == "drama":
            domain_q = "최근 방송 회차의 화제성 장면 유출 및 OTT 순위 상승 원인"
            domain_data = "K-content 화제성 지수 및 커뮤니티 게시글 생성량"
        else:
            domain_q = "최근 유료 회차 결제율 급증 및 영상화 소식 유무"
            domain_data = "웹툰 별점 참여자 수 변화 및 주요 커뮤니티 반응"

        return {
            "title": title,
            "briefing": (
                f"<strong>[{title}]</strong>({category})은(는) 최근 7일간 검색 관심도가 "
                f"과거 30일 평균 대비 <strong>+{inc_rate}%</strong> 급증했습니다. "
                f"이상감지 엔진 분석 결과 종합 점수 <strong>{score}점 ({signal} 등급)</strong>으로 포착되었습니다."
            ),
            "article_ideas": [
                f"[{category} 단독] '{title}' 관심도 +{inc_rate}% 급증, 갑작스런 폭발적 인기의 비결은?",
                f"데이터로 본 '{title}': 이상징후 {signal} 신호 포착이 시사하는 미디어 트렌드",
                f"소비자 반응 분석: '{title}' 관련 유입 키워드 및 온/오프라인 이슈",
            ],
            "questions": [
                "최근 7일 간 결정적인 계기(밈, 숏폼 챌린지, 핫이슈)가 발생했는가?",
                domain_q,
                "주요 타깃 연령층에서의 유입 비율 격차는 어떠한가?",
            ],
            "verification_data": [
                "네이버 데이터랩 및 Google Trends 검색 데이터",
                domain_data,
                "YouTube/TikTok 키워드 노출량 및 댓글 감성 분석 데이터",
            ],
        }

    def _call_llm_api(self, item):
        import openai

        client = openai.OpenAI(api_key=self.api_key)
        prompt = f"""
        당신은 데이터 저널리즘 전문 AI 기자 에이전트입니다.
        아래 미디어 트렌드 지표를 바탕으로 기자를 위한 취재 분석 리포트를 JSON으로 응답하세요.
        - 제목: {item.get('title')}
        - 카테고리: {item.get('category_name')}
        - 관심도 증가율: +{item.get('increase_rate')}%
        - 이상징후 등급: {item.get('signal')}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)