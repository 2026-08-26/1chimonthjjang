from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data


home_v3_bp = Blueprint(
    "home_v3",
    __name__
)


@home_v3_bp.route("/home-v3")
def home_v3():

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    ) = load_dashboard_data()

    return render_template(
        "home/home_index_v3.html",
        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart
    )