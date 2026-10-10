from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB_PATH = Path(__file__).with_name("student_academic.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            register_no TEXT NOT NULL UNIQUE,
            student_name TEXT NOT NULL,
            department TEXT NOT NULL,
            study_year INTEGER NOT NULL CHECK(study_year BETWEEN 1 AND 6)
        );
        CREATE TABLE IF NOT EXISTS courses (
            course_id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL UNIQUE,
            course_name TEXT NOT NULL,
            semester INTEGER NOT NULL CHECK(semester BETWEEN 1 AND 12)
        );
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            UNIQUE(student_id, course_id, attendance_date),
            FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS marks (
            mark_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            assessment_name TEXT NOT NULL,
            marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
            max_marks REAL NOT NULL CHECK(max_marks > 0 AND marks_obtained <= max_marks),
            FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE
        );
        """)
        # Demo data is inserted only when the tables are empty.
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO students(register_no, student_name, department, study_year) VALUES (?, ?, ?, ?)",
                [("A001", "Arun", "AI&DS", 2), ("A002", "Divya", "AI&DS", 2), ("A003", "Rahul", "CSE", 2)]
            )
        if conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO courses(course_code, course_name, semester) VALUES (?, ?, ?)",
                [("23DBMS", "Database Management Systems", 3), ("23JAVA", "Object Oriented Programming", 3)]
            )

@app.route("/")
def index():
    with get_db() as conn:
        student_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        course_count = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        attendance_count = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        marks_count = conn.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
        recent = conn.execute("""
            SELECT a.attendance_date, a.status, s.student_name, s.register_no, c.course_name
            FROM attendance a
            JOIN students s ON s.student_id = a.student_id
            JOIN courses c ON c.course_id = a.course_id
            ORDER BY a.attendance_date DESC, a.attendance_id DESC LIMIT 8
        """).fetchall()
    return render_template("index.html", student_count=student_count, course_count=course_count,
                           attendance_count=attendance_count, marks_count=marks_count, recent=recent)

@app.route("/students", methods=["GET", "POST"])
def students():
    with get_db() as conn:
        if request.method == "POST":
            try:
                conn.execute(
                    "INSERT INTO students(register_no, student_name, department, study_year) VALUES (?, ?, ?, ?)",
                    (request.form["register_no"].strip(), request.form["student_name"].strip(),
                     request.form["department"].strip(), int(request.form["study_year"]))
                )
                conn.commit()
                flash("Student added successfully.", "success")
            except (sqlite3.IntegrityError, ValueError):
                flash("Could not add student. Check the fields and make sure the register number is unique.", "error")
            return redirect(url_for("students"))
        rows = conn.execute("SELECT * FROM students ORDER BY student_id DESC").fetchall()
    return render_template("students.html", students=rows)

@app.post("/students/delete/<int:student_id>")
def delete_student(student_id):
    with get_db() as conn:
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("students"))

@app.route("/courses", methods=["GET", "POST"])
def courses():
    with get_db() as conn:
        if request.method == "POST":
            try:
                conn.execute(
                    "INSERT INTO courses(course_code, course_name, semester) VALUES (?, ?, ?)",
                    (request.form["course_code"].strip(), request.form["course_name"].strip(),
                     int(request.form["semester"]))
                )
                conn.commit()
                flash("Course added successfully.", "success")
            except (sqlite3.IntegrityError, ValueError):
                flash("Could not add course. Check the fields and make sure the course code is unique.", "error")
            return redirect(url_for("courses"))
        rows = conn.execute("SELECT * FROM courses ORDER BY course_id DESC").fetchall()
    return render_template("courses.html", courses=rows)

@app.post("/courses/delete/<int:course_id>")
def delete_course(course_id):
    with get_db() as conn:
        conn.execute("DELETE FROM courses WHERE course_id = ?", (course_id,))
        conn.commit()
    flash("Course deleted.", "success")
    return redirect(url_for("courses"))

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    with get_db() as conn:
        if request.method == "POST":
            try:
                conn.execute("""
                    INSERT INTO attendance(student_id, course_id, attendance_date, status)
                    VALUES (?, ?, ?, ?)
                """, (int(request.form["student_id"]), int(request.form["course_id"]),
                      request.form["attendance_date"], request.form["status"]))
                conn.commit()
                flash("Attendance saved.", "success")
            except (sqlite3.IntegrityError, ValueError):
                flash("Could not save attendance. A record may already exist for this student, course and date.", "error")
            return redirect(url_for("attendance"))
        student_rows = conn.execute("SELECT * FROM students ORDER BY student_name").fetchall()
        course_rows = conn.execute("SELECT * FROM courses ORDER BY course_name").fetchall()
        records = conn.execute("""
            SELECT a.*, s.student_name, s.register_no, c.course_name
            FROM attendance a JOIN students s ON a.student_id=s.student_id
            JOIN courses c ON a.course_id=c.course_id
            ORDER BY a.attendance_date DESC, a.attendance_id DESC
        """).fetchall()
    return render_template("attendance.html", students=student_rows, courses=course_rows, records=records)

@app.route("/marks", methods=["GET", "POST"])
def marks():
    with get_db() as conn:
        if request.method == "POST":
            try:
                obtained = float(request.form["marks_obtained"])
                maximum = float(request.form["max_marks"])
                if maximum <= 0 or obtained < 0 or obtained > maximum:
                    raise ValueError
                conn.execute("""
                    INSERT INTO marks(student_id, course_id, assessment_name, marks_obtained, max_marks)
                    VALUES (?, ?, ?, ?, ?)
                """, (int(request.form["student_id"]), int(request.form["course_id"]),
                      request.form["assessment_name"].strip(), obtained, maximum))
                conn.commit()
                flash("Marks saved.", "success")
            except (sqlite3.IntegrityError, ValueError):
                flash("Enter valid marks. Obtained marks must be between zero and maximum marks.", "error")
            return redirect(url_for("marks"))
        student_rows = conn.execute("SELECT * FROM students ORDER BY student_name").fetchall()
        course_rows = conn.execute("SELECT * FROM courses ORDER BY course_name").fetchall()
        records = conn.execute("""
            SELECT m.*, s.student_name, s.register_no, c.course_name,
                   ROUND(100.0 * m.marks_obtained / m.max_marks, 2) AS percentage
            FROM marks m JOIN students s ON m.student_id=s.student_id
            JOIN courses c ON m.course_id=c.course_id
            ORDER BY m.mark_id DESC
        """).fetchall()
    return render_template("marks.html", students=student_rows, courses=course_rows, records=records)

@app.route("/reports")
def reports():
    with get_db() as conn:
        attendance_report = conn.execute("""
            SELECT s.register_no, s.student_name, c.course_name,
                   SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) AS present_count,
                   COUNT(a.attendance_id) AS total_count,
                   CASE WHEN COUNT(a.attendance_id)=0 THEN 0
                        ELSE ROUND(100.0 * SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)
                             / COUNT(a.attendance_id), 2) END AS percentage
            FROM students s CROSS JOIN courses c
            LEFT JOIN attendance a ON a.student_id=s.student_id AND a.course_id=c.course_id
            GROUP BY s.student_id, c.course_id
            ORDER BY s.student_name, c.course_name
        """).fetchall()
        marks_report = conn.execute("""
            SELECT s.register_no, s.student_name, c.course_name, m.assessment_name,
                   m.marks_obtained, m.max_marks,
                   ROUND(100.0*m.marks_obtained/m.max_marks, 2) AS percentage
            FROM marks m JOIN students s ON s.student_id=m.student_id
            JOIN courses c ON c.course_id=m.course_id
            ORDER BY s.student_name, c.course_name
        """).fetchall()
    return render_template("reports.html", attendance_report=attendance_report, marks_report=marks_report)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
