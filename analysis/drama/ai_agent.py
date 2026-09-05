import json
import os


class TrendAIAgent:

    def __init__(
        self,
        api_key=None
    ):

        self.api_key = (
            api_key
            or os.getenv(
                "OPENAI_API_KEY"
            )
        )

    # ======================================
    # AI 리포트 생성
    # ======================================
    def generate_report(
        self,
        item
    ):

        # API가 없어도 동작하는
        # 기본 리포트를 먼저 생성
        fallback = (
            self._generate_rule_based_report(
                item
            )
        )

        if not self.api_key:
            return fallback

        try:

            llm_report = (
                self._call_llm_api(
                    item
                )
            )

            # AI가 일부 데이터를 누락해도
            # 화면이 깨지지 않도록 보정
            return self._normalize_report(
                llm_report,
                fallback
            )

        except Exception as e:

            print(
                "⚠️ API 호출 실패. "
                "기본 규칙 엔진으로 전환합니다: "
                f"{e}"
            )

            return fallback

    # ======================================
    # API 없이 사용하는 규칙 기반 리포트
    # ======================================
    def _generate_rule_based_report(
        self,
        item
    ):

        title = item.get(
            "title",
            "알 수 없는 콘텐츠"
        )

        category = item.get(
            "category_name",
            "콘텐츠"
        )

        cat_type = item.get(
            "category",
            ""
        )

        inc_rate = item.get(
            "increase_rate",
            0
        )

        signal = item.get(
            "signal",
            "LOW"
        )

        score = item.get(
            "trend_score",
            0
        )

        z_score = item.get(
            "z_score",
            0
        )

        baseline_avg = item.get(
            "baseline_avg",
            item.get(
                "past_30_avg",
                0
            )
        )

        recent_avg = item.get(
            "recent_7_avg",
            0
        )

        signal_reason = item.get(
            "signal_reason",
            "추가 확인이 필요합니다."
        )

        # ----------------------------------
        # 음악
        # ----------------------------------
        if cat_type == "music":

            domain_q = (
                "음원 차트, 숏폼 챌린지, "
                "팬덤 확산 중 어떤 요인이 "
                "상승을 이끌었는가?"
            )

            domain_data = (
                "음원 스트리밍 추이, "
                "YouTube 조회수, "
                "SNS/숏폼 언급량"
            )

            angle = (
                "음원·영상·팬덤 반응이 "
                "동시에 증가했는지 비교"
            )

        # ----------------------------------
        # 드라마
        # ----------------------------------
        elif cat_type == "drama":

            domain_q = (
                "최근 회차, OTT 순위, "
                "출연진 이슈 중 어떤 요인이 "
                "화제성 상승에 영향을 줬는가?"
            )

            domain_data = (
                "OTT 순위, 공식 클립 조회수, "
                "커뮤니티 게시글/댓글량"
            )

            angle = (
                "방송 시점과 온라인 화제성 "
                "상승 시점이 일치하는지 확인"
            )

        # ----------------------------------
        # 웹툰
        # ----------------------------------
        else:

            domain_q = (
                "신규 회차, 휴재 복귀, "
                "영상화/콜라보 소식 중 "
                "어떤 요인이 관심도 상승에 "
                "영향을 줬는가?"
            )

            domain_data = (
                "회차 공개 시점, "
                "댓글/별점 참여, "
                "작품 관련 커뮤니티 반응"
            )

            angle = (
                "작품 이벤트와 독자 반응 "
                "상승 시점이 일치하는지 확인"
            )

        return {
            "title": title,

            "briefing": (
                f"{title}({category})은 최근 7일 평균 관심도가 "
                f"이전 23일 평균 대비 "
                f"{inc_rate:+.1f}% 변했습니다. "
                f"기준 평균은 {baseline_avg:.1f}, "
                f"최근 7일 평균은 {recent_avg:.1f}, "
                f"Z-score는 {z_score:.2f}이며 "
                f"종합 점수는 {score}/100, "
                f"신호는 {signal}입니다. "
                f"{signal_reason}"
            ),

            "article_ideas": [
                (
                    f"'{title}' 관심도 "
                    f"{inc_rate:+.1f}% 변화, "
                    "데이터로 본 상승 배경"
                ),
                (
                    f"'{title}' {signal} 신호 포착: "
                    f"{angle}"
                ),
                (
                    "검색 관심도와 온라인 반응으로 본 "
                    f"'{title}'의 현재 화제성"
                ),
            ],

            "questions": [
                (
                    "최근 7일 안에 관심도를 움직인 "
                    "구체적인 이벤트가 있었는가?"
                ),
                domain_q,
                (
                    "검색량 상승이 실제 시청·청취·열람 "
                    "행동 증가와도 연결되는가?"
                ),
            ],

            "verification_data": [
                (
                    "Google Trends 또는 "
                    "네이버 데이터랩 검색 관심도"
                ),
                domain_data,
                (
                    "콘텐츠 공식 채널의 게시 시점과 "
                    "댓글/조회수 변화"
                ),
            ],
        }

    # ======================================
    # AI 응답 안전 보정
    # ======================================
    def _normalize_report(
        self,
        report,
        fallback
    ):
        """
        AI가 JSON 키를 일부 빼거나
        형식을 잘못 반환해도
        프론트엔드가 깨지지 않도록 합니다.
        """

        if not isinstance(
            report,
            dict
        ):
            return fallback

        normalized = {
            "title":
                str(
                    report.get("title")
                    or fallback["title"]
                ),

            "briefing":
                str(
                    report.get("briefing")
                    or fallback["briefing"]
                ),

            "article_ideas":
                self._normalize_list(
                    report.get(
                        "article_ideas"
                    ),
                    fallback[
                        "article_ideas"
                    ]
                ),

            "questions":
                self._normalize_list(
                    report.get(
                        "questions"
                    ),
                    fallback[
                        "questions"
                    ]
                ),

            "verification_data":
                self._normalize_list(
                    report.get(
                        "verification_data"
                    ),
                    fallback[
                        "verification_data"
                    ]
                ),
        }

        return normalized

    # ======================================
    # 리스트 데이터 검사
    # ======================================
    @staticmethod
    def _normalize_list(
        value,
        fallback
    ):

        if not isinstance(
            value,
            list
        ):
            return fallback

        cleaned = [
            str(v).strip()
            for v in value
            if str(v).strip()
        ]

        if not cleaned:
            return fallback

        return cleaned[:5]

    # ======================================
    # OpenAI API
    # ======================================
    def _call_llm_api(
        self,
        item
    ):

        import openai

        client = openai.OpenAI(
            api_key=self.api_key
        )

        prompt = f"""
당신은 데이터 저널리즘 전문 AI 기자 에이전트입니다.

아래 K-콘텐츠 이상감지 결과를 바탕으로
'취재를 시작하기 위한 분석 리포트'를 작성하세요.

[분석 데이터]

- 제목: {item.get('title')}
- 카테고리: {item.get('category_name')}
- 이전 23일 평균: {item.get('baseline_avg', item.get('past_30_avg'))}
- 최근 7일 평균: {item.get('recent_7_avg')}
- 관심도 변화율: {item.get('increase_rate')}%
- Z-score: {item.get('z_score')}
- 트렌드 점수: {item.get('trend_score')}/100
- 이상징후 등급: {item.get('signal')}

[중요]

- 제공된 수치만 사실처럼 사용하세요.
- 실제 원인을 단정하지 마세요.
- 원인은 '취재로 확인해야 할 가설'로 표현하세요.
- 실제 뉴스 내용을 임의로 만들어내지 마세요.
- 실제 음원 차트 순위를 임의로 만들어내지 마세요.
- 실제 OTT 플랫폼 순위를 임의로 만들어내지 마세요.
- HTML 태그를 넣지 마세요.

반드시 아래 JSON 구조로 응답하세요.

{{
    "title": "콘텐츠명",
    "briefing": "2~4문장의 분석 요약",
    "article_ideas": [
        "기사 아이디어 1",
        "기사 아이디어 2",
        "기사 아이디어 3"
    ],
    "questions": [
        "취재 질문 1",
        "취재 질문 2",
        "취재 질문 3"
    ],
    "verification_data": [
        "확인할 데이터 1",
        "확인할 데이터 2",
        "확인할 데이터 3"
    ]
}}
"""

        response = (
            client.chat.completions.create(
                model="gpt-4o-mini",

                messages=[
                    {
                        "role":
                            "system",

                        "content":
                            (
                                "당신은 수치를 과장하지 않고 "
                                "제공되지 않은 사실을 "
                                "만들어내지 않는 "
                                "데이터 저널리즘 "
                                "보조 에이전트입니다."
                            ),
                    },
                    {
                        "role":
                            "user",

                        "content":
                            prompt,
                    },
                ],

                response_format={
                    "type":
                        "json_object"
                },
            )
        )

        return json.loads(
            response
            .choices[0]
            .message
            .content
        )