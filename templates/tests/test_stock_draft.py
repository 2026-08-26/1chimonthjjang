import json
import os
import unittest
from unittest.mock import patch
from flask import Flask
from web.stock_routes import stock_bp

class StockDraftTests(unittest.TestCase):
 def setUp(self):
  self.app=Flask(__name__,template_folder='../templates',static_folder='../static');self.app.register_blueprint(stock_bp);self.client=self.app.test_client()
  self.env=patch.dict(os.environ,{'OPENAI_API_KEY':''});self.env.start();self.addCleanup(self.env.stop)
 def test_news_draft_selection_and_removal(self):
  articles=[dict(title='피노 실적 발표',url='https://news.google.com/a',publisher='테스트1',date='2026-09-03'),dict(title='피노 신규 계약',url='https://news.google.com/b',publisher='테스트2',date='2026-09-02')]
  path='/api/stock-report/KOSDAQ/033790/2026-09-04'
  with patch('stock_ai_agent.related_news',return_value=(articles,'선택해주세요','https://news.google.com/search')) as news:
   initial=self.client.post(path,json={'include_news':False});self.assertEqual(initial.status_code,200);news.assert_not_called()
   self.assertEqual(initial.json['draft']['sources'],[])
   report=self.client.post(path,json={'include_news':True});self.assertEqual(report.status_code,200);news.assert_called_once()
  token=report.json['draft_token'];drafts=[]
  for selected in ([0],[1],[0,1],[]):
   r=self.client.post('/api/stock-draft',json={'draft_token':token,'selected_articles':selected});self.assertEqual(r.status_code,200)
   self.assertEqual(len(r.json['draft']['sources']),len(selected));drafts.append(r.json['draft']['paragraphs'])
  self.assertNotEqual(drafts[0],drafts[1]);self.assertNotEqual(drafts[1],drafts[2]);self.assertEqual(drafts[3],initial.json['draft']['paragraphs'])
  self.assertEqual(self.client.post('/api/stock-draft',json={'draft_token':token+'x','selected_articles':[0]}).status_code,400)
  with open('/tmp/stock-draft-report.json','w') as f:json.dump(report.json,f)
 def test_pages(self):
  for path,file in [('/stock','/tmp/stock-index-new.html'),('/stock/KOSDAQ/033790/2026-09-04','/tmp/stock-detail-new.html')]:
   r=self.client.get(path);self.assertEqual(r.status_code,200)
   self.assertNotIn('>전체 대시보드</a>',r.text)
   with open(file,'w') as f:f.write(r.text)
  from web.stock_routes import read_signals
  for value,css in [(3.2,'is-up'),(-3.2,'is-down'),(0,'is-flat')]:
   frame=read_signals().head(1).copy();frame['return5']=value
   with patch('web.stock_routes.read_signals',return_value=frame):
    page=self.client.get('/stock').text;self.assertIn('stock-change '+css,page)
