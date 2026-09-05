from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data


home_v2_nav_bp = Blueprint(
    "home_v2_nav",
    __name__
)


@home_v2_nav_bp.route("/home-v2-nav")
def home_v2_nav():

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    ) = load_dashboard_data()

    return render_template(
        "home/home_index_v2_nav.html",
        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart
    )