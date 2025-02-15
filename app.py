# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import date
import sqlite3
import os
import psycopg2
import psycopg2.extras
from functools import wraps

ADMIN_PASSWORD = 'delete123'

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'attendance.db'


def get_db_connection():
    # DATABASE_URL is automatically set by the Heroku Postgres add-on.
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()  # Create a cursor
    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance_log (
            id SERIAL PRIMARY KEY,
            log_date TEXT,
            resident_name TEXT,
            status TEXT,
            block TEXT
        )
    ''')
    conn.commit()
    cur.close()  # Close the cursor
    conn.close()  # Close the connection


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
block_residents = {
    "6th Block": [
         "Hussain Nouh ICU R5","Dalal ICU R4","Mubarak ICU R4","Ali Al Brahim ICU R3", "Mohammed Al Mulhim ICU R2", "Abdullah Bu Hamad ICU2", "Ali Al Ramadan ICU R1", "Mohammed Al Ithan ICU R1", "Hamzah Al Wehamad ER", "Hassan Al Hamoud IM Senior", "Abdullah Al Beladi IM Senior", "Hassan Al Hassar IM Junior", "Fatimah Al Adelle GS R2", "Zahra Al Awad GS R3", "Ali Al Mohammad Saleh GS R2", "Ammar Bu Khamseen NSX R1"
    ],
    "7th Block": [
        "Ali", "Danny", "Dalal"
    ],
    "8th Block": [
        "Ali Al Brahim ICU R3", "Mohammed Al Mulhim ICU R2", "Abdullah Bu Hamad ICU2", "Ali Al Ramadan ICU R1"
    ],
    "9th Block": [
        "R1 (9th)", "R2 (9th)"
    ],
    "10th Block": [
        "R1 (10th)", "R2 (10th)"
    ],
    "11th Block": [
        "R1 (11th)", "R2 (11th)"
    ],
    "12th Block": [
        "R1 (12th)", "R2 (12th)"
    ],
    "13th Block": [
        "R1 (13th)", "R2 (13th)"
    ]
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

@app.route('/', methods=['GET', 'POST'])
@login_required
def attendance():
    from datetime import datetime, date  # ensure these are imported if not already
    if request.method == 'POST':
        # Get the chosen date and block from the form
        log_date = request.form.get('log_date')
        selected_block = request.form.get('block')
        
        # Validate the date format and convert to a date object
        try:
            chosen_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        except Exception as e:
            flash("Invalid date format.", "danger")
            return redirect(url_for('attendance'))
        
        # Lookup block information from the global 'blocks' list
        block_info = next((b for b in blocks if b["name"] == selected_block), None)
        if not block_info:
            flash("Selected block not found.", "danger")
            return redirect(url_for('attendance'))
        
        # Convert block start and end dates to date objects
        block_start = datetime.strptime(block_info["start"], "%Y-%m-%d").date()
        block_end = datetime.strptime(block_info["end"], "%Y-%m-%d").date()
        
        # Ensure the chosen date falls within the block's range
        if not (block_start <= chosen_date <= block_end):
            flash(f"Selected date {log_date} is not within the range for {selected_block} ({block_info['start']} to {block_info['end']}).", "danger")
            return redirect(url_for('attendance'))
        
        # Connect to the database using psycopg2 and create a cursor
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if any attendance records already exist for this date and block
        cur.execute(
            "SELECT COUNT(*) as count FROM attendance_log WHERE log_date = %s AND block = %s",
            (log_date, selected_block)
        )
        row = cur.fetchone()
        if row and row['count'] > 0:
            flash("Attendance for this date and block already exists. Please use the edit function to modify it.", "warning")
            cur.close()
            conn.close()
            return redirect(url_for('attendance'))
        else:
            # No duplicate found; insert records for each resident in the selected block.
            residents_to_use = block_residents.get(selected_block, [])
            for resident in residents_to_use:
                # Get the submitted status for each resident, defaulting to "Absent" if not provided.
                status = request.form.get(resident, "Absent")
                cur.execute("""
                    INSERT INTO attendance_log (log_date, resident_name, status, block)
                    VALUES (%s, %s, %s, %s)
                """, (log_date, resident, status, selected_block))
            conn.commit()
            cur.close()
            conn.close()
            flash("Attendance log submitted successfully!", "success")
            return redirect(url_for('attendance'))
    else:
        # GET request: load the attendance form.
        # Retrieve selected block and date from query parameters, defaulting to today's date.
        selected_block = request.args.get('block') or ""
        log_date = request.args.get('log_date') or date.today().isoformat()
        if selected_block and selected_block in block_residents:
            residents_to_show = block_residents[selected_block]
        else:
            residents_to_show = []
        return render_template('attendance_form.html', residents=residents_to_show, today=log_date, blocks=blocks, selected_block=selected_block)


@app.route('/logs')
@login_required
def view_logs():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    query = "SELECT * FROM attendance_log WHERE 1=1"
    params = []
    
    resident_filter = request.args.get('resident')
    if resident_filter:
        query += " AND resident_name = %s"
        params.append(resident_filter)
    
    block_filter = request.args.get('block')
    if block_filter:
        query += " AND block = %s"
        params.append(block_filter)
    
    start_date = request.args.get('start_date')
    if start_date:
        query += " AND log_date >= %s"
        params.append(start_date)
    
    end_date = request.args.get('end_date')
    if end_date:
        query += " AND log_date <= %s"
        params.append(end_date)
    
    query += " ORDER BY log_date DESC, resident_name"
    
    cur.execute(query, params)
    logs = cur.fetchall()
    
    cur.close()
    conn.close()
    
    block_names = [b["name"] for b in blocks]
    return render_template('logs.html', logs=logs, residents=residents, blocks=block_names)


@app.route('/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_log(log_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if request.method == 'POST':
        log_date = request.form.get('log_date')
        resident_name = request.form.get('resident_name')
        status = request.form.get('status')
        block_val = request.form.get('block')
        cur.execute('''
            UPDATE attendance_log
            SET log_date = %s, resident_name = %s, status = %s, block = %s
            WHERE id = %s
        ''', (log_date, resident_name, status, block_val, log_id))
        conn.commit()
        cur.close()
        conn.close()
        flash("Log updated successfully!", "success")
        return redirect(url_for('view_logs'))
    else:
        cur.execute('SELECT * FROM attendance_log WHERE id = %s', (log_id,))
        log = cur.fetchone()
        cur.close()
        conn.close()
        if not log:
            flash("Log not found.", "danger")
            return redirect(url_for('view_logs'))
        return render_template('edit_log.html', log=log, blocks=blocks)


@app.route('/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_log(log_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("DELETE FROM attendance_log WHERE id = %s", (log_id,))
    conn.commit()
    cur.close()
    conn.close()
    flash("Attendance log deleted successfully!", "success")
    return redirect(url_for('view_logs'))


@app.route('/delete_all', methods=['POST'])
@login_required
def delete_all():
    entered_password = request.form.get('admin_password')
    if entered_password != ADMIN_PASSWORD:
        flash("Incorrect admin password. Logs were not deleted.", "danger")
        return redirect(url_for('view_logs'))
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("DELETE FROM attendance_log")
    conn.commit()
    cur.close()
    conn.close()
    flash("All attendance logs have been cleared.", "success")
    return redirect(url_for('view_logs'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
