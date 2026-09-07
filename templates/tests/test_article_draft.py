import json
import os
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from web.social_routes import social_bp, load_social_signals
from web.economy_routes import economy_bp, load_economy_signals
from web.article_draft import generate_draft

class DraftTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'OPENAI_API_KEY':''});self.env.start();self.addCleanup(self.env.stop)
        self.app=Flask(__name__,template_folder='../templates');self.app.secret_key='test-only'
        self.app.register_blueprint(social_bp);self.app.register_blueprint(economy_bp);self.client=self.app.test_client()
        self.article=dict(title='주택 거래 변화',publisher='테스트',date='2022-12-01',url='https://news.google.com/a')
        self.context=dict(title='변화',region='서울',period='2022년 12월',metrics=[dict(label='거래량',value='10건')],articles=[self.article])

    def test_initial_selected_removed_and_tampered(self):
        for category,loader in [('social',load_social_signals),('economy',load_economy_signals)]:
            row=loader().iloc[0]
            with patch('web.briefing_support.monthly_news',return_value=([self.article],'ok','https://news.google.com/')):
                report=self.client.post(f'/api/{category}-report/{row.signal_type}',json={'include_news':True}).json
            self.assertEqual(report['draft']['sources'],[])
            token=report['draft_token'];endpoint=f'/api/{category}-draft'
            rewritten=self.client.post(endpoint,json={'draft_token':token,'selected_articles':[0]}).json['draft']
            self.assertNotEqual(rewritten['paragraphs'],report['draft']['paragraphs'])
            self.assertIn('[1]',''.join(rewritten['paragraphs']))
            self.assertEqual(rewritten['sources'][0]['url'],self.article['url'])
            removed=self.client.post(endpoint,json={'draft_token':token,'selected_articles':[]}).json['draft']
            self.assertEqual(removed['sources'],[])
            self.assertEqual(removed['paragraphs'],report['draft']['paragraphs'])
            for selection in ([8],[-1],[True],[0,0],'0'):
                self.assertEqual(self.client.post(endpoint,json={'draft_token':token,'selected_articles':selection}).status_code,400)
            self.assertEqual(self.client.post(endpoint,json={'draft_token':token+'x'}).status_code,400)
            self.assertEqual(self.client.post(endpoint,json=[]).status_code,400)
            with patch('time.time',return_value=9999999999):
                self.assertEqual(self.client.post(endpoint,json={'draft_token':token}).status_code,400)

    def test_article_combinations_change_draft(self):
        other=dict(self.article,title='인구 이동 변화',url='https://news.google.com/b')
        first=generate_draft(self.context,[self.article])
        second=generate_draft(self.context,[other])
        both=generate_draft(self.context,[self.article,other])
        self.assertNotEqual(first['paragraphs'],second['paragraphs'])
        self.assertNotEqual(first['paragraphs'],both['paragraphs'])
        self.assertEqual(len(both['sources']),2)
        self.assertIn('[2]',''.join(both['paragraphs']))

    def test_ai_response_and_fallback(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'title':'AI 초안','paragraphs':['거래량은 10건이다.','관련 보도 제목도 확인됐다.[1]']})}}]}).encode()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('web.article_draft.urlopen',return_value=response) as call:
            draft=generate_draft(self.context,[self.article]);self.assertEqual(draft['mode'],'ai')
            payload=json.loads(call.call_args.args[0].data)
            self.assertIn('주택 거래 변화',payload['messages'][1]['content'])
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder'}),patch('web.article_draft.urlopen',side_effect=TimeoutError):
            draft=generate_draft(self.context,[self.article]);self.assertEqual(draft['mode'],'template');self.assertIn('실패',draft['status'])

if __name__=='__main__':unittest.main()
