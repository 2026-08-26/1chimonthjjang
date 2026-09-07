import datetime as dt
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs
from web.briefing_support import monthly_news

class NewsSearchTests(unittest.TestCase):
    def test_alias_or_and_web_fallback(self):
        reply=MagicMock();reply.__enter__.return_value.read.return_value=b'<rss><channel/></rss>'
        with patch('web.briefing_support.urlopen',return_value=reply) as call:
            articles,status,url=monthly_news('전북특별자치도','social',dt.date(2003,12,1))
        q=parse_qs(urlparse(call.call_args.args[0].full_url).query)['q'][0]
        self.assertIn('전라북도',q);self.assertIn(' OR ',q)
        self.assertIn('after:2003-11-30',q)
        self.assertEqual(urlparse(url).hostname,'www.google.com')
        self.assertEqual(articles,[]);self.assertIn('같은 해',status)

    def test_year_expansion_explicit(self):
        reply=MagicMock();reply.__enter__.return_value.read.return_value=b'<rss><channel><item><title>Population</title><link>https://news.google.com/a</link><pubDate>Mon, 10 Feb 2003 00:00:00 GMT</pubDate></item></channel></rss>'
        with patch('web.briefing_support.urlopen',return_value=reply):
            month,_,_=monthly_news('전북특별자치도','social',dt.date(2003,12,1))
            year,status,_=monthly_news('전북특별자치도','social',dt.date(2003,12,1),'year')
        self.assertEqual(month,[]);self.assertEqual(len(year),1);self.assertIn('2003년 전체',status)
