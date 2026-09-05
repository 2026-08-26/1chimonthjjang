import json
import os


class TrendAIAgent:
    """
    DATA TIP-OFF K콘텐츠 취재 보조 에이전트.

    역할을 명확히 분리합니다.

    - 이상감지 알고리즘: 무엇이 비정상적인지 탐지
    - AI Reporter: 그 이상신호를 기자가 검증할 취재 경로로 변환

    AI는 실제 원인을 확정하지 않습니다.
    OPENAI_API_KEY가 없거나 API 호출에 실패해도
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
            return self._normalize_report(report, fallback)

        except Exception as e:
            # API 키·프롬프트·사용자 데이터는 로그에 출력하지 않습니다.
            print(
                "[TrendAIAgent] AI API 호출 실패. "
                f"규칙 기반 리포트로 전환: {type(e).__name__}"
            )
            return fallback

    # =========================================================
    # RULE-BASED FALLBACK
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

        anomaly_days = self._safe_int(
            item.get(
                "anomaly_days",
                item.get("persistence_days", 0)
            )
        )

        max_consecutive = self._safe_int(
            item.get("max_consecutive_anomaly_days")
        )

        # 숫자 낭독을 반복하기보다 기자 관점의 판단으로 요약합니다.
        if signal == "HIGH":
            briefing = (
                f"'{title}'은 단발성 상승보다 지속된 이상 흐름에 가깝습니다. "
                f"변화 크기, 통계적 이례성, 최근 지속성이 함께 나타나 "
                f"취재 우선순위 {score}/100의 {signal} 후보로 분류했습니다. "
                "AI는 원인을 확정하지 않으며, 아래 세 경로를 먼저 확인해 "
                "실제 사건·노출·외부 확산과의 시간적 연결을 검증하는 것이 좋습니다."
            )
        elif signal == "MEDIUM":
            briefing = (
                f"'{title}'에서 평소와 다른 움직임이 확인됐지만 "
                "아직 모든 판단 축이 강하게 일치하는 것은 아닙니다. "
                f"취재 우선순위는 {score}/100이며, 아래 검증 경로를 통해 "
                "일시적 변동인지 실제 취재 가치가 있는 변화인지 먼저 확인하는 것이 좋습니다."
            )
        else:
            briefing = (
                f"'{title}'은 현재 설정된 종합 기준에서는 강한 우선 취재 신호로 보지 않습니다. "
                "다만 특정 공개 일정이나 외부 이슈와 시점이 맞물리는지 확인하면 "
                "후속 관찰 여부를 판단하는 데 도움이 됩니다."
            )

        reporting_paths = self._reporting_paths(
            cat_type=cat_type,
            title=title,
            inc_rate=inc_rate,
            z_score=z_score,
            anomaly_days=anomaly_days,
            max_consecutive=max_consecutive,
        )

        hypotheses = [
            path["hypothesis"]
            for path in reporting_paths
        ]

        article_ideas = self._article_ideas(
            category=category,
            title=title,
            inc_rate=inc_rate,
            signal=signal,
            anomaly_days=anomaly_days,
        )

        questions = self._reporting_questions(
            cat_type=cat_type,
            title=title
        )

        verification_data = self._verification_data(
            cat_type=cat_type
        )

        return {
            "title": title,
            "briefing": briefing,
            "reporting_paths": reporting_paths,
            # 기존 화면/연결부 호환을 위해 유지
            "hypotheses": hypotheses,
            "article_ideas": article_ideas,
            "questions": questions,
            "verification_data": verification_data,
            "summary_metrics": {
                "increase_rate": round(inc_rate, 1),
                "z_score": round(z_score, 2),
                "anomaly_days": anomaly_days,
                "max_consecutive_anomaly_days": max_consecutive,
                "priority_score": score,
                "signal": signal,
            },
        }

    # =========================================================
    # REPORTING PATHS
    # =========================================================

    def _reporting_paths(
        self,
        cat_type,
        title,
        inc_rate,
        z_score,
        anomaly_days,
        max_consecutive,
    ):
        evidence = (
            f"최근 관심도는 기준 대비 {inc_rate:+.1f}% 변했고 "
            f"Z-score는 {z_score:.2f}입니다. "
            f"최근 7일 중 {anomaly_days}일이 이상 범위를 벗어났고 "
            f"최대 {max_consecutive}일 연속 이어졌습니다."
        )

        if cat_type == "music":
            return [
                {
                    "label": "공식 활동·공개 일정",
                    "hypothesis": (
                        "신곡·컴백·음악방송·공식 영상 등 콘텐츠 자체의 "
                        "공개 일정이 관심도 상승을 촉발했을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "관심도 상승 시작일과 신곡 공개, 음악방송, 공식 영상·직캠 "
                        "업로드 날짜를 같은 타임라인에 놓고 비교합니다."
                    ),
                    "falsify": (
                        "관심도 상승이 공식 활동보다 먼저 시작됐거나 공개 이후에도 "
                        "시점이 맞지 않으면 공식 일정만으로 설명하기 어렵습니다."
                    ),
                    "link_type": "source",
                },
                {
                    "label": "플랫폼·검색 노출",
                    "hypothesis": (
                        "차트 진입, 추천 노출, 검색량 확대 등 플랫폼 노출 변화가 "
                        "추가 유입을 만들었을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "Google Trends와 음원 차트·영상 조회 흐름을 비교해 "
                        "검색 상승과 플랫폼 노출이 같은 시점에 움직였는지 확인합니다."
                    ),
                    "falsify": (
                        "검색 관심만 상승하고 차트·영상·플랫폼 지표가 움직이지 않았다면 "
                        "플랫폼 노출 가설의 설명력은 낮아집니다."
                    ),
                    "link_type": "trends",
                },
                {
                    "label": "외부 화제 확산",
                    "hypothesis": (
                        "멤버 이슈, 숏폼 챌린지, 밈, 팬 커뮤니티 확산이 "
                        "외부 검색 유입을 만들었을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "관련 뉴스·SNS·커뮤니티 게시물의 날짜별 증가 구간과 "
                        "관심도 상승 시작 시점을 비교합니다."
                    ),
                    "falsify": (
                        "관련 언급량이 평소 수준이고 관심도 상승과 시간적으로 맞지 않으면 "
                        "외부 확산만으로 설명하기 어렵습니다."
                    ),
                    "link_type": "news",
                },
            ]

        if cat_type == "drama":
            return [
                {
                    "label": "방송·에피소드 효과",
                    "hypothesis": (
                        "최근 방송 회차, OTT 공개, 화제 장면 등 작품 내부 이벤트가 "
                        "관심도 상승을 촉발했을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "방송·OTT 공개일과 관심도 상승 시작일을 비교하고 "
                        "해당 회차의 공식 클립·시청 반응을 함께 확인합니다."
                    ),
                    "falsify": (
                        "관심도 상승이 방송·공개 일정과 무관한 시점에서 시작됐다면 "
                        "회차 효과만으로 설명하기 어렵습니다."
                    ),
                    "link_type": "source",
                },
                {
                    "label": "플랫폼 노출 변화",
                    "hypothesis": (
                        "OTT 순위, 추천 영역, 공식 클립 노출 증가가 "
                        "작품 검색 유입을 확대했을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "Google Trends와 OTT 순위·공식 클립 조회 변화의 날짜를 비교해 "
                        "동시에 상승했는지 확인합니다."
                    ),
                    "falsify": (
                        "OTT·클립 지표가 정체인데 검색 관심만 상승했다면 "
                        "플랫폼 노출 가설은 약해집니다."
                    ),
                    "link_type": "trends",
                },
                {
                    "label": "출연진·외부 이슈",
                    "hypothesis": (
                        "출연진 인터뷰·개인 활동·관련 보도 또는 온라인 화제가 "
                        "작품 관심도에 영향을 줬을 가능성"
                    ),
                    "why": evidence,
                    "check": (
                        "관련 뉴스와 커뮤니티 언급이 증가한 날짜를 찾아 "
                        "작품 관심도 상승 구간과 겹치는지 확인합니다."
                    ),
                    "falsify": (
                        "관련 외부 이슈가 없거나 관심도 상승 시점과 크게 어긋난다면 "
                        "외부 이슈 가설의 우선순위를 낮출 수 있습니다."
                    ),
                    "link_type": "news",
                },
            ]

        # webtoon 및 기타 콘텐츠
        return [
            {
                "label": "작품 내부 변화",
                "hypothesis": (
                    "최근 회차 공개, 주요 전개, 휴재 복귀·완결 등 작품 내부 이벤트가 "
                    "관심도 상승을 촉발했을 가능성"
                ),
                "why": evidence,
                "check": (
                    "웹툰 작품 페이지에서 최근 회차 공개일과 공지·휴재·복귀 여부를 확인하고 "
                    "관심도 상승 시작 시점과 비교합니다."
                ),
                "falsify": (
                    "작품 내부 일정 변화가 없거나 관심도 상승이 회차 공개보다 먼저 시작됐다면 "
                    "작품 내부 이벤트만으로 설명하기 어렵습니다."
                ),
                "link_type": "source",
            },
            {
                "label": "플랫폼 노출 변화",
                "hypothesis": (
                    "추천·랭킹·배너·프로모션 등 플랫폼 노출 변화가 "
                    "새로운 독자 유입을 만들었을 가능성"
                ),
                "why": evidence,
                "check": (
                    "Google Trends 흐름과 플랫폼 내 순위·추천 노출·관심등록 변화가 "
                    "같은 시점에 나타나는지 확인합니다."
                ),
                "falsify": (
                    "플랫폼 순위나 노출 변화가 없는데 검색 관심만 증가했다면 "
                    "플랫폼 노출 가설의 설명력은 낮아집니다."
                ),
                "link_type": "trends",
            },
            {
                "label": "외부 화제 확산",
                "hypothesis": (
                    "특정 장면·캐릭터·영상화 관련 이슈가 뉴스·SNS·커뮤니티에서 "
                    "확산되며 외부 검색 유입을 만들었을 가능성"
                ),
                "why": evidence,
                "check": (
                    "작품명 관련 뉴스·커뮤니티·SNS 언급량이 증가한 날짜를 찾아 "
                    "관심도 상승 시작 시점과 비교합니다."
                ),
                "falsify": (
                    "관련 외부 언급이 평소 수준이고 상승 시점과 맞지 않으면 "
                    "외부 확산 가설의 우선순위를 낮출 수 있습니다."
                ),
                "link_type": "news",
            },
        ]

    # =========================================================
    # ARTICLE / QUESTION / DATA
    # =========================================================

    def _article_ideas(
        self,
        category,
        title,
        inc_rate,
        signal,
        anomaly_days,
    ):
        return [
            (
                f"데이터가 먼저 포착한 '{title}': "
                f"최근 {anomaly_days}일 이상 흐름, 실제 계기는 무엇이었나"
            ),
            (
                f"'{title}' {signal} 취재 신호: "
                "작품 내부 변화·플랫폼 노출·외부 화제를 시간순으로 추적"
            ),
            (
                f"{category} 관심 패턴 분석: "
                f"'{title}'의 {inc_rate:+.1f}% 변화가 일시적 화제인지 "
                "지속 흐름인지 검증"
            ),
        ]

    def _reporting_questions(self, cat_type, title):
        if cat_type == "music":
            return [
                "관심도 상승이 시작된 날짜 전후에 신곡·컴백·방송·공식 영상 공개가 있었는가?",
                "음원 차트·YouTube·숏폼 지표도 검색 관심과 같은 시점에 움직였는가?",
                "팬덤 내부 반응과 일반 대중·해외 검색 반응이 같은 방향으로 움직이는가?",
            ]

        if cat_type == "drama":
            return [
                "관심도 상승이 특정 방송 회차나 OTT 공개 시점과 겹치는가?",
                "OTT 순위·시청률·공식 클립 조회수도 같은 구간에서 변했는가?",
                "출연진 관련 보도·인터뷰·이슈가 작품 검색 증가보다 먼저 나타났는가?",
            ]

        return [
            "관심도 상승이 최근 회차 공개·휴재 복귀·완결·공지 시점과 겹치는가?",
            "플랫폼 순위·댓글·별점·관심등록 등 작품 내부 반응도 같은 시점에 변했는가?",
            "뉴스·커뮤니티·SNS 언급 증가가 검색 관심 상승보다 먼저 나타났는가?",
        ]

    def _verification_data(self, cat_type):
        if cat_type == "music":
            return [
                "공식 활동·신곡·방송·영상 업로드 일정",
                "Google Trends, 음원 차트, YouTube/숏폼의 날짜별 변화",
                "관련 뉴스·SNS·팬 커뮤니티 언급량 타임라인",
            ]

        if cat_type == "drama":
            return [
                "방송 회차·OTT 공개 및 공식 클립 업로드 일정",
                "Google Trends, OTT 순위, 시청률·클립 조회 변화",
                "출연진·작품 관련 뉴스와 커뮤니티 언급량 타임라인",
            ]

        return [
            "웹툰 회차 공개·휴재·복귀·완결·작품 공지 타임라인",
            "Google Trends와 플랫폼 순위·댓글·별점·관심등록 변화",
            "작품 관련 뉴스·커뮤니티·SNS 언급량 타임라인",
        ]

    # =========================================================
    # LLM
    # =========================================================

    def _call_llm_api(self, item):
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
            "priority_score": self._safe_int(
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
            "anomaly_days": self._safe_int(
                item.get(
                    "anomaly_days",
                    item.get("persistence_days", 0)
                )
            ),
            "max_consecutive_anomaly_days": self._safe_int(
                item.get("max_consecutive_anomaly_days")
            ),
        }

        prompt = f"""
당신은 데이터 저널리즘 취재 보조 AI입니다.

프로젝트 목적:
- 이상감지 알고리즘이 평소와 다른 데이터 움직임을 탐지합니다.
- 당신의 역할은 원인을 맞히는 것이 아니라 기자가 어디부터 확인할지 '검증 가능한 취재 경로'를 제안하는 것입니다.

중요 규칙:
1. 실제 원인을 사실처럼 단정하지 마세요.
2. 사용자가 제공하지 않은 실제 사건·날짜·성과·수치를 만들어내지 마세요.
3. briefing에서 입력 수치를 길게 다시 읽지 마세요. 이상 패턴의 성격과 취재 우선순위를 짧게 해석하세요.
4. reporting_paths는 서로 다른 원인 계열 3개로 만드세요.
5. 각 경로는 반드시 가설, 왜 확인할 가치가 있는지, 확인 방법, 반증 조건을 포함해야 합니다.
6. 웹툰은 가능하면 '작품 내부 변화 / 플랫폼 노출 / 외부 화제 확산'을 구분하세요.
7. 드라마·음악도 '콘텐츠 자체 이벤트 / 플랫폼 노출 / 외부 확산'처럼 서로 다른 계열로 분리하세요.
8. link_type은 source, trends, news 중 하나만 사용하세요.
9. HTML 태그를 출력하지 마세요.
10. 기사 아이디어는 확인 전 사실을 제목처럼 확정하지 마세요.

분석 데이터:
{json.dumps(payload, ensure_ascii=False)}

반드시 아래 JSON 형식으로만 응답하세요.

{{
  "briefing": "2~4문장의 짧은 취재 브리핑",
  "reporting_paths": [
    {{
      "label": "취재 경로 이름",
      "hypothesis": "검증할 가능성",
      "why": "이 경로를 확인할 가치가 있는 이유",
      "check": "구체적인 확인 방법",
      "falsify": "이 가설의 우선순위를 낮출 수 있는 반증 조건",
      "link_type": "source"
    }},
    {{
      "label": "취재 경로 이름",
      "hypothesis": "검증할 가능성",
      "why": "이 경로를 확인할 가치가 있는 이유",
      "check": "구체적인 확인 방법",
      "falsify": "반증 조건",
      "link_type": "trends"
    }},
    {{
      "label": "취재 경로 이름",
      "hypothesis": "검증할 가능성",
      "why": "이 경로를 확인할 가치가 있는 이유",
      "check": "구체적인 확인 방법",
      "falsify": "반증 조건",
      "link_type": "news"
    }}
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
                        "당신은 사실과 가설을 구분하고, "
                        "검증 가능한 취재 경로를 설계하는 "
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
            temperature=0.25,
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

    def _normalize_report(self, report, fallback):
        if not isinstance(report, dict):
            return fallback

        paths = self._clean_reporting_paths(
            report.get("reporting_paths"),
            fallback["reporting_paths"]
        )

        return {
            "title": fallback["title"],
            "briefing": self._clean_output_text(
                report.get("briefing"),
                fallback["briefing"]
            ),
            "reporting_paths": paths,
            # 기존 호환 키
            "hypotheses": [
                path["hypothesis"]
                for path in paths
            ],
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
            "summary_metrics": fallback["summary_metrics"],
        }

    def _clean_reporting_paths(
        self,
        value,
        fallback,
        max_items=3
    ):
        if not isinstance(value, list):
            return fallback

        result = []
        allowed_link_types = {
            "source",
            "trends",
            "news"
        }

        for raw in value[:max_items]:
            if not isinstance(raw, dict):
                continue

            label = self._clean_output_text(
                raw.get("label"),
                "취재 경로"
            )
            hypothesis = self._clean_output_text(
                raw.get("hypothesis"),
                ""
            )
            why = self._clean_output_text(
                raw.get("why"),
                ""
            )
            check = self._clean_output_text(
                raw.get("check"),
                ""
            )
            falsify = self._clean_output_text(
                raw.get("falsify"),
                ""
            )

            link_type = self._safe_text(
                raw.get("link_type"),
                "trends"
            ).lower()

            if link_type not in allowed_link_types:
                link_type = "trends"

            if not hypothesis:
                continue

            result.append({
                "label": label,
                "hypothesis": hypothesis,
                "why": why,
                "check": check,
                "falsify": falsify,
                "link_type": link_type,
            })

        return result or fallback

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

        if len(text) > 1200:
            text = text[:1200].rstrip() + "…"

        # 화면에서 AI 문자열을 HTML로 실행하지 않도록 기본 정리
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

    def _safe_float(self, value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(self, value):
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return 0

    def _empty_report(self, message):
        return {
            "title": "분석 불가",
            "briefing": message,
            "reporting_paths": [],
            "hypotheses": [],
            "article_ideas": [],
            "questions": [],
            "verification_data": [],
            "summary_metrics": {},
        }
