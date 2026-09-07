import unittest
import pandas as pd
from flask import Flask
from web.dashboard_data import ROOT, load_dashboard
from web.dashboard_routes import dashboard_bp

class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_dashboard()
        cls.app=Flask(__name__,template_folder=str(ROOT/'templates'))
        cls.app.register_blueprint(dashboard_bp)

    def test_signal_accounting_and_no_demo_in_observed_total(self):
        paths=['result/all_social_signals.csv','result/all_economy_signals.csv','result/stock/all_stock_signals.csv','data/processed/temp_signal.csv','data/processed/humidity_signal.csv','data/processed/rain_signal.csv']
        expected=sum(len(pd.read_csv(ROOT/p)) for p in paths)
        self.assertEqual(self.data['overview']['total'],expected)
        self.assertEqual(sum(self.data['overview']['levels'].values()),expected)
        self.assertEqual(self.data['overview']['levels']['미분류'],len(pd.read_csv(ROOT/paths[2])))
        self.assertEqual(sum(self.data['content']['levels'].values()),self.data['content']['rows'])

    def test_national_not_double_counted(self):
        df=pd.read_csv(ROOT/'data/processed/social_monthly.csv')
        expected=df[df.Region_ko=='전국'].sort_values('Date')
        self.assertEqual(len(self.data['social']['national']),len(expected))
        self.assertAlmostEqual(sum(r['Birth'] for r in self.data['social']['national']),expected.Birth.sum())
        self.assertTrue(all(r['Region_ko']!='전국' for r in self.data['social']['latest']))

    def test_stock_latest_and_ranking_universe(self):
        df=pd.read_csv(ROOT/'result/stock/all_stock_signals.csv')
        latest=df[df.date==df.date.max()]
        self.assertEqual(self.data['stock']['latest_count'],len(latest))
        self.assertAlmostEqual(max(r['volume_ratio'] for r in self.data['stock']['data']),latest.volume_ratio.max(),places=8)

    def test_batting_metric_and_rain_denominator(self):
        df=pd.read_csv(ROOT/'data/processed/baseball_weather_2019.csv')
        df=df[df.AB>0].copy();df=df[df.groupby('player_name').AB.transform('sum')>=100]
        self.assertEqual(len(df),self.data['baseball']['eligible'])
        for r in self.data['baseball']['rain']:
            part=df[(df.rainfall>0) if r['rain_group']=='비' else (df.rainfall<=0)]
            self.assertAlmostEqual(r['avg'],part.H.sum()/part.AB.sum(),places=8)

    def test_sources_and_unknown_route(self):
        for s in self.data['sources']:
            self.assertTrue((ROOT/s['file']).is_file())
            try: df=pd.read_csv(ROOT/s['file'])
            except UnicodeDecodeError: df=pd.read_csv(ROOT/s['file'],encoding='cp949')
            self.assertEqual(s['rows'],len(df))
        client=self.app.test_client()
        for path in ['overview','social','economy','stock','baseball','content','signals','sources']:
            self.assertEqual(client.get('/api/dashboard/'+path).status_code,200)
        self.assertEqual(client.get('/api/dashboard/missing').status_code,404)

if __name__=='__main__':unittest.main()
