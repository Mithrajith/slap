from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from werkzeug.utils import secure_filename
import os
import hashlib

app = Flask(__name__)
CORS(app)

# Create folder if not exists
os.makedirs(os.path.join('statics', 'images'), exist_ok=True)

# Staff Management Routes
@app.route('/api/staff/add', methods=['POST'])
def add_staff_member():
    try:
        data = request.form
        image = request.files.get('image')

        # Validate required fields
        required_fields = ['staff_name', 'staff_id', 'admin_username', 'department', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # Check if staff already exists
        c.execute("SELECT staff_id FROM staff WHERE staff_id = ?", (data['staff_id'],))
        if c.fetchone():
            return jsonify({'error': 'Staff ID already exists'}), 400

        # Handle image upload
        filename = "default.jpg"
        if image:
            filename = secure_filename(f"{data['staff_id']}.jpg")
            image_path = os.path.join('statics', 'images', filename)
            image.save(image_path)

        # Hash password
        salt = os.urandom(32)
        hashed_password = hashlib.pbkdf2_hmac(
            'sha256',
            data['password'].encode(),
            salt,
            100000
        ).hex()

        # Insert staff member
        c.execute('''
            INSERT INTO staff (
                staff_name, 
                staff_id, 
                photo_path, 
                admin_username, 
                department, 
                password
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['staff_name'],
            data['staff_id'],
            filename,
            data['admin_username'],
            data['department'],
            hashed_password
        ))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Staff member added successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin Management Routes
@app.route('/api/admin/add', methods=['POST'])
def add_admin_member():
    try:
        data = request.form
        image = request.files.get('image')

        # Validate required fields
        required_fields = ['admin_name', 'admin_id', 'department', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()

        # Check if admin already exists
        c.execute("SELECT admin_id FROM admin WHERE admin_id = ?", (data['admin_id'],))
        if c.fetchone():
            return jsonify({'error': 'Admin ID already exists'}), 400

        # Handle image upload
        filename = "default.jpg"
        if image:
            filename = secure_filename(f"{data['admin_id']}.png")
            image_path = os.path.join('statics', 'images', filename)
            image.save(image_path)

        # Hash password
        salt = os.urandom(32)
        hashed_password = hashlib.pbkdf2_hmac(
            'sha256',
            data['password'].encode(),
            salt,
            100000
        ).hex()

        # Insert admin member
        c.execute('''
            INSERT INTO admin (
                admin_name, 
                admin_id, 
                photo_path, 
                department, 
                password
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            data['admin_name'],
            data['admin_id'],
            filename,
            data['department'],
            hashed_password
        ))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Admin member added successfully'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get Staff List
@app.route('/api/staff/list', methods=['GET'])
def get_staff_list():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        c.execute("SELECT staff_name, staff_id, department FROM staff")
        staff = c.fetchall()
        conn.close()

        return jsonify([{
            'name': s[0],
            'id': s[1],
            'department': s[2]
        } for s in staff])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get Admin List
@app.route('/api/admin/list', methods=['GET'])
def get_admin_list():
    try:
        conn = sqlite3.connect('leave_portal.db')
        c = conn.cursor()
        c.execute("SELECT admin_name, admin_id, department FROM admin")
        admins = c.fetchall()
        conn.close()

        return jsonify([{
            'name': a[0],
            'id': a[1],
            'department': a[2]
        } for a in admins])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# UI Routes
@app.route('/')
def serve_add_staff():
    return render_template('add_admin.html')

@app.route('/admin/add_admin')
def serve_add_admin():
    return render_template('add_admin.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
