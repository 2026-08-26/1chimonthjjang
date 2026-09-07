import json
import os
import re
from datetime import timezone
from email.utils import parsedate_to_datetime
from functools import lru_cache
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


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

        # 실제 외부 기사 검색 결과를 AI 추론과 분리해 붙입니다.
        # 실패해도 기존 AI 리포트는 정상 동작합니다.
        news_bundle = self._related_news_bundle(item)
        fallback["related_news"] = news_bundle["items"]
        fallback["related_news_query"] = news_bundle["query"]
        fallback["related_news_search_url"] = news_bundle["search_url"]
        fallback["related_news_source"] = news_bundle["source"]

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
                f"프로토타입 시뮬레이션 지수에서 '{title}' 항목은 단발성 상승보다 "
                "지속된 이상 흐름에 가깝습니다. 변화 크기, 통계적 이례성, 최근 지속성이 "
                f"함께 나타나 내부 취재 우선순위 {score}/100의 {signal} 후보로 분류했습니다. "
                "이 점수는 확률이나 정확도가 아닙니다. AI는 원인을 확정하지 않으며, "
                "아래 세 경로를 실제 외부 자료로 검증하는 것이 좋습니다."
            )
        elif signal == "MEDIUM":
            briefing = (
                f"프로토타입 시뮬레이션 지수에서 '{title}'의 평소와 다른 움직임이 확인됐지만 "
                "아직 모든 판단 축이 강하게 일치하는 것은 아닙니다. "
                f"내부 취재 우선순위는 {score}/100이며, 이 점수는 확률이나 정확도가 아닙니다. "
                "아래 검증 경로를 통해 실측 데이터에서도 같은 변화가 보이는지 먼저 확인하는 것이 좋습니다."
            )
        else:
            briefing = (
                f"프로토타입 시뮬레이션 지수에서 '{title}' 항목은 현재 설정된 종합 기준상 "
                "강한 우선 취재 신호로 보지 않습니다. 다만 실측 검색·플랫폼 지표와 "
                "공개 일정·외부 이슈의 시점을 확인하면 후속 관찰 여부를 판단하는 데 도움이 됩니다."
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

        article_draft = self._article_draft(
            title=title,
            category=category,
            cat_type=cat_type,
            signal=signal,
            inc_rate=inc_rate,
            score=score,
            z_score=z_score,
            anomaly_days=anomaly_days,
            max_consecutive=max_consecutive,
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
            "article_draft": article_draft,
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
        signal_evidence = (
            "프로토타입 시뮬레이션 지수에서 "
            f"기준 대비 {inc_rate:+.1f}% 변화, Z-score {z_score:.2f}, "
            f"최근 7일 중 이상 {anomaly_days}일, 최대 {max_consecutive}일 연속이 관찰됐습니다."
        )

        if cat_type == "music":
            return [
                {
                    "label": "공식 활동·공개 일정",
                    "hypothesis": (
                        "신곡·컴백·음악방송·공식 영상 등 콘텐츠 자체의 "
                        "공개 일정이 관심도 변화와 맞물렸을 가능성"
                    ),
                    "why": (
                        f"{signal_evidence} 여러 날 이어진 변화라면 단일 하루 노이즈보다 "
                        "공식 활동 일정과 시작 시점이 겹치는지 먼저 확인할 가치가 있습니다."
                    ),
                    "check": (
                        "실측 검색량을 확보한 뒤 상승 시작일과 신곡 공개, 음악방송, "
                        "공식 영상·직캠 업로드 날짜를 같은 타임라인에 놓고 비교합니다."
                    ),
                    "falsify": (
                        "실측 검색량에서 같은 상승이 재현되지 않거나, 상승 시점이 공식 활동과 "
                        "맞지 않으면 공식 일정 가설의 우선순위를 낮춥니다."
                    ),
                    "link_type": "source",
                },
                {
                    "label": "플랫폼·검색 노출",
                    "hypothesis": (
                        "차트 진입, 추천 노출, 검색량 확대 등 플랫폼 노출 변화가 "
                        "추가 유입을 만들었을 가능성"
                    ),
                    "why": (
                        "시뮬레이션상 상승이 최근 구간에 지속됐기 때문에, 실제 검색·차트·영상 지표가 "
                        "동시에 움직였다면 플랫폼 노출이 확산 경로였는지 검증할 수 있습니다."
                    ),
                    "check": (
                        "Google Trends와 음원 차트·영상 조회 흐름을 날짜별로 비교해 "
                        "검색 상승과 플랫폼 노출이 같은 시점에 움직였는지 확인합니다."
                    ),
                    "falsify": (
                        "실측 검색 관심만 상승하고 차트·영상·플랫폼 지표가 움직이지 않았다면 "
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
                    "why": (
                        "공식 일정이나 플랫폼 지표만으로 설명되지 않는 변화일 수 있으므로, "
                        "뉴스·SNS·커뮤니티 언급이 실측 검색 상승보다 먼저 증가했는지 확인할 가치가 있습니다."
                    ),
                    "check": (
                        "관련 뉴스·SNS·커뮤니티 게시물의 날짜별 증가 구간과 "
                        "실측 검색 관심 상승 시작 시점을 비교합니다."
                    ),
                    "falsify": (
                        "관련 언급량이 평소 수준이고 실측 검색 상승 시점과도 맞지 않으면 "
                        "외부 확산 가설의 우선순위를 낮춥니다."
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
                        "관심 변화와 맞물렸을 가능성"
                    ),
                    "why": (
                        f"{signal_evidence} 드라마는 공개·방송 일정이 명확하므로 "
                        "이상 흐름의 시작 시점과 회차 이벤트를 가장 먼저 대조하기 좋습니다."
                    ),
                    "check": (
                        "실측 검색량을 확보한 뒤 방송·OTT 공개일과 상승 시작일을 비교하고 "
                        "해당 회차의 공식 클립·시청 반응을 함께 확인합니다."
                    ),
                    "falsify": (
                        "실측 검색량에서 같은 상승이 없거나 방송·공개 일정과 무관한 시점에서 "
                        "변화가 시작됐다면 회차 효과 가설을 낮춥니다."
                    ),
                    "link_type": "source",
                },
                {
                    "label": "플랫폼 노출 변화",
                    "hypothesis": (
                        "OTT 순위, 추천 영역, 공식 클립 노출 증가가 "
                        "작품 검색 유입을 확대했을 가능성"
                    ),
                    "why": (
                        "시뮬레이션상 변화가 지속됐기 때문에 실제 OTT 순위·클립 조회·검색량이 "
                        "같은 구간에서 함께 움직였는지 확인하면 노출 효과를 검증할 수 있습니다."
                    ),
                    "check": (
                        "Google Trends와 OTT 순위·공식 클립 조회 변화의 날짜를 비교해 "
                        "동시에 상승했는지 확인합니다."
                    ),
                    "falsify": (
                        "OTT·클립 지표가 정체인데 실측 검색 관심만 상승했다면 "
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
                    "why": (
                        "작품 내부 이벤트와 별개로 출연진·외부 보도가 검색 유입을 만들 수 있으므로 "
                        "외부 언급의 선행 여부를 별도 축으로 확인해야 합니다."
                    ),
                    "check": (
                        "관련 뉴스와 커뮤니티 언급이 증가한 날짜를 찾아 "
                        "실측 작품 검색량 상승 구간과 겹치는지 확인합니다."
                    ),
                    "falsify": (
                        "관련 외부 이슈가 없거나 실측 검색 상승 시점과 크게 어긋난다면 "
                        "외부 이슈 가설의 우선순위를 낮춥니다."
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
                    "관심 변화와 맞물렸을 가능성"
                ),
                "why": (
                    f"{signal_evidence} 웹툰은 회차·공지 시점이 명확하므로 "
                    "실측 검색량과 작품 내부 일정의 선후 관계를 먼저 확인하기 좋습니다."
                ),
                "check": (
                    "작품 페이지에서 최근 회차 공개일과 공지·휴재·복귀 여부를 확인하고, "
                    "실측 검색량 상승 시작 시점과 비교합니다."
                ),
                "falsify": (
                    "실측 검색량에서 같은 변화가 없거나 작품 내부 일정과 시점이 맞지 않으면 "
                    "작품 내부 이벤트 가설의 우선순위를 낮춥니다."
                ),
                "link_type": "source",
            },
            {
                "label": "플랫폼 노출 변화",
                "hypothesis": (
                    "추천·랭킹·배너·프로모션 등 플랫폼 노출 변화가 "
                    "새로운 독자 유입을 만들었을 가능성"
                ),
                "why": (
                    "시뮬레이션상 최근 구간의 변화가 지속됐기 때문에 실제 플랫폼 순위·추천 노출·"
                    "관심등록과 검색량이 같은 시점에 움직였는지 확인하면 노출 가설을 검증할 수 있습니다."
                ),
                "check": (
                    "Google Trends 흐름과 플랫폼 내 순위·추천 노출·관심등록 변화가 "
                    "같은 시점에 나타나는지 확인합니다."
                ),
                "falsify": (
                    "플랫폼 순위나 노출 변화가 없는데 실측 검색 관심만 증가했다면 "
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
                "why": (
                    "작품 내부·플랫폼 변화와 별도로 외부 화제가 검색 상승을 선행했을 수 있으므로 "
                    "뉴스·커뮤니티·SNS 언급량을 독립적으로 대조할 가치가 있습니다."
                ),
                "check": (
                    "작품명 관련 뉴스·커뮤니티·SNS 언급량이 증가한 날짜를 찾아 "
                    "실측 검색 관심 상승 시작 시점과 비교합니다."
                ),
                "falsify": (
                    "관련 외부 언급이 평소 수준이고 실측 검색 상승 시점과도 맞지 않으면 "
                    "외부 확산 가설의 우선순위를 낮춥니다."
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
                f"프로토타입 시뮬레이션이 먼저 포착한 '{title}': "
                f"최근 {anomaly_days}일 이상 흐름, 실측 데이터에서도 재현될까"
            ),
            (
                f"'{title}' {signal} 취재 신호 검증: "
                "작품 내부 변화·플랫폼 노출·외부 화제를 시간순으로 추적"
            ),
            (
                f"{category} 이상감지 시연: "
                f"'{title}'의 {inc_rate:+.1f}% 시뮬레이션 변화가 실제 검색·플랫폼 지표에서도 "
                "나타나는지 확인"
            ),
        ]

    def _article_draft(
        self,
        title,
        category,
        cat_type,
        signal,
        inc_rate,
        score,
        z_score,
        anomaly_days,
        max_consecutive,
    ):
        """
        이상감지 결과를 기사 문장으로 구조화한 '취재 전 초안'.

        확인된 내부 지표만 사실 문장에 사용하고,
        실제 원인·사건·공식 발표·성과는 만들어내지 않습니다.
        내부 관심도 값은 반드시 시뮬레이션 지수라고 명시합니다.
        """

        if signal == "HIGH":
            headline = (
                f"DATA TIP-OFF 시뮬레이션이 포착한 '{title}' 이상흐름…"
                f"{anomaly_days}일 지속"
            )
        elif signal == "MEDIUM":
            headline = (
                f"시뮬레이션 지수에서 포착된 '{title}' 변화…"
                "실측 검증 필요한 신호"
            )
        else:
            headline = (
                f"'{title}' 시뮬레이션 관심도 지수, "
                "기준 구간과 비교해보니"
            )

        subheadline = (
            f"{category} 프로토타입에서 변화 크기·통계적 이례성·지속성을 종합 분석…"
            "실제 검색량·조회수는 아직 확인되지 않았으며 공식 일정·플랫폼·외부 화제 교차 검증 필요"
        )

        if cat_type == "music":
            cause_text = (
                "신곡·컴백·방송·공식 영상 같은 활동 일정, "
                "음원·영상 플랫폼 노출 변화, 뉴스·SNS·팬 커뮤니티 확산"
            )
            verify_items = [
                "실제 검색량(Google Trends·네이버 데이터랩 등)에서 동일한 상승이 재현되는지",
                "신곡·컴백·음악방송·공식 영상 공개 시점",
                "음원 차트·YouTube/숏폼·관련 뉴스·SNS의 날짜별 변화",
            ]

        elif cat_type == "drama":
            cause_text = (
                "최근 방송 회차·OTT 공개 같은 작품 이벤트, "
                "OTT 순위·공식 클립 노출 변화, 출연진·작품 관련 외부 이슈"
            )
            verify_items = [
                "실제 검색량에서 동일한 상승이 재현되는지",
                "방송 회차·OTT 공개·공식 클립 업로드 일정",
                "OTT 순위·시청률·클립 조회·관련 뉴스의 날짜별 변화",
            ]

        else:
            cause_text = (
                "최근 회차 공개·휴재 복귀·완결 같은 작품 내부 변화, "
                "추천·랭킹·프로모션 등 플랫폼 노출, 뉴스·SNS·커뮤니티 확산"
            )
            verify_items = [
                "실제 검색량에서 동일한 상승이 재현되는지",
                "회차 공개·휴재·복귀·완결·작품 공지 시점",
                "플랫폼 순위·댓글·관심등록·뉴스·커뮤니티의 날짜별 변화",
            ]

        body = [
            (
                f"DATA TIP-OFF 프로토타입의 시뮬레이션 관심도 지수에서 '{title}' 항목이 "
                "기준 구간과 다른 수준으로 나타났다. 이 값은 실제 네이버·구글 검색량이나 "
                "YouTube 조회수가 아니다. "
                f"최근 7일 평균 시뮬레이션 지수는 기준 구간 대비 {inc_rate:+.1f}% 변했고, "
                f"Z-score는 {z_score:.2f}로 계산됐다."
            ),
            (
                f"이번 신호는 최근 7일 중 {anomaly_days}일이 프로젝트의 관찰 기준선을 넘었고, "
                f"최대 {max_consecutive}일 연속으로 이상 움직임이 이어졌다. "
                "시스템은 변화 크기와 통계적 이례성, 지속성을 종합해 "
                f"내부 취재 우선순위 {score}/100의 {signal} 후보로 분류했다. "
                "이 점수는 기사 가치의 확률이나 예측 정확도가 아니다."
            ),
            (
                "이 결과만으로 실제 관심 증가나 원인을 판단할 수는 없다. "
                f"우선 실측 검색·플랫폼 데이터를 확보한 뒤 {cause_text}가 "
                "같은 시기에 있었는지 확인해야 한다."
            ),
            (
                "취재 단계에서는 시뮬레이션에서 포착된 변화 시점을 기준으로, "
                "실측 검색량·관련 일정·플랫폼 노출·외부 언급의 발생 시점을 같은 타임라인에 놓고 "
                "비교할 필요가 있다. 실측 지표에서 변화가 재현되지 않으면 해당 후보는 "
                "기사화보다 모델 검증 대상으로 돌리는 것이 타당하다."
            ),
            (
                "따라서 이 초안은 기사의 결론이 아니라 취재 순서를 정리한 작업 문서에 가깝다. "
                "실제 기사로 발전시키기 전에는 공식 자료와 실측 검색·플랫폼·언급량 데이터를 확보하고, "
                "각 가설을 반증할 자료까지 함께 확인해야 한다."
            ),
        ]

        return {
            "status": "DRAFT · 취재 전 · PROTOTYPE",
            "headline": headline,
            "subheadline": subheadline,
            "body": body,
            "must_verify": verify_items,
            "verification_note": (
                "이 초안의 내부 관심도 수치는 시뮬레이션 지수입니다. "
                "실측 데이터에서 동일한 변화가 확인되기 전에는 실제 관심 증가로 표현하면 안 됩니다. "
                "게시 전 공식 자료·외부 데이터·추가 취재를 통한 사실 확인이 필요합니다."
            ),
        }

    def _reporting_questions(self, cat_type, title):
        if cat_type == "music":
            return [
                "실측 검색 관심 상승이 시작된 날짜 전후에 신곡·컴백·방송·공식 영상 공개가 있었는가?",
                "음원 차트·YouTube·숏폼 지표도 검색 관심과 같은 시점에 움직였는가?",
                "팬덤 내부 반응과 일반 대중·해외 검색 반응이 같은 방향으로 움직이는가?",
            ]

        if cat_type == "drama":
            return [
                "실측 검색 관심 상승이 특정 방송 회차나 OTT 공개 시점과 겹치는가?",
                "OTT 순위·시청률·공식 클립 조회수도 같은 구간에서 변했는가?",
                "출연진 관련 보도·인터뷰·이슈가 작품 검색 증가보다 먼저 나타났는가?",
            ]

        return [
            "실측 검색 관심 상승이 최근 회차 공개·휴재 복귀·완결·공지 시점과 겹치는가?",
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
            "data_scope": (
                "CSV 콘텐츠 메타데이터 + 재현 가능한 30일 시뮬레이션 관심도 지수"
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
10. 기사 아이디어는 확인 전 사실을 제목처럼 확정하지 말고, 내부 지표를 말할 때는 반드시 '시뮬레이션' 또는 '프로토타입'임을 드러내세요.
11. article_draft는 실제 기사처럼 읽히는 4~6문단의 '취재 전 초안'으로 작성하세요.
12. article_draft에는 입력으로 주어진 이상감지 수치만 사실로 사용할 수 있습니다.
13. 실제 사건·인물 발언·공식 발표·성과·원인은 제공되지 않았으므로 절대 만들어내지 마세요.
14. article_draft 본문에서 이 수치는 실제 검색량이 아니라 DATA TIP-OFF 프로토타입의 시뮬레이션 관심도 지수임을 명확히 밝히세요.
15. 제목과 부제는 흥미를 주되 실제 관심 증가가 확인된 것처럼 쓰지 말고 '시뮬레이션/프로토타입' 표현을 포함하세요.
16. 기사 본문은 '탐지된 사실 → 지속성 해석 → 실측 재현 확인 → 가능한 검증 방향 → 교차 검증 필요 → 데이터 한계' 순서로 구성하세요.
17. reporting_paths의 why는 세 카드에 같은 숫자 문장을 반복하지 말고, 각 경로를 왜 확인해야 하는지 서로 다르게 설명하세요.
18. briefing과 reporting_paths에서 내부 지표를 실제 검색량·조회수·대중 관심 증가처럼 표현하지 마세요.

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
  ],
  "article_draft": {
    "status": "DRAFT · 취재 전",
    "headline": "검증 전 원인을 단정하지 않는 기사형 제목",
    "subheadline": "데이터에서 확인된 변화와 추가 검증 필요성을 설명하는 부제",
    "body": [
      "기사 본문 1문단",
      "기사 본문 2문단",
      "기사 본문 3문단",
      "기사 본문 4문단",
      "기사 본문 5문단"
    ],
    "must_verify": [
      "기사화 전 확인할 자료 1",
      "기사화 전 확인할 자료 2",
      "기사화 전 확인할 자료 3"
    ],
    "verification_note": "게시 전 사실 확인이 필요하다는 짧은 안내"
  }
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
    # REAL RELATED NEWS
    # =========================================================

    def _related_news_bundle(self, item):
        """
        실제 기사 검색 결과를 가져옵니다.

        - AI가 기사 제목/링크를 생성하지 않습니다.
        - Google News RSS가 반환한 실제 검색 결과만 사용합니다.
        - 네트워크 실패 시 빈 목록으로 안전하게 fallback 합니다.
        """

        title = self._safe_text(
            item.get("title"),
            ""
        )

        cat_type = self._safe_text(
            item.get("category"),
            ""
        ).lower()

        query = self._build_news_query(
            title=title,
            cat_type=cat_type,
        )

        search_url = (
            "https://news.google.com/search?"
            f"q={quote_plus(query)}"
            "&hl=ko&gl=KR&ceid=KR%3Ako"
        )

        if not query:
            return {
                "items": [],
                "query": "",
                "search_url": search_url,
                "source": "Google News",
            }

        items = self._fetch_google_news_rss(
            query
        )

        return {
            "items": items,
            "query": query,
            "search_url": search_url,
            "source": "Google News RSS",
        }

    def _build_news_query(
        self,
        title,
        cat_type,
    ):
        title = self._safe_text(
            title,
            ""
        )

        if not title:
            return ""

        parts = [
            value.strip()
            for value in re.split(
                r"\s*[-–—]\s*",
                title
            )
            if value.strip()
        ]

        if len(parts) >= 2:
            query = " ".join(
                f'"{part}"'
                for part in parts[:3]
            )
        else:
            query = f'"{title}"'

        category_hint = {
            "music": "K-pop",
            "drama": "드라마",
            "webtoon": "웹툰",
        }.get(
            cat_type,
            ""
        )

        if category_hint:
            query = (
                f"{query} {category_hint}"
            )

        return query[:350]

    @staticmethod
    @lru_cache(maxsize=64)
    def _fetch_google_news_rss(query):
        """
        Google News RSS 검색 결과에서 실제 기사 링크를 최대 6건 반환합니다.
        앱 실행 중 동일 검색어는 메모리 캐시를 사용합니다.
        """

        if not query:
            return []

        rss_url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}"
            "&hl=ko&gl=KR&ceid=KR%3Ako"
        )

        request = Request(
            rss_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/124 Safari/537.36"
                ),
                "Accept": (
                    "application/rss+xml,"
                    "application/xml;q=0.9,*/*;q=0.8"
                ),
            },
        )

        try:
            with urlopen(
                request,
                timeout=3.0
            ) as response:
                payload = response.read(
                    1_500_000
                )
        except Exception as exc:
            print(
                "[TrendAIAgent] 관련 뉴스 조회 실패:",
                type(exc).__name__,
            )
            return []

        try:
            root = ET.fromstring(
                payload
            )
        except ET.ParseError:
            return []

        result = []
        seen = set()

        for node in root.findall(
            ".//item"
        ):
            raw_title = (
                node.findtext("title")
                or ""
            ).strip()

            raw_link = (
                node.findtext("link")
                or ""
            ).strip()

            raw_date = (
                node.findtext("pubDate")
                or ""
            ).strip()

            source_node = node.find(
                "source"
            )

            source = (
                (source_node.text or "").strip()
                if source_node is not None
                else ""
            )

            if not raw_title or not raw_link:
                continue

            parsed = urlparse(
                raw_link
            )

            if parsed.scheme not in {
                "http",
                "https",
            }:
                continue

            article_title = raw_title

            if source:
                suffix = (
                    " - "
                    + source
                )

                if article_title.endswith(
                    suffix
                ):
                    article_title = (
                        article_title[
                            :-len(suffix)
                        ].strip()
                    )

            clean_key = (
                article_title.casefold(),
                source.casefold(),
            )

            if clean_key in seen:
                continue

            seen.add(clean_key)

            published_at = ""
            published_label = ""

            if raw_date:
                try:
                    dt = parsedate_to_datetime(
                        raw_date
                    )

                    if dt.tzinfo is None:
                        dt = dt.replace(
                            tzinfo=timezone.utc
                        )

                    published_at = (
                        dt.astimezone(
                            timezone.utc
                        )
                        .isoformat()
                    )

                    published_label = (
                        dt.strftime(
                            "%Y.%m.%d"
                        )
                    )

                except Exception:
                    published_label = (
                        raw_date[:24]
                    )

            result.append({
                "title": article_title[:300],
                "source": source[:120],
                "published_at": published_at,
                "published_label": published_label,
                "url": raw_link,
            })

            if len(result) >= 6:
                break

        return result

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
            "article_draft": self._clean_article_draft(
                report.get("article_draft"),
                fallback["article_draft"]
            ),
            # 실제 기사 목록은 LLM이 만들지 않습니다.
            # 서버가 외부 뉴스 RSS에서 가져온 결과만 그대로 전달합니다.
            "related_news": fallback.get("related_news", []),
            "related_news_query": fallback.get("related_news_query", ""),
            "related_news_search_url": fallback.get("related_news_search_url", ""),
            "related_news_source": fallback.get("related_news_source", ""),
            "summary_metrics": fallback["summary_metrics"],
        }

    def _clean_article_draft(self, value, fallback):
        if not isinstance(value, dict):
            return fallback

        body = self._clean_string_list(
            value.get("body"),
            fallback["body"],
            max_items=6
        )

        must_verify = self._clean_string_list(
            value.get("must_verify"),
            fallback["must_verify"],
            max_items=4
        )

        return {
            "status": self._clean_output_text(
                value.get("status"),
                fallback["status"]
            ),
            "headline": self._clean_output_text(
                value.get("headline"),
                fallback["headline"]
            ),
            "subheadline": self._clean_output_text(
                value.get("subheadline"),
                fallback["subheadline"]
            ),
            "body": body,
            "must_verify": must_verify,
            "verification_note": self._clean_output_text(
                value.get("verification_note"),
                fallback["verification_note"]
            ),
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
            "related_news": [],
            "related_news_query": "",
            "related_news_search_url": "",
            "related_news_source": "",
            "article_draft": {
                "status": "DRAFT · 생성 불가",
                "headline": "",
                "subheadline": "",
                "body": [],
                "must_verify": [],
                "verification_note": message,
            },
            "summary_metrics": {},
        }
