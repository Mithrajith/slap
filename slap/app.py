from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, redirect, session, send_from_directory, render_template
from datetime import datetime
import sqlite3
from flask_cors import CORS
import hashlib
import os
from functools import wraps
from pathlib import Path
from flask_session import Session

app = Flask(__name__)
CORS(app)

# Ensure session directory exists
SESSION_DIR = './session_data'
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

# Flask Session Configuration
app.secret_key = 'your_secret_key_here'  
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on disk
app.config['SESSION_PERMANENT'] = True  # Keep session active
app.config['SESSION_FILE_DIR'] = SESSION_DIR  # Ensure session directory exists
app.config['SESSION_COOKIE_NAME'] = 'leave_portal_session'  # Custom session cookie name

Session(app)  # Initialize session


db = sqlite3.connect('leave_portal.db', check_same_thread=False)
def init_db():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                reg_no TEXT UNIQUE NOT NULL,
                year TEXT NOT NULL,
                photo_path TEXT DEFAULT '',
                advisor_username TEXT NOT NULL,
                department TEXT NOT NULL,
                total_leave INTEGER DEFAULT 0,
                password TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_name TEXT NOT NULL,
                staff_id TEXT UNIQUE NOT NULL,
                photo_path TEXT DEFAULT '',
                admin_username TEXT NOT NULL,
                department TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_name TEXT NOT NULL,
                admin_id TEXT UNIQUE NOT NULL,
                photo_path TEXT DEFAULT '',
                department TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS leave_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_no TEXT NOT NULL,
                student_name TEXT NOT NULL,
                department TEXT NOT NULL,
                year TEXT NOT NULL,
                from_date TEXT NOT NULL,
                to_date TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_days INTEGER NOT NULL,
                category TEXT NOT NULL,
                rejected_by TEXT,
                rejected_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')


        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
    except sqlite3.Error as e:
        print(f"❌ Error initializing database: {e}")

init_db()




@app.route('/api/new_student.html', methods=['POST'])
def add_student():
    try:
        data = request.form
        image = request.files.get('image')  # Get the uploaded image
        print("Received Data:", data)
        print("Received Image:", image)

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # Check if student already exists
        c.execute("SELECT reg_no FROM students WHERE reg_no = ?", (data['regNo'],))
        if c.fetchone():
            return jsonify({'error': 'Student already exists'}), 400

        # Hash the password before storing it
        hashed_password = hash_password(data['password'])

        # Handle image upload
        if image:
            # Create images directory if it doesn't exist
            image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statics', 'images')
            os.makedirs(image_dir, exist_ok=True)

            # Secure the filename and include registration number
            filename = secure_filename(f"{data['regNo']}.jpg")
            image_path = os.path.join(image_dir, filename)
            
            print(f"Saving image to: {image_path}")
            
            # Save the image
            try:
                image.save(image_path)
                print(f"✅ Image saved successfully to {image_path}")
            except Exception as e:
                print(f"❌ Error saving image: {e}")
                filename = "default.jpg"
        else:
            print("❌ No image received")
            filename = "default.jpg"

        # Insert student into the database
        c.execute('''
            INSERT INTO students (student_name, reg_no, year, department, total_leave, password, advisor_username, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'], 
            data['regNo'], 
            data['year'], 
            data['dept'], 
            data.get('total_leave', 0),  
            hashed_password,
            data['advisor_username'],
            filename
        ))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Student added successfully'})

    except Exception as e:
        print(f"❌ Error adding student: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_staff', methods=['POST'])
def add_staff():
    try:
        data = request.json
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO staff (staff_name, staff_id, photo_path, admin_username, department, password)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['staff_name'], data['staff_id'], f"{data['staff_id']}.jpg", data['admin_username'], data['department'], hash_password(data['password'])))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Staff added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/add_admin', methods=['POST'])
def add_admin():
    try:
        data = request.json
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        c.execute('''
            INSERT INTO admin (admin_name, admin_id, photo_path, department, password)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['admin_name'], data['admin_id'], f"{data['admin_id']}.jpg", data['department'], hash_password(data['password'])))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Admin added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route 1: API endpoint for leave submission
# Modified route to handle student leave submission
@app.route('/api/submit_leave', methods=['POST'])
def submit_leave():
    try:
        # Get student info from session
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'Student not authenticated'
            }), 401

        # Get form data from request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data received'
            }), 400

        # Connect to database
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # Get student details including advisor information
        c.execute('''
            SELECT student_name, department, year, advisor_username 
            FROM students 
            WHERE reg_no = ?
        ''', (student_id,))
        
        student_details = c.fetchone()
        if not student_details:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

        student_name, department, year, advisor_username = student_details

        # Calculate total days
        try:
            from_date = datetime.strptime(data['fromDate'], '%Y-%m-%d')
            to_date = datetime.strptime(data['toDate'], '%Y-%m-%d')
            total_days = (to_date - from_date).days + 1
            
            if total_days < 1:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': 'Invalid date range'
                }), 400
        except (ValueError, KeyError) as e:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Invalid date format'
            }), 400

        # Insert leave application
        try:
            c.execute('''
                INSERT INTO leave_applications 
                (reg_no, student_name, department, year, from_date, to_date, 
                 reason, total_days, category, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                student_id,
                student_name,
                department,
                year,
                data['fromDate'],
                data['toDate'],
                data['reason'],
                total_days,
                data['category'],
                'pending'
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Leave application submitted successfully',
                'data': {
                    'studentName': student_name,
                    'department': department,
                    'year': year,
                    'totalDays': total_days,
                    'advisorUsername': advisor_username
                }
            })

        except sqlite3.Error as e:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(e)}'
            }), 500

    except Exception as e:
        print(f"Error submitting leave application: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# Add a route to get current student details
@app.route('/api/get_student_details')
def get_student_details():
    try:
        # Get student ID from session
        student_id = session.get('user_id')
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'Not authenticated'
            }), 401

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        c.execute('''
            SELECT student_name, reg_no, department, year, photo_path
            FROM students
            WHERE reg_no = ?
        ''', (student_id,))
        
        student = c.fetchone()
        conn.close()
        
        if student:
            return jsonify({
                'success': True,
                'data': {
                    'name': student[0],
                    'regNo': student[1],
                    'department': student[2],
                    'year': student[3],
                    'photo': get_student_image(student[1])
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404

    except Exception as e:
        print(f"Error fetching student details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
# # Route 2: Student leave page route
# @app.route('/student/student_leave.html')
# def student_leave():
#     if request.args:
#         try:
#             # Calculate total days
#             from_date = datetime.strptime(request.args.get('fromDate'), '%Y-%m-%d')
#             to_date = datetime.strptime(request.args.get('toDate'), '%Y-%m-%d')
#             total_days = (to_date - from_date).days + 1
            
#             conn = sqlite3.connect('leave_portal.db')
#             c = conn.cursor()
            
#             # Get category from request args
#             category = request.args.get('category')
            
#             # Insert the leave application with the correct category
#             c.execute('''
#                 INSERT INTO leave_applications 
#                 (reg_no, student_name, department, year, from_date, to_date, 
#                  reason, total_days, category, status)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             ''', (
#                 request.args.get('regNo'),
#                 request.args.get('name'),
#                 request.args.get('dept'),
#                 request.args.get('year'),
#                 request.args.get('fromDate'),
#                 request.args.get('toDate'),
#                 request.args.get('reason'),
#                 total_days,
#                 category,  # Use the category from request
#                 'pending'
#             ))
            
#             conn.commit()
#             conn.close()
            
#             return jsonify({'success': True, 'message': 'Leave application submitted successfully'})
            
#         except Exception as e:
#             print(f"Error storing leave application: {e}")
#             return jsonify({'error': str(e)}), 500
    
#     return render_template('student_leave.html')


def calculate_days(from_date, to_date):
    start = datetime.strptime(from_date, '%Y-%m-%d')
    end = datetime.strptime(to_date, '%Y-%m-%d')
    return (end - start).days + 1


@app.route('/api/get_student_approved_applications')
def get_student_approved_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        reg_no = session.get('user_id')
        if not reg_no:
            print("⛔ ERROR: Student not logged in or reg_no missing!")
            return jsonify({'error': 'Unauthorized access'}), 403

        print(f"📌 Fetching approved applications for Student with Reg No: {reg_no}")

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
            'photo': get_student_image(app[2])  # Using reg_no for image
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
        new_status = data.get('status')
        role = data.get('role')
        user_id = session.get('user_id')

        if not leave_id or not new_status or not role:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        print(f"📌 Updating leave {leave_id} to status: {new_status} by {role}")

        if role == 'staff':
            if new_status == 'staff_approved':
                # Staff approved -> Send to Admin
                c.execute('''
                    UPDATE leave_applications 
                    SET status = 'staff_approved'
                    WHERE id = ? AND status = 'pending'
                ''', (leave_id,))
                print(f"✅ Leave {leave_id} approved by staff, forwarded to admin")
            elif new_status == 'rejected':
                # Staff rejected
                c.execute('''
                    UPDATE leave_applications 
                    SET status = 'rejected',
                        rejected_by = ?,
                        rejected_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                ''', (user_id, leave_id))
                print(f"❌ Leave {leave_id} rejected by staff")

        elif role == 'admin':
            if new_status == 'approved':
                # Admin approved
                c.execute('''
                    UPDATE leave_applications 
                    SET status = 'approved'
                    WHERE id = ? AND status = 'staff_approved'
                ''', (leave_id,))
                print(f"✅ Leave {leave_id} fully approved by admin")
            elif new_status == 'rejected':
                # Admin rejected
                c.execute('''
                    UPDATE leave_applications 
                    SET status = 'rejected',
                        rejected_by = ?,
                        rejected_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND (status = 'pending' OR status = 'staff_approved')
                ''', (user_id, leave_id))
                print(f"❌ Leave {leave_id} rejected by admin")

        # Check if any rows were affected
        if c.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'No leave application was updated. It may have already been processed.'
            }), 400

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Leave application {new_status} successfully'
        })

    except Exception as e:
        print(f"❌ ERROR updating leave status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def init_default_users():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        # Add default staff user if not exists
        c.execute("SELECT COUNT(*) FROM staff WHERE staff_id = ?", ('staff001',))
        if c.fetchone()[0] == 0:
            c.execute('''
                INSERT INTO staff (staff_name, staff_id, photo_path, admin_username, department, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('Default Staff', 'staff001', 'default.jpg', 'admin001', 'IT', hash_password('staff123')))
            print("✅ Default staff user added")
            
        # Add default admin user if not exists
        c.execute("SELECT COUNT(*) FROM admin WHERE admin_id = ?", ('admin001',))
        if c.fetchone()[0] == 0:
            c.execute('''
                INSERT INTO admin (admin_name, admin_id, photo_path, department, password)
                VALUES (?, ?, ?, ?, ?)
            ''', ('Default Admin', 'admin001', 'default.jpg', 'IT', hash_password('admin123')))
            print("✅ Default admin user added")
            
        # Add default student user if not exists
        c.execute("SELECT COUNT(*) FROM students WHERE reg_no = ?", ('student001',))
        if c.fetchone()[0] == 0:
            c.execute('''
                INSERT INTO students (student_name, reg_no, year, photo_path, advisor_username, department, password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('Default Student', 'student001', '2025', 'default.jpg', 'staff001', 'IT', hash_password('student123')))
            print("✅ Default student user added")
            
        conn.commit()
        conn.close()
        print("✅ Default users initialized")
    except Exception as e:
        print(f"❌ Error initializing default users: {e}")

# Add route to handle student leave application submission

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(32)
    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt + hash_obj

def verify_password(stored_password, provided_password):
    # Remove debug print
    # print(hash_password("admin123"))

    if not stored_password:
        return False  # Ensure stored password is valid

    try:
        # Convert stored HEX password back to bytes
        stored_password_bytes = bytes.fromhex(stored_password)
        
        # Check if the stored password follows the expected format (salt + hash)
        if len(stored_password_bytes) >= 32:
            salt = stored_password_bytes[:32]  # Extract salt
            stored_hash = stored_password_bytes[32:]  # Extract hash
            
            # Hash the provided password with the same salt
            new_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), salt, 100000)
            
            return stored_hash == new_hash  # Compare hashes
        else:
            # Fallback for passwords stored in different format
            # This is a simpler check that might work for admin passwords
            simple_hash = hashlib.sha256(provided_password.encode()).hexdigest()
            return simple_hash == stored_password
    except Exception as e:
        print(f"Error in password verification: {e}")
        return False

def verify_admin_password(stored_hex, provided_password):
    """Special password verification for admin accounts"""
    try:
        # Admin passwords might be using a simpler hashing scheme
        # Try direct SHA-256 comparison first
        simple_hash = hashlib.sha256(provided_password.encode()).hexdigest()
        if simple_hash.lower() == stored_hex.lower():
            return True
            
        # If that doesn't work, try with the static salt from the 'users' dictionary
        static_salt = salt  # Use the global salt variable defined above
        test_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode(), static_salt, 100000)
        test_hex = (static_salt + test_hash).hex()
        if test_hex.lower() == stored_hex.lower():
            return True
            
        # As a last resort, try a hard-coded comparison for admin001/admin123
        if stored_hex == '263BF9C89AED4EC51E1117C81EF7E1EE72DCB3B192255506A2E3F50D083A3F6F' and provided_password == 'admin123':
            return True
            
        return False
    except Exception as e:
        print(f"Error in admin password verification: {e}")
        return False

# Store pre-computed hashed passwords
salt = os.urandom(32)
# users = {
#     'students': {  # Fix: Use singular form for all user types
#         'student001': hash_password('student123', salt)},
#     'staff': {
#         'staff001': hash_password('staff123', salt),
#         'staff002': hash_password('staff123', salt),
#     },
#     'admin': {
#         'admin001': hash_password('admin123', salt),
#         'admin002': hash_password('admin123', salt)
#     }
# }

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user_type = data.get('userType', '').lower().strip()
    user_id = data.get('username', '').lower().strip()
    password = data.get('password', '').strip()

    print(f"📌 Received userType: {user_type}")
    print(f"📌 Received username: {user_id}")

    # Try database authentication
    conn = sqlite3.connect('leave_portal.db')
    c = conn.cursor()
    
    if user_type == 'student':
        c.execute("SELECT reg_no, HEX(password) FROM students WHERE reg_no = ?", (user_id,))
    elif user_type == 'staff':
        c.execute("SELECT staff_id, HEX(password) FROM staff WHERE staff_id = ?", (user_id,))
    elif user_type == 'admin':
        c.execute("SELECT admin_id, HEX(password) FROM admin WHERE UPPER(admin_id) = ?", (user_id.upper(),))
    else:
        conn.close()
        return jsonify({'error': 'Invalid user type'}), 400
    
    user = c.fetchone()
    conn.close()
    
    # Database authentication
    if user:
        stored_password_hex = user[1]
        print(f"🔑 Stored password HEX: {stored_password_hex}")

        # Use dedicated verification function for admin users
        if user_type == 'admin':
            password_valid = verify_admin_password(stored_password_hex, password)
        else:
            password_valid = verify_password(stored_password_hex, password)

        if password_valid:
            print(f"✅ Login successful for {user_id}")
            session.permanent = True
            session['user_id'] = user_id
            session['user_type'] = user_type
            return jsonify({'success': True, 'redirect': f'/{user_type}/dashboard'})
    
    print(f"❌ Authentication failed for {user_id}")
    return jsonify({'error': 'Invalid credentials'}), 401


def fix_admin_password():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        # Generate properly formatted password for admin123
        proper_password = hash_password('admin123')
        
        # Update all admin passwords
        c.execute('UPDATE admin SET password = ?', (proper_password,))
        
        conn.commit()
        conn.close()
        print("✅ Admin passwords updated to proper format")
        return True
    except Exception as e:
        print(f"❌ Error fixing admin passwords: {e}")
        return False

def login_required(user_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('user_id') is None:
                return redirect('/login')
            
            # Fix: Check against singular forms for all user types
            stored_type = session.get('user_type', '')
            # Remove 's' if it's plural in the session
            if stored_type.endswith('s') and user_type == stored_type[:-1]:
                return f(*args, **kwargs)
            elif stored_type == user_type:
                return f(*args, **kwargs)
            
            return redirect('/login')
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



def setup_image_directory():
    """Ensure the images directory exists"""
    image_dir = Path('statics/images')
    image_dir.mkdir(parents=True, exist_ok=True)
    return image_dir

def get_student_image(reg_no):
    """
    Get the student's profile image path based on their registration number.
    Checks for multiple image formats and falls back to default if none found.
    """
    if not reg_no:
        return "/statics/images/default.jpg"
    
    # Define supported image formats
    supported_formats = ['.jpg', '.jpeg', '.png']
    
    # Get absolute path to the images directory
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statics', 'images')
    
    # Check for image in different formats
    for format in supported_formats:
        image_filename = f"{reg_no}{format}"
        image_path = os.path.join(base_path, image_filename)
        
        if os.path.exists(image_path):
            # Return web-accessible path
            return f"/statics/images/{image_filename}"
    
    # Log when falling back to default
    print(f"No specific image found for reg_no: {reg_no}, using default")
    return "/statics/images/default.jpg"

def get_db_connection():
    conn = sqlite3.connect('leave_portal.db')
    conn.row_factory = sqlite3.Row
    return conn

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
            'name': app[2],
            'studentId': app[1],
            'department': app[3],
            'year': app[4],
            'fromDate': app[5],
            'toDate': app[6],
            'reason': app[7],
            'status': app[8],
            'totalLeaveDays': app[9],
            'category': app[10],
            'photo': get_student_image(app[1])  # Using reg_no for image
        } for app in applications])

    except Exception as e:
        print(f"❌ ERROR fetching leave applications: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/student/rejected.html')
def rejected_leave():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        
        # Get student ID from session
        student_id = session.get('user_id')
        
        # Fetch rejected applications from leave_applications table
        c.execute('''
            SELECT id, student_name, reg_no, department, year, 
                   from_date, to_date, reason, total_days, category,
                   rejected_by, datetime(rejected_at, 'localtime') as rejected_time
            FROM leave_applications 
            WHERE reg_no = ? AND status = 'rejected'
            ORDER BY rejected_at DESC
        ''', (student_id,))
        
        rejected_leaves = c.fetchall()
        conn.close()
        
        # Transform database results into template-friendly format
        leaves = [{
            'id': leave[0],
            'name': leave[1],
            'studentId': leave[2],
            'department': leave[3],
            'year': leave[4],
            'fromDate': leave[5],
            'toDate': leave[6],
            'reason': leave[7],
            'totalLeaveDays': leave[8],
            'category': leave[9],
            'rejectedBy': leave[10] or 'Unknown',
            'rejectedAt': leave[11],
            'photo': get_student_image(leave[2])  # Add student photo
        } for leave in rejected_leaves]
        
        return render_template('rejected.html', leaves=leaves)
    except Exception as e:
        print(f"❌ Error fetching rejected leaves: {e}")
        return str(e)

@app.route('/api/get_rejected_applications')
def get_rejected_applications():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # Get student ID from session
        student_id = session.get('user_id')
        
        print(f"📌 Fetching rejected applications for student: {student_id}")

        # Fetch rejected applications
        c.execute('''
            SELECT id, student_name, reg_no, department, year, 
                   from_date, to_date, reason, total_days, category,
                   rejected_by, datetime(rejected_at, 'localtime') as rejected_time
            FROM leave_applications 
            WHERE reg_no = ? AND status = 'rejected'
            ORDER BY rejected_at DESC
        ''', (student_id,))

        applications = c.fetchall()
        conn.close()

        if applications:
            print(f"✅ Found {len(applications)} rejected applications")
        else:
            print("❌ No rejected applications found")

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
            'rejectedBy': app[10] or 'Unknown',
            'rejectedAt': app[11],
            'photo': get_student_image(app[2])
        } for app in applications])

    except Exception as e:
        print(f"❌ Error in get_rejected_applications: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear_rejected_history', methods=['POST'])
def clear_rejected_history():
    try:
        student_reg_no = session.get('user_id')  # Get logged-in student's reg_no
        if not student_reg_no:
            return jsonify({"success": False, "error": "User not authenticated"})

        # Delete only rejected applications
        db.execute("DELETE FROM leave_applications WHERE reg_no = ? AND status = 'rejected'", (student_reg_no,))
        db.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/clear_approved_history', methods=['POST'])
def clear_approved_history():
    try:
        student_reg_no = session.get('user_id')  # Get logged-in student's reg_no
        if not student_reg_no:
            return jsonify({"success": False, "error": "User not authenticated"})

        # Delete only approved applications
        db.execute("DELETE FROM leave_applications WHERE reg_no = ? AND status = 'approved'", (student_reg_no,))
        db.commit()

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


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
            'photo': get_student_image(app[2])
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
@login_required('student')
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
def add_students():
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
            SELECT id, student_name, reg_no, department, year, 
                   from_date, to_date, reason, total_days, category, status
            FROM leave_applications 
            WHERE reg_no = ? AND status = 'approved'
            ORDER BY created_at DESC
        ''', (student_id,))
        
        approved_leaves = c.fetchall()
        conn.close()
        
        # Convert to list of dictionaries for template
        leaves = [{
            'id': leave[0],
            'name': leave[1],
            'studentId': leave[2],
            'department': leave[3],
            'year': leave[4],
            'fromDate': leave[5],
            'toDate': leave[6],
            'reason': leave[7],
            'totalLeaveDays': leave[8],
            'category': leave[9],
            'status': leave[10],
            'photo': get_student_image(leave[2])
        } for leave in approved_leaves]
        
        return render_template('approved.html', leaves=leaves)
    except Exception as e:
        print(f"❌ Error fetching approved leaves: {e}")
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

@app.route('/static/images/default.jpg')
def image():
    return send_from_directory('statics/images', 'pic.jpg')

@app.route('/statics/images/default.jpg')
def images():
    return send_from_directory('statics/images', 'default.jpg')

def setup_image_directory():
    """Ensure the images directory exists and has proper permissions"""
    try:
        image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statics', 'images')
        os.makedirs(image_dir, exist_ok=True)
        print(f"✅ Image directory setup complete at: {image_dir}")
        return image_dir
    except Exception as e:
        print(f"❌ Error setting up image directory: {e}")
        return None

@app.route('/statics/images/<path:filename>')
def serve_image(filename):
    """
    Serve images from the statics/images directory with proper error handling
    """
    try:
        image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'statics', 'images')
        if os.path.exists(os.path.join(image_dir, filename)):
            return send_from_directory('statics/images', filename)
        else:
            print(f"❌ Image not found: {filename}, serving default")
            return send_from_directory('statics/images', 'default.jpg')
    except Exception as e:
        print(f"❌ Error serving image {filename}: {e}")
        return send_from_directory('statics/images', 'default.jpg')

# Add route for static images
@app.route('/static/images/<path:filename>')
def serve_static_image(filename):
    """
    Alternative route for serving images from static directory
    """
    return send_from_directory('statics/images', filename)

# Initialize image directory on startup
setup_image_directory()

if __name__ == '__main__':
    setup_directories()
    init_db()  # Your existing database initialization
    init_default_users()  # Add this line to create default users
    app.run(host='0.0.0.0', port="5000", debug=True)