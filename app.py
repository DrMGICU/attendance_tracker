# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a strong, random key in production

DATABASE = 'attendance.db'

# A list of residents. (In a real app, this may come from a database table.)
residents = ["Dr. Smith", "Dr. Jones", "Dr. Lee", "Dr. Patel"]

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create the attendance_log table if it doesn't exist."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT,
            resident_name TEXT,
            status TEXT,
            log_type TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database on startup
init_db()

# --- Simple Authentication ---
USERNAME = 'admin'
PASSWORD = 'password123'  # Change this for production

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render the login page and validate credentials."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            flash("You are now logged in!", "success")
            return redirect(url_for('attendance'))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

# --- Attendance Form ---
@app.route('/', methods=['GET', 'POST'])
def attendance():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        log_date = request.form.get('log_date')
        log_type = request.form.get('log_type')
        conn = get_db_connection()
        # Loop through residents and save each record
        for resident in residents:
            status = request.form.get(resident)
            if not status:
                status = "Absent"  # Default if none selected
            conn.execute('''
                INSERT INTO attendance_log (log_date, resident_name, status, log_type)
                VALUES (?, ?, ?, ?)
            ''', (log_date, resident, status, log_type))
        conn.commit()
        conn.close()
        flash("Attendance log submitted successfully!", "success")
        return redirect(url_for('attendance'))

    # Set the default date to today's date.
    today = date.today().isoformat()
    return render_template('attendance_form.html', residents=residents, today=today)

# --- View Logs ---
@app.route('/logs')
def view_logs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    # Retrieve logs ordered by date descending
    logs = conn.execute('SELECT * FROM attendance_log ORDER BY log_date DESC, id DESC').fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

if __name__ == '__main__':
    app.run(debug=True)
