from flask import Blueprint, render_template, jsonify, abort
from web.dashboard_data import load_dashboard

dashboard_bp=Blueprint('dashboard',__name__)

@dashboard_bp.get('/dashboard')
def dashboard():
    return render_template('dashboard/index.html')

@dashboard_bp.get('/api/dashboard/<section>')
def dashboard_api(section):
    if section not in ['all','overview','social','economy','stock','baseball','content','signals','sources']: abort(404)
    data=load_dashboard()
    return jsonify(data if section=='all' else data[section])
