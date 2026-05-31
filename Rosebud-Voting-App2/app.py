from flask import Flask, render_template, request, jsonify, redirect
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

DB_NAME = 'RosebudElectionDB.db'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            class TEXT,
            image_path TEXT,
            has_voted INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            class_room TEXT NOT NULL,
            manifesto TEXT,       
            votes INTEGER DEFAULT 0,
            image_path TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            candidate_id INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            setting_name TEXT PRIMARY KEY,
            setting_value INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS volunteers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    ''')

    cursor.execute("INSERT OR IGNORE INTO settings (setting_name, setting_value) VALUES ('show_results', 0)")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_panel')
def admin_panel():
    admin_mock = {
        'name': 'System Administrator',
        'student_id': 'ADMIN',
        'class': 'Server Room',
        'image_path': 'default.png'
    }
    return render_template('admin.html', student=admin_mock)

@app.route('/api/admin/get_student/<path:sid>')
def get_student_details(sid):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (sid,)).fetchone()
    db.close()
    if student:
        return jsonify(dict(student))
    return jsonify({"error": "Not found"}), 404

@app.route('/election_ballot/<path:sid>')
def election_ballot(sid):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (sid,)).fetchone()
    db.close()
    if student:
        return render_template('election_ballot.html', student=student)
    return redirect('/')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = str(data.get('username', '')).strip().upper()
    password = data.get('password')

    if username == "ADMIN" and password == "SERVER":
        return jsonify({"status": "success", "role": "admin"})

    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (username,)).fetchone()
    db.close()

    if student:
        return jsonify({"status": "success", "role": "student", "user": username})
    
    return jsonify({"status": "error", "message": "Invalid ID"})

@app.route('/api/admin/add_student', methods=['POST'])
def add_student():
    sid = request.form.get('student_id').strip().upper()
    name = request.form.get('name')
    s_class = request.form.get('class')
    file = request.files.get('image')
    
    filename = "default.png"
    if file:
        filename = secure_filename(f"{sid}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    db = get_db()
    db.execute('INSERT INTO students (student_id, name, class, image_path) VALUES (?, ?, ?, ?)', 
               (sid, name, s_class, filename))
    db.commit()
    db.close()
    return jsonify({"status": "success", "message": "Student Registered Successfully!"})

@app.route('/student_portal/<path:sid>')
def student_portal(sid):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (sid,)).fetchone()
    
    candidate_info = db.execute('SELECT manifesto FROM candidates WHERE student_id = ?', (sid,)).fetchone()
    
    is_candidate = 1 if candidate_info else 0
    candidate_manifesto = candidate_info['manifesto'] if candidate_info else ""

    return render_template('student_page.html', 
                           student=student, 
                           is_candidate=is_candidate, 
                           candidate_manifesto=candidate_manifesto)

@app.route('/api/admin/add_candidate', methods=['POST'])
def add_candidate():
    data = request.json
    sid = data.get('student_id')
    pos = data.get('position')
    
    db = get_db()
    
    student = db.execute('SELECT name, class, image_path FROM students WHERE student_id = ?', (sid,)).fetchone()
    
    if not student:
        db.close()
        return jsonify({"status": "error", "message": "Student record not found"}), 404

    try:
        db.execute('''
            INSERT INTO candidates (student_id, name, position, class_room, manifesto, image_path) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sid, student['name'], pos, student['class'], "Ready to serve!", student['image_path']))
        
        db.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    db = get_db()
    candidates = db.execute('SELECT * FROM candidates').fetchall()
    db.close()
    return jsonify([dict(c) for c in candidates])

@app.route('/api/vote', methods=['POST'])
def vote():
    data = request.json
    sid = data.get('student_id')
    cids = data.get('candidate_ids')

    db = get_db()
    
    student = db.execute('SELECT has_voted FROM students WHERE student_id = ?', (sid,)).fetchone()
    if student and student['has_voted'] == 1:
        return jsonify({"status": "error", "message": "You have already cast your ballot!"}), 403

    for cid in cids:
        db.execute('INSERT INTO votes (student_id, candidate_id) VALUES (?, ?)', (sid, cid))
    
    db.execute('UPDATE students SET has_voted = 1 WHERE student_id = ?', (sid,))
    
    db.commit()
    return jsonify({"status": "success"})

@app.route('/api/students', methods=['GET'])
def get_all_students():
    db = get_db()
    students = db.execute('SELECT student_id, name, class FROM students').fetchall()
    db.close()
    return jsonify([dict(s) for s in students])

@app.route('/admin/election_ballot')
def admin_view_ballot():
    admin_mock = {
        'name': 'System Admin', 
        'student_id': 'ADMIN', 
        'image_path': 'School-logo.png'
    }
    return render_template('election_ballot.html', student=admin_mock)

@app.route('/api/candidate/update_manifesto', methods=['POST'])
def update_manifesto():
    data = request.json
    db = get_db()
    db.execute('UPDATE candidates SET manifesto = ? WHERE student_id = ?', 
               (data['manifesto'], data['student_id']))
    db.commit()
    return jsonify({"status": "success"})

@app.route('/api/volunteer/apply', methods=['POST'])
def volunteer():
    data = request.json
    db = get_db()
    student = db.execute('SELECT name FROM students WHERE student_id = ?', (data['student_id'],)).fetchone()
    name = student['name'] if student else "Unknown"
    db.execute('INSERT INTO volunteers (student_id, name, position, reason) VALUES (?, ?, ?, ?)',
               (data['student_id'], name, data['position'], data['reason']))
    db.commit()
    db.close()
    return jsonify({"status": "success", "message": "Application submitted!"})

@app.route('/election_result/<path:sid>')
def election_results(sid):
    db = get_db()
    setting = db.execute('SELECT setting_value FROM settings WHERE setting_name = "show_results"').fetchone()
    if not setting or setting['setting_value'] == 0:
        db.close()
        return """
<center>
    <h1 style="margin-top: 50px; color: #002147;">Results are not yet Published</h1>
    <p>The Admin has not released the official tally. Please check back later!</p>
</center>
"""

    student = db.execute('SELECT * FROM students WHERE student_id=?', (sid,)).fetchone()
    if not student:
        db.close()
        return redirect('/')
    
    positions = db.execute('SELECT DISTINCT position FROM candidates').fetchall()
    
    results_data = []
    total_school_votes = db.execute('SELECT COUNT(*) as total FROM votes').fetchone()['total']

    for pos in positions:
        pos_name = pos['position']
        candidates = db.execute('''
            SELECT c.*, COUNT(v.id) as vote_count 
            FROM candidates c
            LEFT JOIN votes v ON c.id = v.candidate_id
            WHERE c.position = ?
            GROUP BY c.id
            ORDER BY vote_count DESC
        ''', (pos_name,)).fetchall()

        if candidates:
            pos_total = sum(c['vote_count'] for c in candidates)
            
            winner = dict(candidates[0])
            winner['percentage'] = round((winner['vote_count'] / pos_total * 100), 1) if pos_total > 0 else 0
            
            runner_up = None
            if len(candidates) > 1:
                runner_up = dict(candidates[1])
                runner_up['percentage'] = round((runner_up['vote_count'] / pos_total * 100), 1) if pos_total > 0 else 0

            results_data.append({
                'position': pos_name,
                'winner': winner,
                'runner_up': runner_up
            })

    db.close()
    return render_template('election_result.html', results=results_data, total_votes=total_school_votes, student=student)

@app.route('/api/admin/settings', methods=['GET'])
def get_settings():
    db = get_db()
    show_results = db.execute('SELECT setting_value FROM settings WHERE setting_name = "show_results"').fetchone()
    db.close()
    return jsonify({"show_results": show_results['setting_value'] if show_results else 0})

@app.route('/api/admin/toggle_results', methods=['POST'])
def toggle_results():
    data = request.json
    new_val = 1 if data.get('visible') else 0
    db = get_db()
    db.execute('UPDATE settings SET setting_value = ? WHERE setting_name = "show_results"', (new_val,))
    db.commit()
    db.close()
    return jsonify({"status": "success"})

@app.route('/api/admin/update_student', methods=['POST'])
def update_student():
    sid = request.form.get('student_id').strip().upper()
    new_name = request.form.get('name')
    new_class = request.form.get('class')
    file = request.files.get('image')
    
    db = get_db()
    
    if file:
        filename = secure_filename(f"{sid}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.execute('UPDATE students SET name=?, class=?, image_path=? WHERE student_id=?', 
                   (new_name, new_class, filename, sid))
    else:
        db.execute('UPDATE students SET name=?, class=? WHERE student_id=?', 
                   (new_name, new_class, sid))
    
    db.commit()
    db.close()
    return jsonify({"status": "success"})

@app.route('/api/admin/delete_student/<path:sid>', methods=['POST'])
def delete_student(sid):
    sid = sid.strip().upper()
    db = get_db()
    try:
        db.execute('DELETE FROM students WHERE student_id = ?', (sid,))
        db.execute('DELETE FROM candidates WHERE student_id = ?', (sid,))
        db.execute('DELETE FROM volunteers WHERE student_id = ?', (sid,))
        db.execute('DELETE FROM votes WHERE student_id = ?', (sid,))
        candidate = db.execute('SELECT id FROM candidates WHERE student_id = ?', (sid,)).fetchone()
        if candidate:
            db.execute('DELETE FROM votes WHERE candidate_id = ?', (candidate['id'],))
        
        db.commit()
        return jsonify({"status": "success", "message": "Student and all related data removed."})
    except Exception as e:
        print(f"Delete error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)







    