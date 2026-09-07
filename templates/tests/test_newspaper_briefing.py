import datetime as dt
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from web.social_routes import social_bp, load_social_signals
from web.economy_routes import economy_bp, load_economy_signals
from web.briefing_support import monthly_news, metric

class BriefingTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__,template_folder='../templates')
        self.app.register_blueprint(social_bp)
        self.app.register_blueprint(economy_bp)
        self.client=self.app.test_client()

    def test_categories_and_opt_in(self):
        for category, loader in [('social',load_social_signals),('economy',load_economy_signals)]:
            row=loader().iloc[0]
            path=f'/api/{category}-report/{row.signal_type}'
            with patch('web.briefing_support.monthly_news',return_value=([{'title':'Test','url':'https://news.google.com/test'}],'ok','https://news.google.com/search')) as news:
                r=self.client.post(path,json={'include_news':False})
                self.assertEqual(r.status_code,200)
                self.assertGreaterEqual(len(r.json['metrics']),4)
                news.assert_not_called()
                r=self.client.post(path,json={'include_news':True})
                self.assertEqual(len(r.json['articles']),1)
                news.assert_called_once()
            page=self.client.get(f'/{category}/detail/{row.signal_type}')
            self.assertEqual(page.status_code,200)
            with open(f'/tmp/newspaper-{category}.html','w') as f:f.write(page.text)
            with open(f'/tmp/newspaper-{category}.json','w') as f:
                import json
                json.dump(self.client.post(path,json={}).json,f)
            self.assertEqual(self.client.post(f'/api/{category}-report/missing',json={}).status_code,404)

    def test_missing_and_zero(self):
        self.assertEqual(metric({'x':float('nan')},'x','x','명')['value'],'자료 없음')
        self.assertEqual(metric({'x':0},'x','x','명')['value'],'0명')

    def test_news_date_filter_and_failure(self):
        xml=b'<rss><channel><item><title>Valid</title><link>https://news.google.com/a</link><pubDate>Tue, 15 Sep 2020 03:00:00 GMT</pubDate></item><item><title>Old</title><link>https://news.google.com/b</link><pubDate>Sat, 15 Aug 2020 03:00:00 GMT</pubDate></item><item><title>Bad</title><link>javascript:alert(1)</link><pubDate>Tue, 15 Sep 2020 03:00:00 GMT</pubDate></item></channel></rss>'
        response=MagicMock();response.__enter__.return_value.read.return_value=xml
        with patch('web.briefing_support.urlopen',return_value=response):
            articles,_,_=monthly_news('서울','social',dt.date(2020,9,1))
            self.assertEqual([a['title'] for a in articles],['Valid'])
        with patch('web.briefing_support.urlopen',side_effect=TimeoutError):
            articles,status,_=monthly_news('서울','economy',dt.date(2020,9,1))
            self.assertEqual(articles,[])
            self.assertIn('실패',status)

if __name__=='__main__':unittest.main()
