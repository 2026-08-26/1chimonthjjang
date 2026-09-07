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
# MUSIC
# 실제 "앨범 커버" 전용
#
# 현재 CSV는 곡명/앨범명이 아니라
# Group + Stage Name 구조이므로:
#
# 1) 그룹명으로 실제 앨범 검색
# 2) 없으면 멤버명으로 실제 앨범 검색
# 3) Deezer 우선
# 4) iTunes fallback
#
# 사람 사진은 사용하지 않습니다.
# =========================================================

def _split_music_title(title):
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


def _artist_exact_score(
    artist_name,
    wanted,
):
    artist_norm = _norm(
        artist_name
    )

    wanted_norm = _norm(
        wanted
    )

    if not artist_norm or not wanted_norm:
        return -1

    if artist_norm == wanted_norm:
        return 100

    artist_tokens = _tokens(
        artist_name
    )

    wanted_tokens = _tokens(
        wanted
    )

    matched = sum(
        1
        for token in wanted_tokens
        if token in artist_norm
    )

    if not wanted_tokens:
        return -1

    if matched == len(
        wanted_tokens
    ):
        return (
            70
            + min(
                len(artist_tokens),
                5,
            )
        )

    # 너무 느슨한 동명이인 매칭은 사용하지 않습니다.
    return -1


# ---------------------------------------------------------
# DEEZER
# ---------------------------------------------------------

def _deezer_album_rows(
    artist_name,
):
    if not artist_name:
        return []

    queries = [
        (
            "https://api.deezer.com/search/album?q="
            + quote_plus(
                f'artist:"{artist_name}"'
            )
            + "&limit=25"
        ),
        (
            "https://api.deezer.com/search?q="
            + quote_plus(
                f'artist:"{artist_name}"'
            )
            + "&limit=25"
        ),
    ]

    result = []

    for url in queries:
        try:
            data = _http_json(
                url,
                timeout=5.0,
            )
        except Exception as exc:
            print(
                "[KCONTENT DEEZER]",
                type(exc).__name__,
                artist_name,
            )
            continue

        if not isinstance(
            data,
            dict,
        ):
            continue

        rows = data.get(
            "data",
            [],
        )

        if not isinstance(
            rows,
            list,
        ):
            continue

        result.extend(
            row
            for row in rows
            if isinstance(
                row,
                dict,
            )
        )

        if result:
            break

    return result


def _deezer_album_info(
    row,
):
    """
    search/album 결과와 일반 search 결과를 모두 처리합니다.
    반환:
    (artist_name, album_title, cover_url)
    """

    artist = (
        row.get("artist")
        or {}
    )

    artist_name = _clean(
        (
            artist.get("name")
            if isinstance(
                artist,
                dict,
            )
            else ""
        ),
        300,
    )

    # search/album:
    # row 자체가 앨범
    album_title = _clean(
        row.get("title"),
        300,
    )

    cover = _clean(
        (
            row.get("cover_xl")
            or row.get("cover_big")
            or row.get("cover_medium")
            or row.get("cover")
            or ""
        ),
        1500,
    )

    # 일반 track search:
    # row["album"] 안에 앨범 커버가 있음
    nested_album = (
        row.get("album")
        or {}
    )

    if (
        not cover
        and isinstance(
            nested_album,
            dict,
        )
    ):
        album_title = _clean(
            (
                nested_album.get("title")
                or album_title
            ),
            300,
        )

        cover = _clean(
            (
                nested_album.get("cover_xl")
                or nested_album.get("cover_big")
                or nested_album.get("cover_medium")
                or nested_album.get("cover")
                or ""
            ),
            1500,
        )

    return (
        artist_name,
        album_title,
        cover,
    )


def _resolve_deezer_album(
    artist_name,
):
    rows = _deezer_album_rows(
        artist_name
    )

    best_url = ""
    best_score = -1

    for row in rows:
        (
            candidate_artist,
            album_title,
            cover,
        ) = _deezer_album_info(
            row
        )

        if not cover:
            continue

        score = _artist_exact_score(
            candidate_artist,
            artist_name,
        )

        if score < 0:
            continue

        # 앨범 제목이 있으면 실제 앨범 결과라는 뜻이므로 약간 가산
        if album_title:
            score += 5

        if score > best_score:
            best_score = score
            best_url = cover

    return best_url


# ---------------------------------------------------------
# iTunes fallback
# ---------------------------------------------------------

def _itunes_artwork(row):
    return _clean(
        row.get("artworkUrl100")
        or row.get("artworkUrl60")
        or "",
        1500,
    )


def _upgrade_artwork(url):
    if not url:
        return ""

    url = re.sub(
        r"/\d+x\d+bb\.",
        "/600x600bb.",
        url,
    )

    url = re.sub(
        r"\d+x\d+bb",
        "600x600bb",
        url,
    )

    return url


def _itunes_album_search(
    artist_name,
):
    if not artist_name:
        return []

    params = urlencode({
        "term": artist_name,
        "media": "music",
        "entity": "album",
        "attribute": "artistTerm",
        "limit": 50,
        "country": "KR",
    })

    url = (
        "https://itunes.apple.com/search?"
        + params
    )

    try:
        data = _http_json(
            url,
            timeout=5.0,
        )
    except Exception as exc:
        print(
            "[KCONTENT ITUNES]",
            type(exc).__name__,
            artist_name,
        )
        return []

    if not isinstance(
        data,
        dict,
    ):
        return []

    rows = data.get(
        "results",
        [],
    )

    return (
        rows
        if isinstance(
            rows,
            list,
        )
        else []
    )


def _resolve_itunes_album(
    artist_name,
):
    rows = _itunes_album_search(
        artist_name
    )

    best_url = ""
    best_score = -1

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            continue

        artwork = _upgrade_artwork(
            _itunes_artwork(
                row
            )
        )

        if not artwork:
            continue

        candidate_artist = _clean(
            row.get("artistName"),
            300,
        )

        score = _artist_exact_score(
            candidate_artist,
            artist_name,
        )

        if score < 0:
            continue

        collection = _clean(
            row.get("collectionName"),
            300,
        )

        if collection:
            score += 5

        if score > best_score:
            best_score = score
            best_url = artwork

    return best_url


def _resolve_music(title):
    group, member = (
        _split_music_title(
            title
        )
    )

    # 1순위: 그룹의 실제 앨범 커버
    if group:
        image = _resolve_deezer_album(
            group
        )

        if image:
            return image

        image = _resolve_itunes_album(
            group
        )

        if image:
            return image

    # 2순위: 멤버의 실제 솔로 앨범 커버
    if member:
        image = _resolve_deezer_album(
            member
        )

        if image:
            return image

        image = _resolve_itunes_album(
            member
        )

        if image:
            return image

    # 3순위: 전체 제목으로 마지막 재시도
    image = _resolve_deezer_album(
        title
    )

    if image:
        return image

    image = _resolve_itunes_album(
        title
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
        label = "ALBUM"
        symbol = "♪"
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
