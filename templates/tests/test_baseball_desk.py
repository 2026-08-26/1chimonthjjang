import unittest
from unittest.mock import patch
from flask import Flask
from web.baseball_desk import baseball_desk_bp,parse_profile

class BaseballTests(unittest.TestCase):
 def setUp(self):
  self.app=Flask(__name__);self.app.register_blueprint(baseball_desk_bp);self.c=self.app.test_client()
 def test_selection_and_draft(self):
  with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
   for kind,group in [('temp','추움'),('humidity','보통')]:
    from web.baseball_desk import signals
    item=signals().query('kind == @kind').iloc[0]
    r=self.c.post('/api/baseball-desk-report',json=dict(name=item.player_name,kind=kind,group=item.weather_group));self.assertEqual(r.status_code,200)
    self.assertEqual(r.json['selection']['name'],item.player_name);self.assertEqual(len(r.json['metrics']),6)
    d=self.c.post('/api/baseball-desk-draft',json={'draft_token':r.json['draft_token'],'selected_articles':[]});self.assertEqual(d.status_code,200)
    self.assertIn(item.player_name,d.json['draft']['title'])
   self.assertEqual(self.c.post('/api/baseball-desk-report',json={'name':'없는선수','kind':'temp','group':'추움'}).status_code,404)
 def test_profile_failure_and_identity(self):
  with patch('web.baseball_desk.urlopen',side_effect=TimeoutError):
   r=self.c.get('/api/baseball-player?name=이창진');self.assertEqual(r.status_code,200);self.assertEqual(r.json['team'],'기아');self.assertEqual(r.json['photo'],'')
  markup='<span id="a_lblName">이창진</span><span id="a_lblPosition">외야수</span><img id="a_imgProgile" src="https://www.koreabaseball.com/photo.jpg">'
  self.assertEqual(parse_profile(markup,'이창진')['position'],'외야수');self.assertEqual(parse_profile(markup,'다른선수'),{})
