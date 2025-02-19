from flask import Flask, request, jsonify, redirect, session, send_from_directory, render_template
from datetime import datetime
import sqlite3
from flask_cors import CORS
import hashlib
import os
from functools import wraps
from pathlib import Path

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key_here')
# Add database setup

# Add this after your existing database initialization
def init_db():
    """Initialize the database and create required tables"""
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        # Create leave applications table with category field
        c.execute('''
            CREATE TABLE IF NOT EXISTS leave_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_no TEXT NOT NULL,
                student_name TEXT NOT NULL,
                department TEXT NOT NULL,
                year TEXT NOT NULL,
                from_date DATE NOT NULL,
                to_date DATE NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_days INTEGER,
                category TEXT DEFAULT 'General',  # Add category column
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

@app.route('/api/submit_leave', methods=['GET'])
def submit_leave():
    reg_no = request.args.get('regNo')
    department = request.args.get('dept')
    year = request.args.get('year')
    name = request.args.get('name')
    from_date = request.args.get('fromDate')
    to_date = request.args.get('toDate')
    reason = request.args.get('reason')
    category = request.args.get('category', 'General')  # Add category with default value
    
    if not all([reg_no, department, year, name, from_date, to_date, reason]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        total_days = calculate_days(from_date, to_date)
        
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        # Get previous leaves count
        c.execute('SELECT COUNT(*) FROM leave_applications WHERE reg_no = ? AND status = "approved"', (reg_no,))
        previous_leaves = c.fetchone()[0]
        
        # Insert new leave application with category
        c.execute('''
            INSERT INTO leave_applications 
            (reg_no, student_name, department, year, from_date, to_date, reason, total_days, previous_leaves, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (reg_no, name, department, year, from_date, to_date, reason, total_days, previous_leaves, category))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Leave application submitted successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500




# Modify the student leave route to store the application
@app.route('/student/student_leave.html')
def student_leave():
    if request.args:
        try:
            # Calculate total days
            from_date = datetime.strptime(request.args.get('fromDate'), '%Y-%m-%d')
            to_date = datetime.strptime(request.args.get('toDate'), '%Y-%m-%d')
            total_days = (to_date - from_date).days + 1
            
            conn = sqlite3.connect('leave_portal.db')
            c = conn.cursor()
            
            # Insert the leave application with total_days and category
            c.execute('''
                INSERT INTO leave_applications 
                (reg_no, student_name, department, year, from_date, to_date, reason, total_days, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.args.get('regNo'),
                request.args.get('name'),
                request.args.get('dept'),
                request.args.get('year'),
                request.args.get('fromDate'),
                request.args.get('toDate'),
                request.args.get('reason'),
                total_days,
                request.args.get('category', 'General')  # Add category with default
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Leave application submitted successfully'})
            
        except Exception as e:
            print(f"Error storing leave application: {e}")
            return jsonify({'error': str(e)}), 500
    
    return render_template('student_leave.html')
def calculate_days(from_date, to_date):
    start = datetime.strptime(from_date, '%Y-%m-%d')
    end = datetime.strptime(to_date, '%Y-%m-%d')
    return (end - start).days + 1

@app.route('/api/get_student_approved_applications')
def get_student_approved_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # ✅ Get logged-in student's Reg No
        reg_no = session.get('reg_no')
        if not reg_no:
            print("⛔ ERROR: Student not logged in or reg_no missing!")
            return jsonify({'error': 'Unauthorized access'}), 403

        print(f"📌 Fetching approved applications for Student with Reg No: {reg_no}")

        # ✅ Fetch only approved applications for the logged-in student
        c.execute('''
            SELECT id, student_name, reg_no, department, year, 
                   from_date, to_date, reason, total_days, category, status
            FROM leave_applications 
            WHERE status = 'approved' AND reg_no = ?
            ORDER BY from_date DESC
        ''', (reg_no,))

        applications = c.fetchall()
        conn.close()

        if applications:
            print(f"✅ SUCCESS: Found {len(applications)} approved applications for Student {reg_no}")
        else:
            print(f"❌ No approved applications found for Student {reg_no}")

        return jsonify([{
            'id': app[0],
            'name': app[1],
            'studentId': app[2],
            'department': app[3],
            'year': app[4],
            'fromDate': app[5],
            'toDate': app[6],
            'reason': app[7],
            'totalLeaveDays': app[8],
            'category': app[9],
            'status': app[10],
            'photo': '/static/placeholder.jpg'
        } for app in applications])

    except Exception as e:
        print(f"❌ ERROR fetching student approved applications: {e}")
        return jsonify({'error': str(e)}), 500


def get_previous_leaves(reg_no):
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        c.execute('''
            SELECT COUNT(*) FROM leave_applications 
            WHERE reg_no = ? AND status = 'approved'
        ''', (reg_no,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"Error getting previous leaves: {e}")
        return 0

@app.route('/api/update_leave_status', methods=['POST'])
def update_leave_status():
    try:
        data = request.json
        leave_id = data.get('id')
        status = data.get('status')
        role = data.get('role')

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        if role == 'staff' and status == 'staff_approved':
            # Staff approved -> Send to Admin for final approval
            c.execute('''
                UPDATE leave_applications 
                SET status = 'staff_approved'
                WHERE id = ?
            ''', (leave_id,))
            print(f"✅ Leave {leave_id} approved by STAFF and sent to ADMIN")

        elif role == 'admin' and status == 'approved':
            # Admin approved -> Move to Approved Leave Page
            c.execute('''
                UPDATE leave_applications 
                SET status = 'approved'
                WHERE id = ?
            ''', (leave_id,))
            print(f"✅ Leave {leave_id} fully APPROVED by ADMIN")

        elif status == 'rejected':
            # Rejected by either Staff or Admin
            rejected_by = data.get('rejectedBy', role)
            c.execute('''
                UPDATE leave_applications 
                SET status = 'rejected', rejected_by = ?, rejected_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (rejected_by, leave_id))
            print(f"❌ Leave {leave_id} REJECTED by {rejected_by}")

        conn.commit()
        conn.close()

        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ ERROR updating leave status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/student/rejected.html')
def rejected_leave():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        student_id = session.get('user_id')
        
        # Updated query to include rejection details
        c.execute('''
            SELECT 
                la.*,
                datetime(la.rejected_at, 'localtime') as rejected_time
            FROM leave_applications la
            WHERE reg_no = ? AND status = 'rejected'
            ORDER BY rejected_at DESC
        ''', (student_id,))
        
        rejected_leaves = c.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for template
        leaves = []
        for leave in rejected_leaves:
            leaves.append({
                'id': leave[0],
                'name': leave[1],
                'studentId': leave[2],
                'fromDate': leave[5],
                'toDate': leave[6],
                'category': leave[10],
                'status': leave[8],
                'rejectedBy': leave[11],  # Assuming this is the column index for rejected_by
                'rejectedAt': leave[-1]   # Using the aliased rejection time
            })
        
        return render_template('rejected.html', leaves=leaves)
    except Exception as e:
        return str(e)

# Add route to handle student leave application submission



def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt + hash_obj

def verify_password(stored_password, provided_password):
    salt = stored_password[:32]
    stored_hash = stored_password[32:]
    new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
    return stored_hash == new_hash

# Store pre-computed hashed passwords
salt = os.urandom(32)
users = {
    'students': {  # Note: this is plural
        '714023202041': hash_password('student', salt),
        '714023202046': hash_password('student', salt),
        '714023202060':hash_password('student',salt)    },
    'staff': {
        'staff001': hash_password('staff123', salt),
        'staff002': hash_password('staff456', salt),
    },
    'admin': {
        'admin001': hash_password('admin123', salt)
    }
}

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user_type = data.get('userType', '').lower().strip()
    user_id = data.get('username', '').lower().strip()  # This could be student_name, staff_id, or admin_id
    password = data.get('password', '').strip()

    print(f"📌 Received userType: {user_type}")
    print(f"📌 Received username: {user_id}")

    if user_type == 'student':
        user_type = 'students'  # Normalize for consistency

    if not all([user_type, user_id, password]):
        return jsonify({'error': 'Missing credentials'}), 400

    if user_type not in users:
        print(f"❌ Invalid user type: {user_type}")
        return jsonify({'error': 'Invalid user type'}), 400

    if user_id in users[user_type] and verify_password(users[user_type][user_id], password):
        session['user_id'] = user_id
        session['user_type'] = user_type

        # 🔴 Only fetch `reg_no` for students
        if user_type == 'students':
            reg_no = None
            conn = sqlite3.connect('leave_portal.db')
            c = conn.cursor()
            c.execute("SELECT DISTINCT reg_no FROM leave_applications WHERE student_name = ? OR reg_no = ? LIMIT 1", 
                      (user_id, user_id))
            student_data = c.fetchone()
            conn.close()

            if student_data:
                reg_no = student_data[0]
                session['reg_no'] = reg_no  # ✅ Store reg_no in session
                print(f"✅ Student {user_id} logged in with reg_no: {reg_no}")
            else:
                session['reg_no'] = None

        # Define redirects for different user types
        redirects = {
            'students': '/student/dashboard',
            'staff': '/staff/dashboard',
            'admin': '/admin/dashboard'
        }

        return jsonify({
            'success': True,
            'redirect': redirects.get(user_type, '/login'),
            'name': user_id
        })

    print(f"❌ Login failed for user: {user_id}")
    return jsonify({'error': 'Invalid credentials'}), 401

def login_required(user_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session['user_type'] != user_type:
                return redirect('/login')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Ensure template directories exist
def setup_directories():
    base_dir = Path('leave_portal/templates')
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Create empty template files if they don't exist
    template_files = [
        'login_student.html', 
        'student_dash.html', 
        'staff_dash.html', 
        'admin_dash.html',
        '404.html',  # Add error templates
        '500.html'
    ]
    for template in template_files:
        template_path = base_dir / template
        if not template_path.exists():
            template_path.touch()



@app.route('/api/get_leave_applications')
def get_leave_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        user_role = session.get('user_type')
        user_id = session.get('user_id')

        print(f"📌 Fetching leave applications for: {user_id} (Role: {user_role})")

        if user_role == 'staff':
            # Staff should see only pending applications
            c.execute('''
                SELECT * FROM leave_applications WHERE status = 'pending'
            ''')

        elif user_role == 'admin':
            # Admin should see only applications approved by staff
            c.execute('''
                SELECT * FROM leave_applications WHERE status = 'staff_approved'
            ''')

        else:
            # Students should see their own applications
            reg_no = session.get('reg_no')
            if not reg_no:
                print("⛔ ERROR: Student reg_no missing in session!")
                return jsonify([])

            c.execute('''
                SELECT * FROM leave_applications WHERE reg_no = ?
            ''', (reg_no,))

        applications = c.fetchall()
        conn.close()

        if applications:
            print(f"✅ SUCCESS: Found {len(applications)} applications!")
        else:
            print("❌ No leave applications found!")

        return jsonify([{
            'id': app[0],
            'name': app[1],
            'studentId': app[2],
            'department': app[3],
            'year': app[4],
            'fromDate': app[5],
            'toDate': app[6],
            'reason': app[7],
            'status': app[8],
            'totalLeaveDays': app[9],
            'category': app[10],
            'photo': '/static/placeholder.jpg'
        } for app in applications])

    except Exception as e:
        print(f"❌ ERROR fetching leave applications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_rejected_applications')
def get_rejected_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        user_role = session.get('user_type')
        student_id = session.get('user_id')
        reg_no = session.get('reg_no')  # Fetch from session

        # 🔴 If `reg_no` is missing, fetch it from the database
        if user_role == 'students' and not reg_no:
            c.execute("SELECT DISTINCT reg_no FROM leave_applications WHERE student_name = ? OR reg_no = ? LIMIT 1", 
                      (student_id, student_id))
            result = c.fetchone()
            if result:
                reg_no = result[0]
                session['reg_no'] = reg_no  # ✅ Store in session
                print(f"✅ Recovered reg_no from DB: {reg_no}")

        print(f"📌 Fetching rejected applications for: {student_id} (Reg No: {reg_no})")  # Debugging print

        if not reg_no:
            print("❌ ERROR: reg_no is still None!")
            return jsonify([])  # Return empty response

        c.execute('''
            SELECT id, student_name, reg_no, from_date, to_date,
                   category, rejected_by, rejected_at, reason
            FROM leave_applications 
            WHERE status = 'rejected' AND reg_no = ?
            ORDER BY rejected_at DESC
        ''', (reg_no,))

        applications = c.fetchall()
        conn.close()

        if applications:
            print("✅ SUCCESS: Rejected applications found!", applications)
        else:
            print("❌ No rejected applications found in DB!")

        return jsonify([{
            'id': app[0],
            'name': app[1],
            'studentId': app[2],
            'fromDate': app[3],
            'toDate': app[4],
            'category': app[5],
            'rejectedBy': app[6] or 'Unknown',
            'rejectedAt': app[7],
            'reason': app[8] or 'No reason provided'
        } for app in applications])

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_approved_applications')
def get_approved_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # ✅ Fetch only applications where status is 'approved'
        c.execute('''
            SELECT id, student_name, reg_no, department, year, 
                   from_date, to_date, reason, total_days, category, status
            FROM leave_applications 
            WHERE status = 'approved'
            ORDER BY from_date DESC
        ''')

        applications = c.fetchall()
        conn.close()

        if applications:
            print(f"✅ SUCCESS: Found {len(applications)} approved applications!")
        else:
            print("❌ No approved applications found!")

        return jsonify([{
            'id': app[0],
            'name': app[1],
            'studentId': app[2],
            'department': app[3],
            'year': app[4],
            'fromDate': app[5],
            'toDate': app[6],
            'reason': app[7],
            'totalLeaveDays': app[8],
            'category': app[9],
            'status': app[10],  # ✅ Ensure status is included
            'photo': '/static/placeholder.jpg'
        } for app in applications])

    except Exception as e:
        print(f"❌ ERROR fetching approved applications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
@app.route('/login')
def serve_login():
    return render_template('login_student.html')

@app.route('/statics/js/login_js.js')
def login_js():
    return send_from_directory('statics/js', 'login_js.js')

@app.route('/student/dashboard')
@login_required('students')
def student_dashboard():
    return render_template('student_dash.html')

@app.route('/staff/dashboard')
@login_required('staff')
def staff_dashboard():
    return render_template('staff_dash.html')

@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    return render_template('admin_dash.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
# admin
@app.route('/admin/admin_permission.html')
def admin_permission():
    return render_template('admin_permission.html')

@app.route('/admin/admin_new_students.html')
def admin_new_student():
    return render_template('admin_new_students.html')

@app.route('/admin/admin_dash.html')
def admin_dash():
    return render_template('admin_dash.html')

@app.route('/admin/Manage_student.html')
def Manage_student():
    return render_template('Manage_student.html')

@app.route('/admin/admin_leave.html')
def admin_leave():
    return render_template('admin_leave.html')

@app.route('/admin/statics/css/admin_css1.css')
def admin_css1():
    return send_from_directory('statics/css', 'admin_css1.css')

@app.route('/admin/statics/css/admin_css2.css')
def admin_css2():
    return send_from_directory('statics/css', 'admin_css2.css')


@app.route('/admin/statics/css/admin_css3.css')
def admin_css3():
    return send_from_directory('statics/css', 'admin_css3.css')

@app.route('/admin/statics/css/admin_css4.css')
def admin_css4():
    return send_from_directory('statics/css', 'admin_css4.css')

@app.route('/admin/statics/css/admin_css5.css')
def admin_css5():
    return send_from_directory('statics/css', 'admin_css5.css')

@app.route('/admin/new_student.html')
def add_studet():
    return render_template('new_student.html')

@app.route('/staff/statics/css/student_css1.css')
def st_css1():
    return send_from_directory('statics/css', 'student_css1.css')

@app.route('/admin/login_student.html')
def login_admin():
    return render_template('login_student.html')



# staff
@app.route('/staff/staff_permission.html')
def staff_permission():
    return render_template('staff_permission.html')

@app.route('/staff/staff_manage.html')
def staff_manage():
    return render_template('staff_manage.html')

@app.route('/staff/staff_leave_request.html')
def staff_leave_request():
    return render_template('staff_leave_request.html')

@app.route('/staff/statics/css/staff_css1.css')
def staff_css1():
    return send_from_directory('statics/css', 'staff_css1.css')

@app.route('/staff/statics/css/staff_css2.css')
def staff_css2():
    return send_from_directory('statics/css', 'staff_css2.css')


@app.route('/staff/statics/css/staff_css3.css')
def staff_css3():
    return send_from_directory('statics/css', 'staff_css3.css')

@app.route('/staff/statics/css/staff_css4.css')
def staff_css4():
    return send_from_directory('statics/css', 'staff_css4.css')

@app.route('/staff/statics/css/staff_css5.css')
def staff_css5():
    return send_from_directory('statics/css', 'staff_css5.css')

@app.route('/staff/staff_dash.html')
def staff_dash():
    return render_template('staff_dash.html')

@app.route('/staff/new_student.html')
def add_student():
    return render_template('new_student.html')

@app.route('/staff/statics/css/student_css1.css')
def stu_css1():
    return send_from_directory('statics/css', 'student_css1.css')

@app.route('/staff/login_student.html')
def login_staff():
    return send_from_directory('templates','login_student.html')


#students
@app.route('/student/student_permission.html')
def student_permission():
    return render_template('student_permission.html')

@app.route('/student/student_dash.html')
def student_dash():
    return render_template('student_dash.html')

@app.route('/student/statics/css/staff_css2.css')
def stastu_css2():
    return send_from_directory('statics/css', 'staff_css2.css')

@app.route('/student/student_leave.html')
def student_leave_request():
    return render_template('student_leave.html')

@app.route('/student/statics/css/student_css.css')
def student_css():
    return send_from_directory('statics/css', 'student_css.css')

@app.route('/student/statics/css/student_css1.css')
def student_css1():
    return send_from_directory('statics/css', 'student_css1.css')


@app.route('/student/statics/css/student_css2.css')
def student_css2():
    return send_from_directory('statics/css', 'student_css2.css')

@app.route('/student/statics/css/student_css3.css')
def student_css3():
    return send_from_directory('statics/css', 'student_css3.css')

@app.route('/student/statics/css/student_css4.css')
def student_css4():
    return send_from_directory('statics/css', 'student_css4.css')

@app.route('/student/student_result.html')
def student_result():
    return render_template('student_result.html')

@app.route('/student/login_student.html')
def login_student():
    return render_template('login_student.html')

@app.route('/student/approved.html')
def approved_leave():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        student_id = session.get('user_id')
        
        c.execute('''
            SELECT * FROM leave_applications 
            WHERE reg_no = ? AND status = 'approved'
            ORDER BY created_at DESC
        ''', (student_id,))
        
        approved_leaves = c.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for template
        leaves = []
        for leave in approved_leaves:
            leaves.append({
                'status': leave[8]
            })
        
        return render_template('approved.html', leaves=leaves)
    except Exception as e:
        return str(e)


@app.route('/statics/css/login_css.css')
def login_css():
    return send_from_directory('statics/css', 'login_css.css')


# @app.route('/student/statics/css/student_css.css')
# def student_css():
#     return send_from_directory('statics/css', 'student_css.css')

@app.route('/student/statics/css/login_css.css')
def stu_log_css():
    return send_from_directory('statics/css', 'login_css.css')

@app.route('/staff/statics/css/login_css.css')
def stf_log_css():
    return send_from_directory('statics/css', 'login_css.css')

@app.route('/admin/statics/css/login_css.css')
def adm_log_css():
    return send_from_directory('statics/css', 'login_css.css')

if __name__ == '__main__':
    setup_directories()
    app.run(host='0.0.0.0',port="5000",debug=False)


