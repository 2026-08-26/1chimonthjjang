from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data


home_v4_bp = Blueprint(
    "home_v4",
    __name__
)


@home_v4_bp.route("/home-v4")
def home_v4():

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    ) = load_dashboard_data()

    return render_template(
        "home/home_index_v4.html",
        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart
    )