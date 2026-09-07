import json
import re
import ssl
from functools import lru_cache
from html import unescape
from urllib.parse import parse_qs, quote_plus, urlencode, urlparse
from urllib.request import Request, urlopen

from flask import Blueprint, Response, redirect, request


kcontent_media_bp = Blueprint(
    "kcontent_media",
    __name__,
)


USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# 학교/회사 PC의 Python 인증서 문제 때문에
# 외부 공개 이미지/API 조회용 fallback context를 둡니다.
SSL_CONTEXT = ssl._create_unverified_context()


JSON_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
}


NAVER_HEADERS = {
    **JSON_HEADERS,
    "Referer": "https://comic.naver.com/",
}


def _clean(value, limit=500):
    return str(value or "").strip()[:limit]


def _norm(value):
    value = _clean(value, 1000).lower()

    value = re.sub(
        r"[’'\"`]",
        "",
        value,
    )

    value = re.sub(
        r"[^0-9a-z가-힣]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _tokens(value):
    return [
        token
        for token in _norm(value).split()
        if len(token) >= 1
    ]


def _http_bytes(
    url,
    headers=None,
    timeout=5.5,
):
    req = Request(
        url,
        headers=headers or JSON_HEADERS,
    )

    with urlopen(
        req,
        timeout=timeout,
        context=SSL_CONTEXT,
    ) as response:
        return (
            response.read(3_000_000),
            (
                response.headers.get(
                    "Content-Type",
                    ""
                )
                .split(";")[0]
                .strip()
                .lower()
            ),
        )


def _http_text(
    url,
    headers=None,
    timeout=5.5,
):
    raw, _ = _http_bytes(
        url,
        headers=headers,
        timeout=timeout,
    )

    return raw.decode(
        "utf-8",
        errors="replace",
    )


def _http_json(
    url,
    headers=None,
    timeout=5.5,
):
    return json.loads(
        _http_text(
            url,
            headers=headers,
            timeout=timeout,
        )
    )


# =========================================================
# MUSIC KEY = K-POP IDOL DATA
#
# 중요:
# kpopidolsv3.csv는 "노래 목록"이 아닙니다.
# Stage Name / Full Name / Group / Company 등의 아이돌 멤버 메타데이터입니다.
#
# 그래서 category 내부 키는 기존 호환 때문에 "music"을 유지하지만,
# 썸네일은 앨범 커버가 아니라 다음 순서로 찾습니다.
#
# 1) 해당 멤버 프로필 이미지
# 2) 멤버 이미지가 없으면 해당 그룹 이미지
# 3) 둘 다 없으면 IDOL 기본 타일
# =========================================================

def _split_music_title(title):
    """
    현재 제목 형식:
    Group - Stage Name

    예:
    After School - Raina
    ZE:A - Minwoo
    NCT - Taeil
    """
    parts = [
        part.strip()
        for part in re.split(
            r"\s*[-–—]\s*",
            title,
        )
        if part.strip()
    ]

    if len(parts) >= 2:
        return (
            parts[0],
            " ".join(parts[1:]),
        )

    return (
        title.strip(),
        "",
    )


def _name_aliases(value):
    """
    띄어쓰기/기호 차이 보정.

    예:
    New Sun -> Newsun
    ZE:A -> ZEA
    After School -> Afterschool
    """
    value = _clean(
        value,
        300,
    )

    if not value:
        return []

    aliases = [
        value,
    ]

    compact = re.sub(
        r"\s+",
        "",
        value,
    )

    plain = re.sub(
        r"[^0-9A-Za-z가-힣]+",
        "",
        value,
    )

    for candidate in (
        compact,
        plain,
    ):
        if (
            candidate
            and candidate.lower()
            not in {
                item.lower()
                for item in aliases
            }
        ):
            aliases.append(
                candidate
            )

    return aliases


def _wikipedia_candidates(
    query,
    language,
):
    params = urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "0",
        "gsrlimit": 8,
        "prop": "pageimages|extracts",
        "piprop": "thumbnail|original",
        "pithumbsize": 500,
        "exintro": 1,
        "explaintext": 1,
        "exchars": 1000,
        "origin": "*",
    })

    url = (
        f"https://{language}.wikipedia.org/w/api.php?"
        + params
    )

    try:
        data = _http_json(
            url,
            timeout=5.0,
        )
    except Exception as exc:
        print(
            "[KCONTENT IDOL WIKI]",
            type(exc).__name__,
            language,
            query,
        )
        return []

    if not isinstance(
        data,
        dict,
    ):
        return []

    pages = (
        data.get("query", {})
        .get("pages", {})
    )

    if not isinstance(
        pages,
        dict,
    ):
        return []

    result = []

    for page in pages.values():
        if not isinstance(
            page,
            dict,
        ):
            continue

        thumbnail = (
            page.get("thumbnail")
            or {}
        )

        original = (
            page.get("original")
            or {}
        )

        image = _clean(
            thumbnail.get("source")
            or original.get("source")
            or "",
            1800,
        )

        if not image:
            continue

        result.append({
            "title": _clean(
                page.get("title"),
                300,
            ),
            "extract": _clean(
                page.get("extract"),
                1500,
            ),
            "image": image,
        })

    return result


def _idol_member_score(
    candidate,
    group,
    member,
):
    """
    멤버 이미지 판정.

    - 멤버 이름이 반드시 후보 제목/설명에 있어야 함
    - 그룹 이름도 설명에 확인되면 높은 점수
    - 가수/아이돌/멤버 관련 표현 가산
    """
    page_title = _norm(
        candidate.get("title")
    )

    body = _norm(
        (
            candidate.get("title", "")
            + " "
            + candidate.get("extract", "")
        )
    )

    member_aliases = _name_aliases(
        member
    )

    group_aliases = _name_aliases(
        group
    )

    member_hit = any(
        _norm(alias)
        and _norm(alias) in body
        for alias in member_aliases
    )

    if not member_hit:
        return -1

    score = 40

    if any(
        _norm(alias)
        and _norm(alias) in page_title
        for alias in member_aliases
    ):
        score += 40

    group_hit = any(
        _norm(alias)
        and _norm(alias) in body
        for alias in group_aliases
    )

    if group_hit:
        score += 30

    if re.search(
        r"\b(singer|rapper|idol|member|vocalist)\b|가수|래퍼|아이돌|멤버|보컬",
        body,
    ):
        score += 8

    return score


def _idol_group_score(
    candidate,
    group,
):
    page_title = _norm(
        candidate.get("title")
    )

    body = _norm(
        (
            candidate.get("title", "")
            + " "
            + candidate.get("extract", "")
        )
    )

    aliases = _name_aliases(
        group
    )

    group_hit = any(
        _norm(alias)
        and _norm(alias) in body
        for alias in aliases
    )

    if not group_hit:
        return -1

    score = 30

    if any(
        _norm(alias)
        and _norm(alias) in page_title
        for alias in aliases
    ):
        score += 50

    if re.search(
        r"\b(group|band|girl group|boy band|k-pop|kpop)\b|그룹|걸그룹|보이그룹",
        body,
    ):
        score += 10

    return score


def _best_wikipedia_image(
    queries,
    scorer,
):
    best_url = ""
    best_score = -1

    for query in queries:
        for language in (
            "ko",
            "en",
        ):
            candidates = (
                _wikipedia_candidates(
                    query,
                    language,
                )
            )

            for candidate in candidates:
                score = scorer(
                    candidate
                )

                if score > best_score:
                    best_score = score
                    best_url = (
                        candidate.get("image")
                        or ""
                    )

            if (
                best_url
                and best_score >= 70
            ):
                return best_url

    return (
        best_url
        if best_score >= 0
        else ""
    )


def _commons_candidates(query):
    params = urlencode({
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": 12,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 500,
        "origin": "*",
    })

    url = (
        "https://commons.wikimedia.org/w/api.php?"
        + params
    )

    try:
        data = _http_json(
            url,
            timeout=5.0,
        )
    except Exception as exc:
        print(
            "[KCONTENT IDOL COMMONS]",
            type(exc).__name__,
            query,
        )
        return []

    if not isinstance(
        data,
        dict,
    ):
        return []

    pages = (
        data.get("query", {})
        .get("pages", {})
    )

    if not isinstance(
        pages,
        dict,
    ):
        return []

    result = []

    for page in pages.values():
        if not isinstance(
            page,
            dict,
        ):
            continue

        infos = page.get(
            "imageinfo"
        )

        if not isinstance(
            infos,
            list,
        ) or not infos:
            continue

        info = infos[0]

        if not isinstance(
            info,
            dict,
        ):
            continue

        metadata = (
            info.get("extmetadata")
            or {}
        )

        meta_text = []

        if isinstance(
            metadata,
            dict,
        ):
            for key in (
                "ObjectName",
                "ImageDescription",
                "Categories",
            ):
                node = metadata.get(
                    key
                )

                if (
                    isinstance(
                        node,
                        dict,
                    )
                    and node.get("value")
                ):
                    meta_text.append(
                        str(
                            node.get("value")
                        )
                    )

        image = _clean(
            info.get("thumburl")
            or info.get("url")
            or "",
            1800,
        )

        if not image:
            continue

        result.append({
            "title": _clean(
                page.get("title"),
                500,
            ),
            "extract": " ".join(
                meta_text
            ),
            "image": image,
        })

    return result


def _best_commons_image(
    queries,
    scorer,
):
    best_url = ""
    best_score = -1

    for query in queries:
        candidates = (
            _commons_candidates(
                query
            )
        )

        for candidate in candidates:
            score = scorer(
                candidate
            )

            if score > best_score:
                best_score = score
                best_url = (
                    candidate.get("image")
                    or ""
                )

        if (
            best_url
            and best_score >= 70
        ):
            return best_url

    return (
        best_url
        if best_score >= 0
        else ""
    )


def _resolve_music(title):
    """
    기존 내부 category='music'은 유지하지만
    CSV 성격에 맞춰 '아이돌 멤버/그룹 이미지'를 반환합니다.
    """
    group, member = (
        _split_music_title(
            title
        )
    )

    # -----------------------------------------------------
    # 1순위: 정확한 멤버 이미지
    # -----------------------------------------------------
    if group and member:
        member_queries = [
            f'"{member}" "{group}" K-pop',
            f'"{member}" "{group}" singer',
            f'{member} {group} idol',
        ]

        member_scorer = (
            lambda candidate:
                _idol_member_score(
                    candidate,
                    group,
                    member,
                )
        )

        image = (
            _best_wikipedia_image(
                member_queries,
                member_scorer,
            )
        )

        if image:
            return image

        image = (
            _best_commons_image(
                member_queries,
                member_scorer,
            )
        )

        if image:
            return image

    # -----------------------------------------------------
    # 2순위: 정확한 그룹 이미지
    # -----------------------------------------------------
    group_name = (
        group
        or title
    )

    if group_name:
        group_queries = [
            f'"{group_name}" K-pop group',
            f'"{group_name}" idol group',
            group_name,
        ]

        group_scorer = (
            lambda candidate:
                _idol_group_score(
                    candidate,
                    group_name,
                )
        )

        image = (
            _best_wikipedia_image(
                group_queries,
                group_scorer,
            )
        )

        if image:
            return image

        image = (
            _best_commons_image(
                group_queries,
                group_scorer,
            )
        )

        if image:
            return image

    return ""


# =========================================================
# DRAMA
# TVMaze의 실제 show poster
# =========================================================

def _drama_score(show, title):
    wanted = _tokens(
        title
    )

    show_name = _norm(
        show.get("name")
    )

    if not show_name:
        return -1

    matches = sum(
        1
        for token in wanted
        if token in show_name
    )

    score = matches * 20

    if (
        _norm(title)
        == show_name
    ):
        score += 80

    if (
        _norm(
            show.get("language")
        )
        == "korean"
    ):
        score += 15

    network = (
        show.get("network")
        or show.get("webChannel")
        or {}
    )

    country = (
        network.get("country")
        or {}
    )

    if (
        _norm(
            country.get("code")
        )
        == "kr"
    ):
        score += 10

    return score


def _resolve_drama(title):
    url = (
        "https://api.tvmaze.com/search/shows?q="
        + quote_plus(title)
    )

    try:
        rows = _http_json(
            url,
            timeout=5.0,
        )
    except Exception as exc:
        print(
            "[KCONTENT DRAMA SEARCH]",
            type(exc).__name__,
            title,
        )

        return ""

    if not isinstance(
        rows,
        list,
    ):
        return ""

    best_url = ""
    best_score = -1

    for row in rows[:20]:
        if not isinstance(
            row,
            dict,
        ):
            continue

        show = row.get("show")

        if not isinstance(
            show,
            dict,
        ):
            continue

        image = (
            show.get("image")
            or {}
        )

        poster = _clean(
            image.get("original")
            or image.get("medium")
            or "",
            1500,
        )

        if not poster:
            continue

        score = _drama_score(
            show,
            title,
        )

        if score > best_score:
            best_score = score
            best_url = poster

    return (
        best_url
        if best_score >= 20
        else ""
    )


# =========================================================
# WEBTOON
# Naver titleId -> 작품 페이지 og:image 우선
# =========================================================

def _title_id_from_url(url):
    try:
        parsed = urlparse(url)

        values = parse_qs(
            parsed.query
        ).get(
            "titleId"
        )

        if values:
            return _clean(
                values[0],
                30,
            )

    except Exception:
        pass

    return ""


def _og_image_from_html(html):
    patterns = [
        (
            r'<meta[^>]+property=["\']og:image["\'][^>]+'
            r'content=["\']([^"\']+)["\']'
        ),
        (
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+'
            r'property=["\']og:image["\']'
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            html,
            flags=re.I,
        )

        if match:
            return unescape(
                match.group(1)
            ).strip()

    return ""


def _naver_webtoon_page_image(
    title_id
):
    if not title_id:
        return ""

    page_url = (
        "https://comic.naver.com/webtoon/list?"
        f"titleId={quote_plus(title_id)}"
    )

    try:
        html = _http_text(
            page_url,
            headers=NAVER_HEADERS,
            timeout=5.0,
        )

        image = _og_image_from_html(
            html
        )

        if image:
            return image

    except Exception as exc:
        print(
            "[KCONTENT WEBTOON PAGE]",
            type(exc).__name__,
            title_id,
        )

    return ""


def _walk_objects(value):
    result = []

    def walk(node):
        if isinstance(node, dict):
            result.append(node)

            for child in node.values():
                walk(child)

        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)

    return result


def _find_webtoon_search_result(
    data,
    title,
):
    wanted = _norm(
        title
    )

    best = None
    best_score = -1

    for obj in _walk_objects(
        data
    ):
        candidate_title = _clean(
            obj.get("titleName")
            or obj.get("webtoonTitle")
            or obj.get("title")
            or obj.get("name")
            or "",
            300,
        )

        if not candidate_title:
            continue

        normalized = _norm(
            candidate_title
        )

        score = 0

        if normalized == wanted:
            score += 100

        elif (
            wanted
            and (
                wanted in normalized
                or normalized in wanted
            )
        ):
            score += 50

        title_id = _clean(
            obj.get("titleId")
            or obj.get("id")
            or "",
            30,
        )

        image = _clean(
            obj.get("thumbnailUrl")
            or obj.get("thumbnailImageUrl")
            or obj.get("imageUrl")
            or obj.get("thumbnail")
            or "",
            1500,
        )

        if score > best_score and (
            title_id
            or image
        ):
            best_score = score

            best = {
                "title_id": title_id,
                "image": image,
            }

    return (
        best
        if best_score >= 50
        else None
    )


def _resolve_webtoon(
    title,
    external_url,
):
    # 1) 기존 CSV/loader가 제공한 direct titleId
    title_id = _title_id_from_url(
        external_url
    )

    if title_id:
        image = _naver_webtoon_page_image(
            title_id
        )

        if image:
            return image

    # 2) 네이버 웹툰 내부 검색 API
    keyword = quote_plus(
        title
    )

    search_urls = [
        (
            "https://comic.naver.com/api/search/all?"
            f"keyword={keyword}"
        ),
        (
            "https://comic.naver.com/api/search/webtoon?"
            f"keyword={keyword}"
        ),
    ]

    for url in search_urls:
        try:
            data = _http_json(
                url,
                headers=NAVER_HEADERS,
                timeout=5.0,
            )
        except Exception:
            continue

        best = _find_webtoon_search_result(
            data,
            title,
        )

        if not best:
            continue

        if best.get("title_id"):
            image = _naver_webtoon_page_image(
                best["title_id"]
            )

            if image:
                return image

        image = _clean(
            best.get("image"),
            1500,
        )

        if image:
            if image.startswith("//"):
                image = (
                    "https:"
                    + image
                )

            return image

    return ""


# =========================================================
# PLACEHOLDER
# =========================================================

def _placeholder_svg(category):
    if category == "music":
        label = "IDOL"
        symbol = "★"
        bg = "#f2edf0"

    elif category == "drama":
        label = "DRAMA"
        symbol = "▶"
        bg = "#eef0f3"

    else:
        label = "WEBTOON"
        symbol = "▦"
        bg = "#edf2eb"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="240" height="320" viewBox="0 0 240 320">
    <rect width="240" height="320" rx="24" fill="{bg}"/>
    <text x="120" y="145" text-anchor="middle" font-size="52" font-family="Arial,sans-serif" fill="#555">{symbol}</text>
    <text x="120" y="188" text-anchor="middle" font-size="18" font-weight="700" font-family="Arial,sans-serif" fill="#555">{label}</text>
    </svg>"""

    return Response(
        svg.encode("utf-8"),
        mimetype="image/svg+xml",
    )


@lru_cache(maxsize=256)
def _resolve_remote_url(
    category,
    title,
    external_url,
):
    if category == "music":
        return _resolve_music(
            title
        )

    if category == "drama":
        return _resolve_drama(
            title
        )

    if category == "webtoon":
        return _resolve_webtoon(
            title,
            external_url,
        )

    return ""


@kcontent_media_bp.get(
    "/api/kcontent-thumbnail"
)
def thumbnail():
    category = _clean(
        request.args.get(
            "category"
        ),
        30,
    )

    title = _clean(
        request.args.get(
            "title"
        ),
        220,
    )

    external_url = _clean(
        request.args.get(
            "external_url"
        ),
        1200,
    )

    if category not in {
        "music",
        "drama",
        "webtoon",
    }:
        category = "webtoon"

    if not title:
        return _placeholder_svg(
            category
        )

    try:
        remote_url = _resolve_remote_url(
            category,
            title,
            external_url,
        )

    except Exception as exc:
        print(
            "[KCONTENT THUMBNAIL RESOLVE]",
            type(exc).__name__,
            title,
        )

        remote_url = ""

    if not remote_url:
        return _placeholder_svg(
            category
        )

    # Apple / TVMaze/CDN 이미지는 브라우저가 직접 읽게 하면
    # 서버의 이미지 인증서/Content-Type 문제를 피할 수 있습니다.
    parsed = urlparse(
        remote_url
    )

    host = (
        parsed.netloc
        .lower()
        .split(":")[0]
    )

    if (
        category in {
            "music",
            "drama",
        }
        and host
    ):
        return redirect(
            remote_url,
            code=302,
        )

    # 네이버 웹툰 이미지는 Referer가 필요한 경우가 있어서
    # 서버가 proxy하여 반환합니다.
    try:
        raw, content_type = _http_bytes(
            remote_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://comic.naver.com/",
            },
            timeout=5.5,
        )

        if (
            raw
            and content_type.startswith(
                "image/"
            )
        ):
            response = Response(
                raw,
                mimetype=content_type,
            )

            response.headers[
                "Cache-Control"
            ] = (
                "public, max-age=21600"
            )

            return response

    except Exception as exc:
        print(
            "[KCONTENT WEBTOON IMAGE]",
            type(exc).__name__,
            title,
        )

    return _placeholder_svg(
        category
    )
