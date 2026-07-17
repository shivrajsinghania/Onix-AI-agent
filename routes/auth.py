import re
from flask import Blueprint, request, jsonify, render_template, redirect, session
from werkzeug.security import generate_password_hash
from routes.utils import normalize_gmail_email, add_user, validate_user, get_connection

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def welcome():
    if "user" in session:
        return redirect("/agent")
    return render_template("landing_page_onix.html")

@auth_bp.route("/signup")
def signup():
    if "user" in session:
        return redirect("/agent")
    return render_template("signup_onix.html")

@auth_bp.route("/check-username")
def check_username():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"available": False, "message": "Enter a username"})

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username=%s", (username,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()

    return jsonify({
        "available": not exists,
        "message": "Available" if not exists else "Already taken"
    })

@auth_bp.route("/submit", methods=["POST"])
def submit():
    email_local = request.form.get("email", "").strip().lower()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    errors = {}

    if not email_local:
        errors["email"] = "Enter the part before @gmail.com."
    elif not re.fullmatch(r"[a-zA-Z0-9._%+-]+", email_local):
        errors["email"] = "Use only letters, numbers, dots, underscores, and -."
    email = normalize_gmail_email(email_local)

    if not username:
        errors["username"] = "Create a username."
    elif len(username) < 3:
        errors["username"] = "Username must be at least 3 characters."
    elif not re.fullmatch(r"[a-zA-Z0-9._]+", username):
        errors["username"] = "Use only letters, numbers, dots, and underscores."

    if len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."
    else:
        has_letter = any(ch.isalpha() for ch in password)
        has_number = any(ch.isdigit() for ch in password)
        if not (has_letter and has_number):
            errors["password"] = "Use letters and at least one number."
    if password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."

    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    hashed_password = generate_password_hash(password)
    result = add_user(email, username, hashed_password)

    if result == "success":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        session["user"] = username
        session["user_id"] = user[0]
        return jsonify({"ok": True, "redirect": "/agent"})

    return jsonify({"ok": False, "errors": {"username": "Username already exists."}}), 400

@auth_bp.route("/login-page")
def loginpage():
    if "user" in session:
        return redirect("/agent")
    return render_template("login_onix.html")

@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    errors = {}
    
    if not username:
        errors["username"] = "Enter your username."
    if not password:
        errors["password"] = "Enter your password."
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400

    if validate_user(username, password):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        session["user"] = username
        session["user_id"] = user[0]
        return jsonify({"ok": True, "redirect": "/agent"})

    return jsonify({"ok": False, "errors": {"password": "Invalid username or password."}}), 400
    
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@auth_bp.route("/check-session")
def check_session():
    if "user" in session:
        return jsonify({"logged_in": True})
    return jsonify({"logged_in": False})
