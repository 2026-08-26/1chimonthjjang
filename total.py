import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/baseball")
def baseball():

    # 분석 결과 CSV 불러오기
    temp = pd.read_csv("data/processed/temp_signal.csv")
    humidity = pd.read_csv("data/processed/humidity_signal.csv")
    rain = pd.read_csv("data/processed/rain_signal.csv")

    # 이상 신호가 강한 순서
    temp["signal_strength"] = temp["signal_score"].abs()
    humidity["signal_strength"] = humidity["signal_score"].abs()
    rain["signal_strength"] = rain["signal_score"].abs()

    # TOP 10
    temp_top = (
        temp.sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    humidity_top = (
        humidity.sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    # 비 오는 날만
    rain_top = (
        rain[rain["rain_group"] == "비"]
        .sort_values("signal_strength", ascending=False)
        .head(10)
        .to_dict("records")
    )

    return render_template(
        "baseball.html",
        temp_top=temp_top,
        humidity_top=humidity_top,
        rain_top=rain_top
    )

if __name__ == "__main__":
    app.run(debug=True)

    