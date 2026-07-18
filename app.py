import os
import json
import smtplib
import uuid
from email.mime.text import MIMEText
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import database as db
from analyzer import analyze_report_image

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_report_context(result, report_id, saved, created_at=None):
    """Turn the analyzer's structured dict into everything report.html needs,
    including counts for the summary pie chart."""
    items = result.get("items", [])
    counts = {"normal": 0, "high": 0, "low": 0}
    for item in items:
        counts[item.get("status", "normal")] = counts.get(item.get("status", "normal"), 0) + 1

    return {
        "raw_fallback": result.get("raw_fallback"),
        "title": result.get("title", ""),
        "summary": result.get("summary", ""),
        "items": items,
        "tips": result.get("tips", []),
        "disclaimer": result.get("disclaimer", ""),
        "counts": counts,
        "report_id": report_id,
        "saved": saved,
        "created_at": created_at,
    }


def login_required_or_guest(f):
    """Allows both logged-in users and guests to access a route."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session and not session.get("guest"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if "user_id" in session or session.get("guest"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/guest")
def guest():
    session.clear()
    session["guest"] = True
    session["guest_id"] = str(uuid.uuid4())
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("الرجاء تعبئة جميع الحقول", "error")
            return render_template("register.html")

        if db.get_user_by_email(email):
            flash("هذا البريد الإلكتروني مسجل مسبقًا", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        user_id = db.create_user(name, email, password_hash)

        session.clear()
        session["user_id"] = user_id
        session["user_name"] = name
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = db.get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("البريد الإلكتروني أو كلمة المرور غير صحيحة", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required_or_guest
def dashboard():
    reports = []
    if "user_id" in session:
        reports = db.get_reports_for_user(session["user_id"])
    return render_template(
        "dashboard.html",
        is_guest=session.get("guest", False),
        user_name=session.get("user_name"),
        reports=reports,
    )


@app.route("/upload", methods=["POST"])
@login_required_or_guest
def upload():
    file = request.files.get("report_image")

    if not file or file.filename == "":
        flash("الرجاء اختيار صورة للتقرير", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("صيغة الملف غير مدعومة. استخدم JPG أو PNG أو WEBP", "error")
        return redirect(url_for("dashboard"))

    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        result = analyze_report_image(filepath)
    except Exception as exc:
        flash(f"حدث خطأ أثناء تحليل الصورة: {exc}", "error")
        return redirect(url_for("dashboard"))

    if result.get("error"):
        flash(result["error"], "error")
        return redirect(url_for("dashboard"))

    analysis_json = json.dumps(result, ensure_ascii=False)

    report_id = None
    if "user_id" in session:
        report_id = db.save_report(
            session["user_id"], filename, result.get("title", ""), "", analysis_json
        )

    return render_template(
        "report.html",
        **build_report_context(result, report_id, "user_id" in session),
    )


@app.route("/history")
def history():
    if "user_id" not in session:
        flash("سجّل الدخول لعرض سجلّك الطبي المحفوظ", "error")
        return redirect(url_for("login"))
    reports = db.get_reports_for_user(session["user_id"])
    return render_template("history.html", reports=reports)


@app.route("/report/<int:report_id>")
def view_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    report = db.get_report_by_id(report_id, session["user_id"])
    if report is None:
        flash("لم يتم العثور على هذا التقرير", "error")
        return redirect(url_for("history"))
    try:
        result = json.loads(report["analysis"])
    except (json.JSONDecodeError, TypeError):
        result = {"raw_fallback": report["analysis"]}

    return render_template(
        "report.html",
        **build_report_context(result, report["id"], True, report["created_at"]),
    )


@app.route("/report/<int:report_id>/email", methods=["POST"])
def email_report(report_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    report = db.get_report_by_id(report_id, session["user_id"])
    if report is None:
        flash("لم يتم العثور على هذا التقرير", "error")
        return redirect(url_for("history"))

    to_email = request.form.get("email", "").strip()
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")

    if not smtp_user or not smtp_pass:
        flash("إرسال البريد غير مُفعّل بعد. أضف SMTP_USER و SMTP_PASS في ملف .env", "error")
        return redirect(url_for("view_report", report_id=report_id))

    try:
        result = json.loads(report["analysis"])
        lines = [result.get("summary", ""), ""]
        for item in result.get("items", []):
            status_ar = {"normal": "طبيعي", "high": "مرتفع", "low": "منخفض"}.get(
                item.get("status"), ""
            )
            lines.append(
                f"- {item.get('name', '')}: {item.get('value', '')} {item.get('unit', '')} "
                f"({status_ar}) — {item.get('explanation', '')}"
            )
        if result.get("tips"):
            lines.append("")
            lines.append("نصائح:")
            for tip in result["tips"]:
                lines.append(f"- {tip}")
        if result.get("disclaimer"):
            lines.append("")
            lines.append(result["disclaimer"])
        email_body = "\n".join(lines)
    except (json.JSONDecodeError, TypeError):
        email_body = report["analysis"]

    try:
        msg = MIMEText(email_body, "plain", "utf-8")
        msg["Subject"] = "تحليل تقريرك الطبي - SmartLab"
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        flash("تم إرسال التحليل عبر البريد الإلكتروني بنجاح", "success")
    except Exception as exc:
        flash(f"تعذّر إرسال البريد: {exc}", "error")

    return redirect(url_for("view_report", report_id=report_id))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
