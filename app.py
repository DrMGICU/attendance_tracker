# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'attendance.db'

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
        "Resident A (7th)", 
        "Resident B (7th)", 
        "Resident C (7th)"
    ],
    "8th Block": [
        "Resident X (8th)", 
        "Resident Y (8th)", 
        "Resident Z (8th)"
    ],
    "9th Block": [
        "R1 (9th)",
        "R2 (9th)"
    ],
    "10th Block": [
        "R1 (10th)",
        "R2 (10th)"
    ],
    "11th Block": [
        "R1 (11th)",
        "R2 (11th)"
    ],
    "12th Block": [
        "R1 (12th)",
        "R2 (12th)"
    ],
    "13th Block": [
        "R1 (13th)", 
        "R2 (13th)"
        ],
    }

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Force-drop and recreate the attendance_log table with the updated schema."""
    conn = get_db_connection()
    conn.execute("DROP TABLE IF EXISTS attendance_log")
    conn.execute('''
        CREATE TABLE attendance_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT,
            resident_name TEXT,
            status TEXT,
            block TEXT
        )
    ''')
    conn.commit()
    conn.close()
# Define blocks as a list of dictionaries
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
    if request.method == 'POST':
        log_date = request.form.get('log_date')
        selected_block = request.form.get('block')
        conn = get_db_connection()
        # Use the residents from the selected block (if available)
        residents_to_save = block_residents.get(selected_block, [])
        # Loop over the block-specific residents and save each record
        for resident in residents_to_save:
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
        selected_block = request.args.get('block')
        if selected_block and selected_block in block_residents:
            residents_to_show = block_residents[selected_block]
        else:
            residents_to_show = []  # Or you could set a default block
        today = date.today().isoformat()
        return render_template('attendance_form.html', residents=residents_to_show, today=today, blocks=blocks, selected_block=selected_block)

    # Set the default date to today's date.
    today = date.today().isoformat()
    return render_template('attendance_form.html', residents=residents, today=today)

# --- View Logs ---
@app.route('/logs')
def view_logs():
    conn = get_db_connection()
    query = "SELECT * FROM attendance_log WHERE 1=1"
    params = []

    # Filter by resident if provided
    resident_filter = request.args.get('resident')
    if resident_filter:
        query += " AND resident_name = ?"
        params.append(resident_filter)
    
    # Filter by block if provided
    block_filter = request.args.get('block')
    if block_filter:
        query += " AND block = ?"
        params.append(block_filter)
    
    # Filter by start date
    start_date = request.args.get('start_date')
    if start_date:
        query += " AND log_date >= ?"
        params.append(start_date)
    
    # Filter by end date
    end_date = request.args.get('end_date')
    if end_date:
        query += " AND log_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY log_date DESC, resident_name"
    logs = conn.execute(query, params).fetchall()
    conn.close()
    
    # For the filtering form we need a list of resident names and block names
    block_names = [b["name"] for b in blocks]
    return render_template('logs.html', logs=logs, residents=residents, blocks=block_names)

@app.route('/edit/<int:log_id>', methods=['GET', 'POST'])
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
        return render_template('edit_log.html', log=log, blocks=blocks)

if __name__ == '__main__':
    # Get the port from environment variable or use 5000 as default
    port = int(os.environ.get("PORT", 5000))
    # Bind to 0.0.0.0 to be reachable externally
    app.run(host='0.0.0.0', port=port, debug=True)