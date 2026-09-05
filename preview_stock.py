"""Standalone preview; production application connects stock_bp in total.py."""
from flask import Flask, redirect
from web.stock_routes import stock_bp
app=Flask(__name__)
app.register_blueprint(stock_bp)
@app.route('/')
def home(): return redirect('/stock')
if __name__=='__main__': app.run(port=5002,debug=False)
