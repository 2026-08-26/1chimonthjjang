from web.article_draft import attach_draft
"""Structured signal facts and optional, date-matched news headlines."""
import datetime as dt
import math
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


def metric(row, label, key, unit, digits=0, signed=False):
    try:
        number = float(row[key])
        if not math.isfinite(number):
            raise ValueError('Missing value')
        value = format(number, ('+' if signed else '') + f',.{digits}f') + unit
        direction = ('up' if number > 0 else 'down' if number < 0 else '') if signed else ''
    except (KeyError, TypeError, ValueError):
        value, direction = '자료 없음', ''
    return dict(label=label, value=value, direction=direction)


def news_query(region, category):
    aliases = {'전북특별자치도': '(전북 OR 전라북도 OR 전북특별자치도)',
               '강원특별자치도': '(강원 OR 강원도 OR 강원특별자치도)',
               '제주특별자치도': '(제주 OR 제주도 OR 제주특별자치도)'}
    place = aliases.get(region, region)
    subject = '(주택 OR 아파트 OR 거래 OR 금리)' if category == 'economy' else '(인구 OR 전입 OR 전출 OR 순이동)'
    return f'{place} {subject}'


def monthly_news(region, category, date, scope='month'):
    start = date.replace(day=1)
    end = (start + dt.timedelta(days=32)).replace(day=1)
    if scope == 'year':
        start, end = dt.date(date.year, 1, 1), dt.date(date.year + 1, 1, 1)
    query = f'{news_query(region, category)} after:{(start - dt.timedelta(days=1)).isoformat()} before:{end.isoformat()}'
    params = urlencode({'q': query, 'hl': 'ko', 'gl': 'KR', 'ceid': 'KR:ko'})
    search_url = 'https://www.google.com/search?' + urlencode({'q': query, 'hl': 'ko'})
    period = f'{date.year}년 전체' if scope == 'year' else f'{start:%Y년 %m월}'
    try:
        req = Request('https://news.google.com/rss/search?' + params, headers={'User-Agent': 'DATA-TIP-OFF/1.0'})
        with urlopen(req, timeout=8) as response:
            body = response.read(1_000_001)
        if len(body) > 1_000_000:
            raise ValueError('Response too large')
        articles, seen = [], set()
        for entry in ET.fromstring(body).findall('./channel/item'):
            title, url = entry.findtext('title', '').strip(), entry.findtext('link', '').strip()
            try:
                published = parsedate_to_datetime(entry.findtext('pubDate', '')).astimezone(dt.timezone(dt.timedelta(hours=9))).date()
            except (ValueError, TypeError, OverflowError):
                continue
            if not title or not start <= published < end or url in seen:
                continue
            if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'news.google.com':
                continue
            seen.add(url)
            articles.append(dict(title=title, url=url, date=published.isoformat(), publisher=entry.findtext('source', '')))
        articles.sort(key=lambda a: a['date'], reverse=True)
        status = f'{period} 관련 보도입니다. 제목과 출처를 확인한 뒤 추가할 기사를 선택해주세요.' if articles else f'{period} 관련 보도를 찾지 못했습니다. 검색 서비스에 오래된 보도가 없을 수 있습니다. 검색 범위를 같은 해로 넓히거나 일반 웹 검색을 이용해주세요.'
        return articles[:8], status, search_url
    except Exception:
        return [], '기사 조회에 실패했습니다. 데이터 브리핑은 생성되었습니다. 잠시 후 다시 시도해주세요.', search_url


def briefing_extras(row, category, payload=None):
    if category == 'social':
        fields = [('자연증가', 'Natural_growth', '명', 0, False), ('자연증가 변화 · 전년 동월 대비', 'Natural_growth_change', '명', 0, True), ('순이동', 'Net_migration', '명', 0, False), ('순이동 변화 · 전년 동월 대비', 'Net_migration_change', '명', 0, True)]
        region = str(row['Region_ko'])
    else:
        fields = [('주택가격 변화 · 전년 동월 대비', 'Price_yoy_pct', '%', 1, True), ('거래량 변화 · 전년 동월 대비', 'Transaction_yoy_pct', '%', 1, True), ('거래 건수', 'Transaction_count', '건', 0, False), ('기준금리', 'Base_rate', '%', 2, False), ('기준금리 변화', 'Base_rate_change', '%p', 2, True)]
        region = str(row['Region'])
    result = dict(metrics=[metric(row, *field) for field in fields], region=region, period=row['Date'].strftime('%Y년 %m월'), articles=[], news_status='관련 기사 추가 여부를 선택하고 브리핑을 생성해주세요.', news_search_url=None)
    if isinstance(payload, dict) and payload.get('include_news') is True:
        scope = 'year' if payload.get('news_scope') == 'year' else 'month'
        articles, status, url = monthly_news(region, category, row['Date'].date(), scope) if scope == 'year' else monthly_news(region, category, row['Date'].date())
        result['news_scope'] = scope
        result.update(articles=articles, news_status=status, news_search_url=url)
    return attach_draft(result, row["signal_name"])
