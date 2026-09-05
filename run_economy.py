from flask import Flask

from web.economy_routes import economy_bp
from web.social_routes import social_bp

from web.home_routes import home_bp
from web.home_v2_routes import home_v2_bp
from web.home_v3_routes import home_v3_bp
from web.home_v4_routes import home_v4_bp
from web.home_v2_sidebar_routes import home_v2_sidebar_bp


app = Flask(
    __name__,
    template_folder="templates"
)


app.register_blueprint(home_bp)
app.register_blueprint(home_v2_bp)
app.register_blueprint(home_v3_bp)
app.register_blueprint(home_v4_bp)
app.register_blueprint(home_v2_sidebar_bp)

app.register_blueprint(economy_bp)
app.register_blueprint(social_bp)


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )