"""Rule-based reporting with optional related news headlines, no paid AI API."""
import datetime as dt
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

def related_news(name, date):
    end = dt.date.fromisoformat(date)
    start = end - dt.timedelta(days=7)
    query = f'"{name}" 주가 after:{start.isoformat()} before:{(end+dt.timedelta(days=1)).isoformat()}'
    params = urlencode({'q':query,'hl':'ko','gl':'KR','ceid':'KR:ko'})
    search_url = 'https://news.google.com/search?' + params
    try:
        req = Request('https://news.google.com/rss/search?'+params,headers={'User-Agent':'DATA-TIP-OFF/1.0'})
        with urlopen(req,timeout=8) as response:
            body=response.read(1_000_001)
        if len(body)>1_000_000: raise ValueError('Response too large')
        root = ET.fromstring(body)
        articles=[]
        for entry in root.findall('./channel/item'):
            title=entry.findtext('title',''); link=entry.findtext('link','')
            published=parsedate_to_datetime(entry.findtext('pubDate','')).astimezone(dt.timezone(dt.timedelta(hours=9))).date()
            if not start<=published<=end or name.casefold() not in title.casefold(): continue
            if urlparse(link).scheme!='https' or urlparse(link).hostname!='news.google.com': continue
            articles.append({'title':title,'url':link,'date':published.isoformat(),'publisher':entry.findtext('source','')})
        articles=sorted(articles,key=lambda x:x['date'],reverse=True)[:5]
        return articles, ('관련 보도 제목을 찾았습니다. 본문과 공시는 검증하지 않았습니다.' if articles else '해당 기간에 일치하는 보도 제목을 찾지 못했습니다. 원인 확인이 필요합니다.'),search_url
    except Exception:
        return [],'뉴스 조회에 실패했습니다. 데이터 브리핑은 제공하며 원인은 미확인으로 표시합니다.',search_url

class StockAIAgent:
    def generate_report(self,item,include_news=False):
        name,date=item['name'],item['date']
        ret=float(item['return5']); ratio=float(item['volume_ratio'])
        direction='상승' if ret>0 else '하락' if ret<0 else '보합'
        report={
            'title':f'{name} 주식 취재 브리핑',
            'briefing':f'{date} 기준 {name}의 종가는 5거래일 전보다 {ret:+.2f}% 변했습니다. 거래량은 이전 20거래일 평균의 {ratio:.2f}배입니다. 이 수치는 가격과 거래의 변화를 보여주며 원인을 입증하지는 않습니다.',
            'facts':[f"종가 {float(item['close']):,.0f}원",f"당일 등락률 {float(item['change']):+.2f}%",f'5거래일 가격 변화 {ret:+.2f}%',f'이전 20거래일 평균 대비 거래량 {ratio:.2f}배',f"시장 거래대금 비중 {float(item['share_pct']):.2f}%"],
            'cause_status':'미확인',
            'cause_summary':f'{name}의 {direction} 배경은 시세 CSV만으로 확인되지 않았습니다.',
            'hypotheses':[],
            'article_ideas':[f'{name}, 5거래일 {ret:+.2f}%…가격 변화를 동반한 재료는 무엇인가',f'{name} 거래량 평소의 {ratio:.2f}배…거래 주체와 공시 시점 추적'],
            'questions':['관련 보도·공시는 가격이 움직이기 전 공개됐나, 움직인 뒤 나온 해설인가?','같은 업종 종목도 함께 움직였나, 이 기업만의 변화인가?','기관·외국인·개인 중 누가 거래를 주도했나?','주식분할·병합·증자·권리락이 가격 비교에 영향을 줬나?'],
            'verification_data':['DART·KIND의 해당 기간 원문 공시','기사 원문과 최초 보도 시각','투자자별 순매수 및 업종 지수','기업행사와 수정주가 자료'],
            'articles':[], 'news_status':'뉴스 조회를 선택하면 기준일 이전 7일~기준일의 관련 보도 제목을 검색합니다.',
            'source_links':[{'title':'DART 공시 확인','url':'https://dart.fss.or.kr/'},{'title':'KIND 공시 확인','url':'https://kind.krx.co.kr/'}],
        }
        if include_news:
            articles,status,url=related_news(name,date)
            report.update(articles=articles,news_status=status)
            report['source_links'].append({'title':'같은 기간 뉴스 검색','url':url})
            categories=[('실적·사업 전망',['실적','흑자','적자','매출','영업이익']),('계약·투자·사업 관련 소식',['수주','계약','투자','인수','합병']),('정책·산업 관련 소식',['정책','정부','규제','지원','반도체','바이오']),('주식 수·자본 관련 소식',['증자','분할','병합','전환사채','자사주'])]
            for label,words in categories:
                matched=[a for a in articles if any(w in a['title'] for w in words)]
                if matched: report['hypotheses'].append({'title':label,'description':'관련 보도 제목에서 발견한 확인 후보입니다. 가격 변동 원인으로 확인된 사실은 아닙니다.','sources':matched})
            if articles: report['cause_summary']='같은 기간의 관련 보도가 검색됐습니다. 아래 기사와 공시의 내용을 확인해야 가격 변동과의 관련성을 판단할 수 있습니다.'
        return report
