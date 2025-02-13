# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import date
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'attendance.db'

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
            block TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database at startup
init_db()

# Global list of blocks (used in both attendance form and logs filtering)
blocks = [
    {"name": "6th Block", "start": "2025-02-16", "end": "2025-03-15"},
    {"name": "7th Block", "start": "2025-03-16", "end": "2025-04-12"},
    {"name": "8th Block", "start": "2025-04-13", "end": "2025-05-10"},
    {"name": "9th Block", "start": "2025-05-11", "end": "2025-06-07"},
    {"name": "10th Block", "start": "2025-06-08", "end": "2025-07-05"},
    {"name": "11th Block", "start": "2025-07-06", "end": "2025-08-02"},
    {"name": "12th Block", "start": "2025-08-03", "end": "2025-08-30"},
    {"name": "13th Block", "start": "2025-08-31", "end": "2025-09-27"}
]

# Dictionary mapping block names to block-specific residents for attendance
residents = [
    "Ali Al Brahim ICU R3", "Mohammed Al Mulhim ICU R2", "Abdullah Bu Hamad ICU2",
    "Ali Al Ramadan ICU R1", "Mohammed Al Ithan ICU R1", "Hamzah Al Wehamad ER",
    "Hassan Al Hamoud IM Senior", "Abdullah Al Beladi IM Senior",
    "Hassan Al Hassar IM Junior", "Fatimah Al Adelle GS R2",
    "Zahra Al Awad GS R3", "Ali Al Mohammad Saleh GS R2", "Ammar Bu Khamseen NSX R1"
]
# Dictionary mapping block names to a list of residents for that block
block_residents = {
    "6th Block": [
        "Ali Al Brahim ICU R3", 
        "Mohammed Al Mulhim ICU R2", 
        "Abdullah Bu Hamad ICU2", 
        "Ali Al Ramadan ICU R1", 
        "Mohammed Al Ithan ICU R1", 
        "Hamzah Al Wehamad ER", 
        "Hassan Al Hamoud IM Senior", 
        "Abdullah Al Beladi IM Senior", 
        "Hassan Al Hassar IM Junior", 
        "Fatimah Al Adelle GS R2", 
        "Zahra Al Awad GS R3", 
        "Ali Al Mohammad Saleh GS R2", 
        "Ammar Bu Khamseen NSX R1"
    ],
    "7th Block": [
        "Ali Al Brahim ICU R3", 
        "Mohammed Al Mulhim ICU R2", 
        "Ali Al Ramadan ICU R1"
    ],
    "8th Block": [
        "Mohammed Al Ithan ICU R1", 
        "Hamzah Al Wehamad ER", 
        "Hassan Al Hamoud IM Senior"
    ],
    "9th Block": [
        "Ali Al Brahim ICU R3",
        "Mohammed Al Mulhim ICU R2"
    ],
    "10th Block": [
        "Ali Al Brahim ICU R3",
        "Mohammed Al Mulhim ICU R2"
    ],
    "11th Block": [
        "Ali Al Brahim ICU R3",
        "Mohammed Al Mulhim ICU R2"
    ],
    "12th Block": [
        "Ali Al Brahim ICU R3",
        "Mohammed Al Mulhim ICU R2"
    ],
    "13th Block": [
        "Ali Al Brahim ICU R3",
        "Mohammed Al Mulhim ICU R2"
    ],
    }

# Global residents list (used for logs filtering)
# This is built as a union of all block residents:
all_residents = set()
for res_list in block_residents.values():
    all_residents.update(res_list)
residents = list(all_residents)

# Decorator to require login on protected routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash("Please log in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Credentials (for demonstration)
USERNAME = 'admin'
PASSWORD = 'password123'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        pwd = request.form.get('password')
        if username == USERNAME and pwd == PASSWORD:
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
@login_required
def attendance():
    if request.method == 'POST':
        log_date = request.form.get('log_date')
        selected_block = request.form.get('block')
        conn = get_db_connection()
        # Use the block-specific resident list
        residents_to_use = block_residents.get(selected_block, [])
        for resident in residents_to_use:
            status = request.form.get(resident, "Absent")
            conn.execute('''
                INSERT INTO attendance_log (log_date, resident_name, status, block)
                VALUES (?, ?, ?, ?)
            ''', (log_date, resident, status, selected_block))
        conn.commit()
        conn.close()
        flash("Attendance log submitted successfully!", "success")
        return redirect(url_for('attendance'))
    else:
        # GET: Show the attendance form.
        # Expecting a block to be selected first via a GET parameter.
        selected_block = request.args.get('block') or ""
        if selected_block and selected_block in block_residents:
            residents_to_show = block_residents[selected_block]
        else:
            residents_to_show = []  # No block selected; you might display a message.
        today = date.today().isoformat()
        return render_template('attendance_form.html', residents=residents_to_show, today=today, blocks=blocks, selected_block=selected_block)

@app.route('/logs')
@login_required
def view_logs():
    conn = get_db_connection()
    query = "SELECT * FROM attendance_log WHERE 1=1"
    params = []
    resident_filter = request.args.get('resident')
    if resident_filter:
        query += " AND resident_name = ?"
        params.append(resident_filter)
    block_filter = request.args.get('block')
    if block_filter:
        query += " AND block = ?"
        params.append(block_filter)
    start_date = request.args.get('start_date')
    if start_date:
        query += " AND log_date >= ?"
        params.append(start_date)
    end_date = request.args.get('end_date')
    if end_date:
        query += " AND log_date <= ?"
        params.append(end_date)
    query += " ORDER BY log_date DESC, resident_name"
    logs = conn.execute(query, params).fetchall()
    conn.close()
    block_names = [b["name"] for b in blocks]
    return render_template('logs.html', logs=logs, residents=residents, blocks=block_names)

@app.route('/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    conn = get_db_connection()
    if request.method == 'POST':
        log_date = request.form.get('log_date')
        resident_name = request.form.get('resident_name')
        status = request.form.get('status')
        block_val = request.form.get('block')
        conn.execute('''
            UPDATE attendance_log
            SET log_date = ?, resident_name = ?, status = ?, block = ?
            WHERE id = ?
        ''', (log_date, resident_name, status, block_val, log_id))
        conn.commit()
        conn.close()
        flash("Log updated successfully!", "success")
        return redirect(url_for('view_logs'))
    else:
        log = conn.execute('SELECT * FROM attendance_log WHERE id = ?', (log_id,)).fetchone()
        conn.close()
        if not log:
            flash("Log not found.", "danger")
            return redirect(url_for('view_logs'))
        return render_template('edit_log.html', log=log, blocks=blocks)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)