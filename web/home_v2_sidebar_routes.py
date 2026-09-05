from flask import Blueprint, render_template

from web.home_routes import load_dashboard_data


home_v2_sidebar_bp = Blueprint(
    "home_v2_sidebar",
    __name__
)


@home_v2_sidebar_bp.route("/home-v2-sidebar")
def home_v2_sidebar():

    (
        stats,
        top_signals,
        monthly_chart,
        rule_chart
    ) = load_dashboard_data()

    return render_template(
        "home/home_index_v2_sidebar.html",
        stats=stats,
        top_signals=top_signals,
        monthly_chart=monthly_chart,
        rule_chart=rule_chart
    )