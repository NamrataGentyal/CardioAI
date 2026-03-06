from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import numpy as np
import pickle
import json
import os
import re

app = Flask(__name__)
app.secret_key = 'cardioai_mysql_v2_2026_zQ5nJ8wX'   # changed → clears all old sessions

# ── MySQL connection ─────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',          # change if your MySQL user is different
    'password': 'Namrata@23', # ← replace with your MySQL root password
    'database': 'cardioai',
}

def get_db():
    """Return a new MySQL connection."""
    return mysql.connector.connect(**DB_CONFIG)

# ── Load model artifacts ────────────────────────────────────────────────────
model  = pickle.load(open("model.pkl",  "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))

stats = {}
if os.path.exists("model_stats.json"):
    with open("model_stats.json") as f:
        stats = json.load(f)

FEATURE_NAMES = [
    'age', 'anaemia', 'creatinine_phosphokinase', 'diabetes',
    'ejection_fraction', 'high_blood_pressure', 'platelets',
    'serum_creatinine', 'serum_sodium', 'sex', 'smoking', 'time'
]

FEATURE_RANGES = {
    'age':                       (1,   120),
    'anaemia':                   (0,   1),
    'creatinine_phosphokinase':  (1,   8000),
    'diabetes':                  (0,   1),
    'ejection_fraction':         (1,   100),
    'high_blood_pressure':       (0,   1),
    'platelets':                 (1,   900000),
    'serum_creatinine':          (0.1, 20),
    'serum_sodium':              (100, 150),
    'sex':                       (0,   1),
    'smoking':                   (0,   1),
    'time':                      (1,   365),
}


def validate_input(data: dict):
    """Return (values_list, error_message). error_message is None on success."""
    values = []
    for feat in FEATURE_NAMES:
        raw = data.get(feat, '').strip()
        if raw == '':
            return None, f"Missing value for '{feat}'."
        try:
            val = float(raw)
        except ValueError:
            return None, f"Invalid number for '{feat}': {raw!r}"
        lo, hi = FEATURE_RANGES[feat]
        if not (lo <= val <= hi):
            return None, f"'{feat}' must be between {lo} and {hi} (got {val})."
        values.append(val)
    return values, None


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template('home.html')


@app.route("/predictor")
def predictor():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    display = session.get('name', session.get('username'))
    return render_template('index.html', stats=stats, username=display)


@app.route("/about")
def about():
    return render_template('about.html')


@app.route("/contact", methods=["GET", "POST"])
def contact():
    success = False
    if request.method == "POST":
        success = True
    return render_template('contact.html', success=success)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get('logged_in'):
        return redirect(url_for('predictor'))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        try:
            conn = get_db()
            cur  = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            cur.close()
            conn.close()
        except mysql.connector.Error as e:
            return render_template('login.html', error=f"Database error: {e}")

        if user and check_password_hash(user['password_hash'], password):
            session['logged_in'] = True
            session['username']  = user['username']
            session['name']      = user['name']
            return redirect(url_for('predictor'))
        error = "Invalid username or password."
    return render_template('login.html', error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get('logged_in'):
        return redirect(url_for('predictor'))
    error   = None
    success = None
    if request.method == "POST":
        name     = request.form.get("name",             "").strip()
        username = request.form.get("username",         "").strip()
        email    = request.form.get("email",            "").strip()
        password = request.form.get("password",         "").strip()
        confirm  = request.form.get("confirm_password", "").strip()

        if not name or not username or not email or not password:
            error = "All fields are required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            error = "Username may only contain letters, numbers, and underscores."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            try:
                conn = get_db()
                cur  = conn.cursor(dictionary=True)

                # Check duplicate username
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    error = "Username already taken. Please choose another."
                else:
                    # Check duplicate email
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        error = "An account with this email already exists."
                    else:
                        hashed = generate_password_hash(password)
                        cur.execute(
                            "INSERT INTO users (name, username, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (name, username, email, hashed)
                        )
                        conn.commit()
                        success = "Account created successfully! You can now log in."
                cur.close()
                conn.close()
            except mysql.connector.Error as e:
                error = f"Database error: {e}"
    return render_template('signup.html', error=error, success=success)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route("/predict", methods=["POST"])
def predict():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    values, error = validate_input(request.form)
    if error:
        display = session.get('name', session.get('username'))
        return render_template('index.html', stats=stats, error=error, username=display)

    arr          = np.array(values).reshape(1, -1)
    arr_scaled   = scaler.transform(arr)
    prediction   = int(model.predict(arr_scaled)[0])
    probability  = float(model.predict_proba(arr_scaled)[0][1])   # P(failure)
    confidence   = round(probability * 100, 1)

    if prediction == 1:
        result       = "Heart Failure Detected"
        result_class = "danger"
        advice       = ("High risk detected. Please consult a cardiologist "
                        "immediately for further evaluation.")
    else:
        result       = "No Heart Failure Detected"
        result_class = "success"
        advice       = ("Low risk detected. Maintain a healthy lifestyle, "
                        "regular check-ups, and follow your doctor's guidance.")

    return render_template(
        'index.html',
        stats        = stats,
        result       = result,
        result_class = result_class,
        confidence   = confidence,
        advice       = advice,
        form_data    = request.form,
        username     = session.get('name', session.get('username')),
    )


@app.route("/api/predict", methods=["POST"])
def api_predict():
    """JSON endpoint for programmatic access."""
    data = request.get_json(force=True) or {}
    values, error = validate_input({k: str(v) for k, v in data.items()})
    if error:
        return jsonify({'status': 'error', 'message': error}), 400

    arr         = np.array(values).reshape(1, -1)
    arr_scaled  = scaler.transform(arr)
    prediction  = int(model.predict(arr_scaled)[0])
    probability = float(model.predict_proba(arr_scaled)[0][1])

    return jsonify({
        'status':      'ok',
        'prediction':  prediction,
        'label':       'Heart Failure' if prediction == 1 else 'No Heart Failure',
        'probability': round(probability, 4),
        'confidence':  f"{probability * 100:.1f}%",
    })


@app.route("/stats")
def model_stats():
    return jsonify(stats)


@app.route("/health")
def health():
    return jsonify({'status': 'healthy', 'model_loaded': model is not None})


if __name__ == '__main__':
    app.run(debug=True, port=3000)
