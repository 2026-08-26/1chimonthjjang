"""Dashboard-only preview; full integration is in total.py and total_team.py."""
from flask import Flask
from web.dashboard_routes import dashboard_bp
app=Flask(__name__)
app.register_blueprint(dashboard_bp)
if __name__=='__main__': app.run(host='127.0.0.1',port=5091,debug=False)
