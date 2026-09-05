import os
from flask import Flask, render_template, request, jsonify
from anomaly import analyze_trend_data
from ai_agent import generate_ai_briefing # 기존 ai_agent 연동

app = Flask(__name__, template_folder='templates', static_folder='static')

# 예시 데이터 경로
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'kdrama.csv') # 보유한 CSV 경로로 조정 가능

@app.route('/')
def index():
    # 이상 감지 데이터 분석 수행
    signals = analyze_trend_data(DATA_PATH)
    return render_template('trend/trend_index.html', signals=signals)

@app.route('/detail/<signal_id>')
def detail(signal_id):
    signals = analyze_trend_data(DATA_PATH)
    # 선택된 시그널 정보 찾기
    signal = next((s for s in signals if s['id'] == signal_id), signals[0] if signals else {
        'title': 'Move to Heaven', 'category': '드라마',
        'base_avg': 100.5, 'recent_avg': 242.5, 'change_rate': 141.4,
        'z_score': 6.97, 'pulse_score': 99, 'grade': 'HIGH',
        'status_desc': '평소 대비 2.4배 폭증, 긴급 취재 시그널 포착'
    })
    
    # AI 에이전트 브리핑 생성 연동
    ai_briefing = generate_ai_briefing(signal['title']) if 'generate_ai_briefing' in globals() else {
        'headlines': [
            f"'{signal['title']}' 급상승세 포착... 배경과 이유는?",
            f"데이터가 가리킨 화제의 이슈, {signal['title']} 집중 분석"
        ],
        'questions': [
            "최근 지표 급상승을 견인한 주요 타겟층이나 외부 요인이 있는가?",
            "향후 지속 가능성에 대한 내부 전망은 어떠한가?"
        ]
    }
    
    return render_template('trend/trend_detail.html', signal=signal, briefing=ai_briefing)

if __name__ == '__main__':
    app.run(debug=True, port=5000)