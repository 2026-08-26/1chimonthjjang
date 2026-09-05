from flask import Flask

from web.economy_routes import economy_bp
from web.social_routes import social_bp


app = Flask(
    __name__,
    template_folder="templates"
)

app.register_blueprint(
    economy_bp
)

app.register_blueprint(
    social_bp
)


if __name__ == "__main__":
    app.run(
        debug=True,
        port=5001
    )