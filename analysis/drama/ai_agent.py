import json
import os


class TrendAIAgent:
    """
    DATA TIP-OFF K콘텐츠 취재 보조 에이전트.

    원인을 확정하지 않고,
    이상감지 지표를 바탕으로 기자가 검증할 가설과
    취재 방향을 제안합니다.

    OPENAI_API_KEY가 없거나 API 호출이 실패해도
    규칙 기반 fallback으로 정상 동작합니다.
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    # =========================================================
    # PUBLIC
    # =========================================================

    def generate_report(self, item):

        if not isinstance(item, dict):
            return self._empty_report(
                "분석할 콘텐츠 데이터가 올바르지 않습니다."
            )

        fallback = self._generate_rule_based_report(item)

        if not self.api_key:
            return fallback

        try:
            report = self._call_llm_api(item)
            return self._normalize_report(
                report,
                fallback
            )

        except Exception as e:
            # API 키나 사용자 데이터는 로그에 출력하지 않음
            print(
                "[TrendAIAgent] AI API 호출 실패. "
                f"규칙 기반 리포트로 전환: {type(e).__name__}"
            )

            return fallback

    # =========================================================
    # RULE BASED FALLBACK
    # =========================================================

    def _generate_rule_based_report(self, item):

        title = self._safe_text(
            item.get("title"),
            "알 수 없는 콘텐츠"
        )

        category = self._safe_text(
            item.get("category_name"),
            "콘텐츠"
        )

        cat_type = self._safe_text(
            item.get("category"),
            ""
        )

        signal = self._safe_text(
            item.get("signal"),
            "LOW"
        ).upper()

        inc_rate = self._safe_float(
            item.get("increase_rate")
        )

        score = self._safe_int(
            item.get("trend_score")
        )

        z_score = self._safe_float(
            item.get("z_score")
        )

        baseline = self._safe_float(
            item.get(
                "baseline_avg",
                item.get("past_30_avg", 0)
            )
        )

        recent = self._safe_float(
            item.get("recent_7_avg")
        )

        ratio = self._safe_float(
            item.get("interest_ratio")
        )

        if ratio <= 0 and baseline > 0:
            ratio = recent / baseline

        hypotheses = self._category_hypotheses(
            cat_type,
            title
        )

        article_ideas = self._article_ideas(
            category,
            title,
            inc_rate,
            signal
        )

        questions = self._reporting_questions(
            cat_type,
            title
        )

        verification_data = self._verification_data(
            cat_type
        )

        briefing = (
            f"{title}({category})의 최근 7일 평균 관심도는 "
            f"기준 23일 평균 대비 {inc_rate:+.1f}% 변했습니다. "
            f"평소 대비 관심 수준은 {ratio:.2f}배, "
            f"Z-score는 {z_score:.2f}, "
            f"이상감지 점수는 {score}/100으로 "
            f"{signal} 신호가 포착되었습니다. "
            "이 수치는 관심 패턴의 이상 움직임을 뜻하며 "
            "실제 원인을 확정하지 않습니다. "
            "아래 가설을 외부 자료와 취재를 통해 검증해야 합니다."
        )

        return {
            "title": title,
            "briefing": briefing,
            "hypotheses": hypotheses,
            "article_ideas": article_ideas,
            "questions": questions,
            "verification_data": verification_data,
        }

    # =========================================================
    # CATEGORY CONTENT
    # =========================================================

    def _category_hypotheses(self, cat_type, title):

        if cat_type == "music":
            return [
                "신곡·컴백·차트 진입·음악방송 등 최근 공개 일정이 관심도 상승 시점과 겹쳤을 가능성",
                "숏폼 챌린지, 직캠, 밈 또는 팬 커뮤니티 확산이 검색 관심을 끌어올렸을 가능성",
                "멤버 개인 활동, 방송 출연, 협업 또는 관련 이슈가 그룹·인물 검색량에 영향을 줬을 가능성",
            ]

        if cat_type == "drama":
            return [
                "최근 방송 회차 또는 OTT 공개 시점이 관심도 상승 구간과 겹쳤을 가능성",
                "공식 클립이나 화제 장면이 커뮤니티·SNS에서 확산되며 검색 유입을 만들었을 가능성",
                "출연진 관련 일정·인터뷰·이슈 또는 해외 반응 증가가 작품 관심도에 영향을 줬을 가능성",
            ]

        return [
            "최근 회차의 주요 전개 또는 새 에피소드 공개가 검색 관심 증가와 겹쳤을 가능성",
            "복귀·완결·영상화·콜라보·프로모션 등의 공지가 관심도를 끌어올렸을 가능성",
            "특정 캐릭터나 장면이 커뮤니티와 SNS에서 확산되며 작품 검색 유입을 만들었을 가능성",
        ]

    def _article_ideas(
        self,
        category,
        title,
        inc_rate,
        signal
    ):
        return [
            (
                f"데이터로 본 '{title}': "
                f"최근 관심도 {inc_rate:+.1f}% 변화, "
                "무슨 일이 있었나"
            ),
            (
                f"'{title}' {signal} 신호 포착: "
                "검색 관심이 달라진 시점과 온라인 반응을 추적"
            ),
            (
                f"{category} 관심 패턴 분석: "
                f"'{title}'의 급격한 변화가 일시적 화제인지 "
                "지속 흐름인지 검증"
            ),
        ]

    def _reporting_questions(
        self,
        cat_type,
        title
    ):

        common = [
            "관심도 변화가 시작된 날짜 전후에 공식 발표, 방송, 공개 일정 또는 외부 이슈가 있었는가?",
            "검색 관심 증가와 SNS·커뮤니티·영상 플랫폼 반응 증가가 같은 시점에 나타나는가?",
            "국내 관심과 해외 관심, 팬덤 내부 반응과 일반 대중 반응이 같은 방향으로 움직이는가?",
        ]

        if cat_type == "music":
            common[1] = (
                "음원 차트, 직캠·공식 영상, 숏폼 챌린지와 "
                "검색 관심 상승 시점이 일치하는가?"
            )

        elif cat_type == "drama":
            common[1] = (
                "방송 회차, OTT 순위, 공식 클립 조회수와 "
                "검색 관심 상승 시점이 일치하는가?"
            )

        else:
            common[1] = (
                "회차 공개, 별점·댓글·관심등록 변화와 "
                "검색 관심 상승 시점이 일치하는가?"
            )

        return common

    def _verification_data(self, cat_type):

        base = [
            "네이버 데이터랩·Google Trends 등 실제 검색 추이",
            "공식 SNS 및 주요 커뮤니티의 날짜별 언급량",
            "관련 보도·공식 발표·공개 일정 타임라인",
        ]

        if cat_type == "music":
            base[1] = (
                "음원 차트·YouTube 공식 영상/직캠·"
                "TikTok/릴스 노출량의 날짜별 변화"
            )

        elif cat_type == "drama":
            base[1] = (
                "시청률·OTT 순위·공식 클립 조회수·"
                "드라마 화제성 지표"
            )

        else:
            base[1] = (
                "회차별 댓글·별점 참여·관심등록·"
                "관련 커뮤니티 언급량"
            )

        return base

    # =========================================================
    # LLM
    # =========================================================

    def _call_llm_api(self, item):
        """
        API 키는 서버 환경변수에서만 읽습니다.
        HTML/JavaScript로 전달하지 않습니다.
        """

        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key
        )

        payload = {
            "title": self._safe_text(
                item.get("title"),
                "알 수 없는 콘텐츠"
            ),
            "category": self._safe_text(
                item.get("category_name"),
                "콘텐츠"
            ),
            "category_type": self._safe_text(
                item.get("category"),
                ""
            ),
            "signal": self._safe_text(
                item.get("signal"),
                "LOW"
            ),
            "trend_score": self._safe_int(
                item.get("trend_score")
            ),
            "increase_rate": self._safe_float(
                item.get("increase_rate")
            ),
            "z_score": self._safe_float(
                item.get("z_score")
            ),
            "baseline_avg": self._safe_float(
                item.get(
                    "baseline_avg",
                    item.get("past_30_avg", 0)
                )
            ),
            "recent_7_avg": self._safe_float(
                item.get("recent_7_avg")
            ),
            "interest_ratio": self._safe_float(
                item.get("interest_ratio")
            ),
        }

        prompt = f"""
당신은 데이터 저널리즘 취재 보조 AI입니다.

아래 데이터는 실제 사건의 원인을 증명하는 데이터가 아니라
콘텐츠 관심 패턴의 이상 움직임을 탐지한 지표입니다.

중요 규칙:
1. 원인을 사실처럼 단정하지 마세요.
2. "~일 가능성", "~인지 확인 필요"처럼 가설로 표현하세요.
3. 사용자가 제공하지 않은 실제 사건, 날짜, 성과, 수치를 만들어내지 마세요.
4. 기사 아이디어도 확인 전 사실처럼 제목을 확정하지 마세요.
5. 검증 가능한 외부 데이터와 취재 질문을 제안하세요.
6. HTML 태그를 출력하지 마세요.

분석 데이터:
{json.dumps(payload, ensure_ascii=False)}

반드시 아래 JSON 형식으로만 응답하세요.

{{
  "briefing": "2~4문장의 짧은 취재 브리핑",
  "hypotheses": [
    "검증할 가설 1",
    "검증할 가설 2",
    "검증할 가설 3"
  ],
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
    "추가 확인 데이터 1",
    "추가 확인 데이터 2",
    "추가 확인 데이터 3"
  ]
}}
"""

        response = client.chat.completions.create(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-4o-mini"
            ),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 사실과 가설을 구분하는 "
                        "데이터 저널리즘 취재 보조 AI입니다."
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
            temperature=0.3,
        )

        content = (
            response.choices[0]
            .message
            .content
        )

        return json.loads(content)

    # =========================================================
    # NORMALIZE
    # =========================================================

    def _normalize_report(
        self,
        report,
        fallback
    ):

        if not isinstance(report, dict):
            return fallback

        return {
            "title": fallback["title"],
            "briefing": self._clean_output_text(
                report.get("briefing"),
                fallback["briefing"]
            ),
            "hypotheses": self._clean_string_list(
                report.get("hypotheses"),
                fallback["hypotheses"]
            ),
            "article_ideas": self._clean_string_list(
                report.get("article_ideas"),
                fallback["article_ideas"]
            ),
            "questions": self._clean_string_list(
                report.get("questions"),
                fallback["questions"]
            ),
            "verification_data": self._clean_string_list(
                report.get("verification_data"),
                fallback["verification_data"]
            ),
        }

    # =========================================================
    # SAFETY HELPERS
    # =========================================================

    def _clean_string_list(
        self,
        value,
        fallback,
        max_items=3
    ):

        if not isinstance(value, list):
            return fallback

        result = []

        for item in value[:max_items]:

            text = self._clean_output_text(
                item,
                ""
            )

            if text:
                result.append(text)

        return result or fallback

    def _clean_output_text(
        self,
        value,
        fallback
    ):

        if value is None:
            return fallback

        text = str(value).strip()

        # 너무 긴 응답이 UI를 망가뜨리지 않도록 제한
        if len(text) > 1200:
            text = text[:1200].rstrip() + "…"

        # HTML 태그를 그대로 렌더링하지 않도록 단순 제거
        text = (
            text.replace("<", "")
            .replace(">", "")
        )

        return text or fallback

    def _safe_text(
        self,
        value,
        fallback=""
    ):

        if value is None:
            return fallback

        text = str(value).strip()

        if not text:
            return fallback

        return text[:300]

    def _safe_float(
        self,
        value
    ):

        try:
            return float(value or 0)

        except (
            TypeError,
            ValueError
        ):
            return 0.0

    def _safe_int(
        self,
        value
    ):

        try:
            return int(
                float(value or 0)
            )

        except (
            TypeError,
            ValueError
        ):
            return 0

    def _empty_report(
        self,
        message
    ):

        return {
            "title": "분석 불가",
            "briefing": message,
            "hypotheses": [],
            "article_ideas": [],
            "questions": [],
            "verification_data": [],
        }
