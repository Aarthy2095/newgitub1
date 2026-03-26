"""
Digital Lab Record Entry Management System
==========================================
A Flask-based web application to manage student lab entries.

Admin Credentials:
    Username: admin
    Password: admin123

Run Instructions:
    1. pip install flask
    2. python app.py
    3. Open http://127.0.0.1:5000 in your browser
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from datetime import datetime, date
import sqlite3
import csv
import io
import os

# ─── App Configuration ────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "labrecord_secret_key_2024"  # Change in production

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
DATABASE = "database.db"

# ─── Database Helpers ─────────────────────────────────────────────────────────

def get_db():
    """Open a new database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT    NOT NULL,
            reg_no  TEXT    NOT NULL UNIQUE,
            dept    TEXT    NOT NULL
        )
    """)

    # Entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL,
            lab_name    TEXT    NOT NULL DEFAULT 'Computer Lab',
            system_no   TEXT,
            time_in     TEXT    NOT NULL,
            time_out    TEXT,
            date        TEXT    NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)

    # Add system_no column to existing databases (safe migration)
    try:
        cursor.execute("ALTER TABLE entries ADD COLUMN system_no TEXT")
    except Exception:
        pass  # Column already exists — ignore

    conn.commit()
    conn.close()


# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def is_logged_in():
    """Check if admin session is active."""
    return session.get("admin_logged_in") is True


def login_required(f):
    """Decorator to protect admin routes."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_logged_in():
            flash("Please login to access the admin panel.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ─── Public Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Landing page — student entry form."""
    return render_template("index.html")


@app.route("/entry", methods=["POST"])
def student_entry():
    """
    Handle student check-in.
    - If student not inside → mark Time In.
    - If already inside → show warning.
    """
    reg_no    = request.form.get("reg_no", "").strip().upper()
    system_no = request.form.get("system_no", "").strip()
    if not reg_no:
        flash("Please enter a Register Number.", "danger")
        return redirect(url_for("index"))
    if not system_no:
        flash("Please enter a System Number.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    # Look up the student
    student = conn.execute(
        "SELECT * FROM students WHERE reg_no = ?", (reg_no,)
    ).fetchone()

    if not student:
        conn.close()
        flash(f"Register Number '{reg_no}' not found. Please contact admin.", "danger")
        return redirect(url_for("index"))

    # Check if that system is already occupied today
    today = date.today().isoformat()
    sys_busy = conn.execute(
        """SELECT e.id, s.name FROM entries e
           JOIN students s ON e.student_id = s.id
           WHERE e.system_no = ? AND e.date = ? AND e.time_out IS NULL""",
        (system_no, today)
    ).fetchone()

    if sys_busy:
        conn.close()
        flash(f"⚠️ System {system_no} is already occupied by {sys_busy['name']}. Please choose another system.", "warning")
        return redirect(url_for("index"))

    # Check for an open entry (no time_out) for today
    open_entry = conn.execute(
        """SELECT * FROM entries
           WHERE student_id = ? AND date = ? AND time_out IS NULL""",
        (student["id"], today)
    ).fetchone()

    if open_entry:
        conn.close()
        flash(f"⚠️ {student['name']} is already inside the lab on System {open_entry['system_no']}!", "warning")
        return redirect(url_for("index"))

    # Mark Time In with system number
    now = datetime.now().strftime("%H:%M:%S")
    conn.execute(
        "INSERT INTO entries (student_id, lab_name, system_no, time_in, date) VALUES (?, ?, ?, ?, ?)",
        (student["id"], "Computer Lab", system_no, now, today)
    )
    conn.commit()
    conn.close()

    flash(f"✅ Welcome, {student['name']}! Assigned to System {system_no}. Time In: {now}.", "success")
    return redirect(url_for("index"))


@app.route("/exit", methods=["POST"])
def student_exit():
    """
    Handle student check-out.
    Finds the open entry for today and sets time_out.
    """
    reg_no = request.form.get("reg_no", "").strip().upper()
    if not reg_no:
        flash("Please enter a Register Number.", "danger")
        return redirect(url_for("index"))

    conn = get_db()
    student = conn.execute(
        "SELECT * FROM students WHERE reg_no = ?", (reg_no,)
    ).fetchone()

    if not student:
        conn.close()
        flash(f"Register Number '{reg_no}' not found.", "danger")
        return redirect(url_for("index"))

    today = date.today().isoformat()
    open_entry = conn.execute(
        """SELECT * FROM entries
           WHERE student_id = ? AND date = ? AND time_out IS NULL""",
        (student["id"], today)
    ).fetchone()

    if not open_entry:
        conn.close()
        flash(f"No open entry found for {student['name']} today. Please check in first.", "info")
        return redirect(url_for("index"))

    now = datetime.now().strftime("%H:%M:%S")
    conn.execute(
        "UPDATE entries SET time_out = ? WHERE id = ?",
        (now, open_entry["id"])
    )
    conn.commit()
    conn.close()

    flash(f"👋 Goodbye, {student['name']}! Time Out recorded at {now}.", "success")
    return redirect(url_for("index"))


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Admin login page."""
    if is_logged_in():
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    """Clear admin session."""
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    """
    Admin dashboard with:
    - Total entries today
    - Students currently inside
    - Total registered students
    """
    conn = get_db()
    today = date.today().isoformat()

    total_today = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE date = ?", (today,)
    ).fetchone()[0]

    inside_now = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE date = ? AND time_out IS NULL", (today,)
    ).fetchone()[0]

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    # Latest 10 entries for quick view
    recent_entries = conn.execute("""
        SELECT e.id, s.name, s.reg_no, s.dept,
               e.lab_name, e.system_no, e.time_in, e.time_out, e.date
        FROM entries e
        JOIN students s ON e.student_id = s.id
        WHERE e.date = ?
        ORDER BY e.id DESC
        LIMIT 10
    """, (today,)).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_today=total_today,
        inside_now=inside_now,
        total_students=total_students,
        recent_entries=recent_entries,
        today=today
    )


@app.route("/admin/entries")
@login_required
def admin_entries():
    """View all entries with optional date filter."""
    filter_date = request.args.get("filter_date", "")
    conn = get_db()

    if filter_date:
        entries = conn.execute("""
            SELECT e.id, s.name, s.reg_no, s.dept,
                   e.lab_name, e.system_no, e.time_in, e.time_out, e.date
            FROM entries e
            JOIN students s ON e.student_id = s.id
            WHERE e.date = ?
            ORDER BY e.id DESC
        """, (filter_date,)).fetchall()
    else:
        entries = conn.execute("""
            SELECT e.id, s.name, s.reg_no, s.dept,
                   e.lab_name, e.system_no, e.time_in, e.time_out, e.date
            FROM entries e
            JOIN students s ON e.student_id = s.id
            ORDER BY e.id DESC
            LIMIT 200
        """).fetchall()

    conn.close()
    return render_template("admin_entries.html", entries=entries, filter_date=filter_date)


@app.route("/admin/students")
@login_required
def admin_students():
    """View all registered students."""
    conn = get_db()
    # order by registration number to list students numerically
    students = conn.execute(
        "SELECT * FROM students ORDER BY reg_no"
    ).fetchall()
    conn.close()
    return render_template("admin_students.html", students=students)


@app.route("/admin/students/add", methods=["POST"])
@login_required
def admin_add_student():
    """Add a new student to the database."""
    name   = request.form.get("name", "").strip()
    reg_no = request.form.get("reg_no", "").strip().upper()
    dept   = request.form.get("dept", "").strip()

    if not all([name, reg_no, dept]):
        flash("All fields are required.", "danger")
        return redirect(url_for("admin_students"))

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO students (name, reg_no, dept) VALUES (?, ?, ?)",
            (name, reg_no, dept)
        )
        conn.commit()
        flash(f"Student '{name}' added successfully.", "success")
    except sqlite3.IntegrityError:
        flash(f"Register Number '{reg_no}' already exists.", "danger")
    finally:
        conn.close()

    return redirect(url_for("admin_students"))


@app.route("/admin/students/delete/<int:student_id>", methods=["POST"])
@login_required
def admin_delete_student(student_id):
    """Delete a student (and their entries via cascade logic)."""
    conn = get_db()
    student = conn.execute(
        "SELECT name FROM students WHERE id = ?", (student_id,)
    ).fetchone()

    if student:
        # Also delete all entries for this student
        conn.execute("DELETE FROM entries WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        flash(f"Student '{student['name']}' deleted.", "success")
    else:
        flash("Student not found.", "danger")

    conn.close()
    return redirect(url_for("admin_students"))



def calculate_study_year(reg_no: str) -> str:
    """Derive study year from registration number.

    Rule derived from provided examples:
        252603101 -> first year
        242603101 -> second year
        232603101 -> third year
    The first two digits encode a batch code (e.g. 25,24,23).
    We compute year as `26 - batch` so that 25=>1, 24=>2, 23=>3.
    Any result outside 1-3 returns empty.
    """
    try:
        batch = int(reg_no[:2])
        year = 26 - batch
        if year in (1, 2, 3):
            return str(year)
        return ""
    except Exception:
        return ""

def calculate_hour_label(time_str: str) -> str:
    """Return a human label for an hourly period based on time_in string.

    Expected format of time_str is 'HH:MM:SS'.
    Periods:
      09:00-10:00 -> "9:00-10:00 First Hour"
      10:00-11:00 -> "10:00-11:00 Second Hour"
      11:00-12:00 -> "11:00-12:00 Third Hour"
      13:00-14:00 -> "1:00-2:00 Four hour"
      14:00-15:00 -> "2:00-3:00 Fifth Hour"
    Returns empty string if outside defined ranges.
    """
    try:
        h = int(time_str.split(":")[0])
    except Exception:
        return ""
    if 9 <= h < 10:
        return "9:00-10:00 First Hour"
    if 10 <= h < 11:
        return "10:00-11:00 Second Hour"
    if 11 <= h < 12:
        return "11:00-12:00 Third hour"
    if 13 <= h < 14:
        return "1:00-2:00 Four hour"
    if 14 <= h < 15:
        return "2:00-3:00 Fifth Hour"
    return ""


@app.route("/admin/export")
@login_required
def admin_export():
    """Export all entries to CSV files split by study year.

    The original implementation returned a single CSV containing every
    entry.  The requested enhancement is to separate first/second/third
    years (and "other" when the year calculation fails) into distinct
    files.  To keep things tidy we bundle the three CSVs into a ZIP
    archive that the browser can download in one go.
    """
    filter_date = request.args.get("filter_date", "")
    conn = get_db()

    if filter_date:
        rows = conn.execute("""
            SELECT s.name, s.reg_no, s.dept, e.lab_name, e.system_no, e.time_in, e.time_out, e.date
            FROM entries e JOIN students s ON e.student_id = s.id
            WHERE e.date = ?
            ORDER BY e.id DESC
        """, (filter_date,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT s.name, s.reg_no, s.dept, e.lab_name, e.system_no, e.time_in, e.time_out, e.date
            FROM entries e JOIN students s ON e.student_id = s.id
            ORDER BY e.id DESC
        """).fetchall()

    conn.close()

    # augment with study year and hour label, and group by year
    groups = {"1": [], "2": [], "3": [], "": []}
    order = [
        "9:00-10:00 First Hour",
        "10:00-11:00 Second Hour",
        "11:00-12:00 Third hour",
        "1:00-2:00 Four hour",
        "2:00-3:00 Fifth Hour",
        ""  # unknown at end
    ]

    for row in rows:
        name, reg_no, dept, lab, system_no, time_in, time_out, dateval = row
        study_year = calculate_study_year(reg_no)
        hour_label = calculate_hour_label(time_in)
        groups[study_year].append((hour_label, reg_no, study_year, name, dept, lab, system_no, time_in, time_out, dateval))

    # sort each year's group
    for year in groups:
        groups[year].sort(key=lambda x: (order.index(x[0]) if x[0] in order else len(order), x[1]))

    # prepare a ZIP archive containing one CSV per year
    zip_buffer = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for year_label, rows_list in groups.items():
            if not rows_list:
                # skip empty groups
                continue
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow([
                "Name", "Reg No", "Department", "Study Year", "Lab", "System No",
                "Time In", "Time Out", "Date"
            ])
            last_label = None
            for hour_label, reg_no, study_year, name, dept, lab, system_no, time_in, time_out, dateval in rows_list:
                if hour_label != last_label:
                    if last_label is not None:
                        writer.writerow([])
                        writer.writerow(["Subject", "", "", "", "", "", "", "", "Staff Signature"])
                        writer.writerow([])
                    writer.writerow([hour_label or "Other Hours"])
                    last_label = hour_label
                writer.writerow([name, reg_no, dept, study_year, lab, system_no, time_in, time_out, dateval])
            if last_label is not None:
                writer.writerow([])
                writer.writerow(["Subject", "", "", "", "", "", "", "", "Staff Signature"])

            csv_buffer.seek(0)
            # filename for this year
            year_name = f"year{year_label or 'other'}"
            fname = f"lab_entries_{year_name}_{filter_date or 'all'}.csv"
            zf.writestr(fname, csv_buffer.getvalue())

    zip_buffer.seek(0)
    archive_name = f"lab_entries_{filter_date or 'all'}_by_year.zip"
    return Response(
        zip_buffer.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment; filename={archive_name}"}
    )


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Initialize the database on first run
    init_db()
    print("=" * 55)
    print("  Digital Lab Record Entry Management System")
    print("=" * 55)
    print("  URL      : http://127.0.0.1:5000")
    print("  Admin    : http://127.0.0.1:5000/admin/login")
    print("  Username : admin")
    print("  Password : admin123")
    print("=" * 55)
    app.run(debug=True)
