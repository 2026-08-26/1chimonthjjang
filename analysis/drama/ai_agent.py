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


    # ==========================================================
    # 외부 호출
    # ==========================================================

    def generate_report(
        self,
        item
    ):

        fallback = (
            self._generate_rule_based_report(
                item
            )
        )


        # API KEY가 없으면 기본 브리핑
        if not self.api_key:

            return fallback


        try:

            llm_report = (
                self._call_llm_api(
                    item
                )
            )


            return (
                self._normalize_report(

                    llm_report,

                    fallback
                )
            )


        except Exception as e:

            print(
                "⚠️ OpenAI API 호출 실패. "
                f"기본 분석으로 전환합니다: {e}"
            )

            return fallback


    # ==========================================================
    # 규칙 기반 취재 브리핑
    # ==========================================================

    def _generate_rule_based_report(
        self,
        item
    ):

        title = str(
            item.get(
                "title",
                "알 수 없는 콘텐츠"
            )
        )


        category = str(
            item.get(
                "category_name",
                "콘텐츠"
            )
        )


        cat_type = str(
            item.get(
                "category",
                ""
            )
        )


        inc_rate = float(
            item.get(
                "increase_rate",
                0
            )
            or 0
        )


        signal = str(
            item.get(
                "signal",
                "LOW"
            )
        )


        score = int(
            item.get(
                "trend_score",
                0
            )
            or 0
        )


        z_score = float(
            item.get(
                "z_score",
                0
            )
            or 0
        )


        baseline_avg = float(
            item.get(
                "baseline_avg",
                item.get(
                    "past_30_avg",
                    0
                )
            )
            or 0
        )


        recent_avg = float(
            item.get(
                "recent_7_avg",
                0
            )
            or 0
        )


        signal_reason = str(
            item.get(
                "signal_reason",
                "추가 확인이 필요한 시그널입니다."
            )
        )


        # ======================================================
        # 카테고리별 취재 방향
        # ======================================================

        if cat_type == "music":

            domain_question = (
                "음원 공개, 숏폼 챌린지, 팬덤 활동, "
                "방송 출연 중 어떤 요소가 관심도 변화와 "
                "같은 시점에 나타났는가?"
            )

            domain_data = (
                "음원 스트리밍 추이, 공식 영상 조회수, "
                "SNS 및 숏폼 언급량"
            )

            article_angle = (
                "음원·영상·팬덤 반응의 상승 시점 비교"
            )


        elif cat_type == "drama":

            domain_question = (
                "최근 방송 회차, OTT 공개, 공식 클립, "
                "출연진 관련 이슈 중 어떤 요소가 "
                "관심도 상승 시점과 일치하는가?"
            )

            domain_data = (
                "OTT 순위, 공식 클립 조회수, "
                "커뮤니티 게시글 및 댓글량"
            )

            article_angle = (
                "방송 시점과 온라인 화제성 변화 시점 비교"
            )


        else:

            domain_question = (
                "신규 회차 공개, 휴재 복귀, 완결, "
                "영상화 또는 협업 소식 중 어떤 요인이 "
                "관심도 상승 시점과 일치하는가?"
            )

            domain_data = (
                "웹툰 회차 공개 시점, 댓글·별점 참여량, "
                "관련 커뮤니티 게시글 변화"
            )

            article_angle = (
                "작품 이벤트와 독자 반응 상승 시점 비교"
            )


        # ======================================================
        # 최종 결과
        # ======================================================

        return {

            "title": title,

            "briefing": (
                f"{title}({category})의 최근 7일 평균 관심도는 "
                f"이전 23일 평균 대비 {inc_rate:+.1f}% 변했습니다. "
                f"기준 평균은 {baseline_avg:.1f}, "
                f"최근 7일 평균은 {recent_avg:.1f}, "
                f"Z-score는 {z_score:.2f}입니다. "
                f"이상감지 종합 점수는 {score}/100이며 "
                f"{signal} 신호로 분류되었습니다. "
                f"{signal_reason}"
            ),

            "article_ideas": [

                (
                    f"'{title}' 관심도 "
                    f"{inc_rate:+.1f}% 변화, "
                    "급격한 관심 변화의 배경은?"
                ),

                (
                    f"데이터가 포착한 '{title}' "
                    f"{signal} 시그널: "
                    f"{article_angle}"
                ),

                (
                    f"검색 데이터로 본 '{title}', "
                    "온라인 관심이 움직인 시점은 언제인가"
                ),
            ],

            "questions": [

                (
                    "최근 7일 사이 관심도를 움직일 만한 "
                    "구체적인 사건이나 콘텐츠 공개가 있었는가?"
                ),

                domain_question,

                (
                    "검색 관심도 변화가 실제 시청·청취·열람 "
                    "행동 증가와도 연결되는가?"
                ),
            ],

            "verification_data": [

                (
                    "Google Trends 또는 네이버 데이터랩의 "
                    "기간별 검색 관심도"
                ),

                domain_data,

                (
                    "공식 채널 게시 시점과 조회수·댓글량 "
                    "변화 데이터"
                ),
            ],
        }


    # ==========================================================
    # AI 응답 보정
    # ==========================================================

    def _normalize_report(
        self,
        report,
        fallback
    ):

        if not isinstance(
            report,
            dict
        ):

            return fallback


        return {

            "title": str(
                report.get(
                    "title"
                )
                or fallback[
                    "title"
                ]
            ),

            "briefing": str(
                report.get(
                    "briefing"
                )
                or fallback[
                    "briefing"
                ]
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

            str(item).strip()

            for item in value

            if str(item).strip()
        ]


        if not cleaned:

            return fallback


        return cleaned[:5]


    # ==========================================================
    # OpenAI API
    # ==========================================================

    def _call_llm_api(
        self,
        item
    ):

        import openai


        client = openai.OpenAI(
            api_key=self.api_key
        )


        prompt = f"""
당신은 데이터 저널리즘 전문 AI 취재 보조 에이전트입니다.

아래 이상감지 결과를 바탕으로 기자가 실제 취재를 시작할 때
활용할 수 있는 브리핑을 작성하세요.

[콘텐츠]
제목: {item.get('title')}
카테고리: {item.get('category_name')}

[이상감지 데이터]
이전 23일 평균: {item.get('baseline_avg', item.get('past_30_avg'))}
최근 7일 평균: {item.get('recent_7_avg')}
관심도 변화율: {item.get('increase_rate')}%
Z-score: {item.get('z_score')}
트렌드 점수: {item.get('trend_score')}/100
신호: {item.get('signal')}

[작성 원칙]
- 제공된 수치만 사실로 사용한다.
- 관심도가 오른 실제 이유를 임의로 단정하지 않는다.
- 원인은 기자가 확인해야 할 취재 가설로 작성한다.
- 존재하지 않는 뉴스, 순위, 사건을 만들어내지 않는다.
- HTML 태그를 사용하지 않는다.

반드시 아래 JSON 형식으로 응답하세요.

{{
    "title": "콘텐츠 제목",
    "briefing": "2~4문장 핵심 분석",
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
        "확인 데이터 1",
        "확인 데이터 2",
        "확인 데이터 3"
    ]
}}
"""


        response = (
            client
            .chat
            .completions
            .create(

                model="gpt-4o-mini",

                messages=[

                    {
                        "role": "system",

                        "content": (
                            "당신은 데이터로 이상징후를 탐지하고 "
                            "기자가 추가 취재할 수 있는 질문을 만드는 "
                            "데이터 저널리즘 보조 에이전트입니다."
                        ),
                    },

                    {
                        "role": "user",

                        "content": prompt,
                    },
                ],

                response_format={
                    "type": "json_object"
                },
            )
        )


        return json.loads(
            response
            .choices[0]
            .message
            .content
        )