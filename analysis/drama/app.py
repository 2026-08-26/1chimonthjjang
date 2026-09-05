from flask import Flask, render_template
import pandas as pd
import os

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# 공통 데이터 로드 함수
def load_trend_data():
    csv_path = os.path.join('data', 'trend_data.csv')
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path)
    return pd.DataFrame()

# 1. 전체 보기 (All)
@app.route('/trend')
@app.route('/trend/all')
def trend_all():
    df = load_trend_data()
    items = df.to_dict(orient='records') if not df.empty else []
    return render_template('trend/trend_index.html', items=items, active_tab='all')

# 2. 뮤직 카테고리
@app.route('/trend/music')
def trend_music():
    df = load_trend_data()
    if not df.empty and 'category' in df.columns:
        filtered = df[df['category'].astype(str).str.lower() == 'music']
        items = filtered.to_dict(orient='records')
    else:
        items = []
    return render_template('trend/trend_index.html', items=items, active_tab='music')

# 3. 드라마 카테고리
@app.route('/trend/drama')
def trend_drama():
    df = load_trend_data()
    if not df.empty and 'category' in df.columns:
        filtered = df[df['category'].astype(str).str.lower() == 'drama']
        items = filtered.to_dict(orient='records')
    else:
        items = []
    return render_template('trend/trend_index.html', items=items, active_tab='drama')

# 4. 웹툰 카테고리
@app.route('/trend/webtoon')
def trend_webtoon():
    df = load_trend_data()
    if not df.empty and 'category' in df.columns:
        filtered = df[df['category'].astype(str).str.lower() == 'webtoon']
        items = filtered.to_dict(orient='records')
    else:
        items = []
    return render_template('trend/trend_index.html', items=items, active_tab='webtoon')

if __name__ == '__main__':
    app.run(debug=True, port=5000)