import os
from flask import Flask, request
from config.database import create_tables

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.chat import chat_bp
from routes.task import task_bp
from routes.data import data_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

create_tables()

@app.after_request
def add_no_cache_headers(response):
    if request.path in ["/agent", "/login-page", "/", "/signup"] or request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(task_bp)
app.register_blueprint(data_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
