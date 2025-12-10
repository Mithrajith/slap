# 🎓 Student Leave Application Portal (SLAP)

## 📖 Project Domain & Real-World Problem

### **Domain**
**Education Technology (EdTech) & Institutional Administration**

### **The Problem**
In many educational institutions, the process of applying for and approving student leave is often manual, paper-based, or fragmented across emails and informal messages. This leads to:
- **Inefficiency:** Physical forms getting lost or delayed.
- **Lack of Transparency:** Students don't know the status of their request.
- **Administrative Burden:** Faculty and admins struggle to track attendance records and leave history.
- **Security Risks:** Lack of proper authentication and audit trails for approvals.

### **The Solution**
**SLAP (Student Leave Application Portal)** is a secure, digitalized, and automated workflow system designed to streamline the leave management process. It provides a centralized platform for students to apply for leave and for faculty/administrators to review and approve requests in a multi-tier hierarchy.

### **Target Users**
1.  **Students:** Apply for leave, track status, view history.
2.  **Staff (Faculty/Advisors):** First-level review and approval/rejection.
3.  **Administrators:** Final authority for approval, record keeping, and generating official acceptance letters.

---

## 🚀 High-Level Project Overview

SLAP is a production-ready web application built with **Flask** that digitizes the entire lifecycle of a leave request. It enforces a strict security model and a multi-stage approval workflow.

### **Core Objectives**
- **Digitization:** Eliminate paper trails.
- **Security:** Ensure data integrity and prevent unauthorized access (OWASP Top 10 compliance).
- **Automation:** Automate status updates and document generation.
- **Usability:** Provide clean, role-specific dashboards.

### **Key Capabilities**
- **Role-Based Access Control (RBAC):** Distinct portals for Students, Staff, and Admins.
- **Multi-Tier Approval Workflow:** Requests flow from Student → Staff → Admin.
- **Automated PDF Generation:** Generates official acceptance letters upon final approval.
- **Security-First Architecture:** Includes CSRF protection, secure session management, and input sanitization.

---

## 🏗️ System Architecture & Technical Workflow

The system follows a **Model-View-Controller (MVC)** architectural pattern, implemented using a modular Flask structure.

### **End-to-End Data Flow**
1.  **Request Initiation:** Student submits a leave form (dates, reason, category) via the frontend.
2.  **Validation & Storage:** Backend sanitizes input, validates dates, and stores the request in SQLite with a `pending` status.
3.  **Level 1 Processing (Staff):** Staff logs in, views `pending` requests, and approves or rejects. Status updates to `staff_approved` or `rejected`.
4.  **Level 2 Processing (Admin):** Admin views `staff_approved` requests. Upon final approval, the system generates a PDF acceptance letter.
5.  **Notification:** Student dashboard updates with the final status and download link for the letter.

### **Major Components**
- **Client:** HTML5/CSS3/JS frontend serving distinct dashboards.
- **Web Server:** Flask application handling routing, authentication, and business logic.
- **Database:** SQLite (relational) storing users, roles, and application records.
- **Security Layer:** Middleware for headers, CSRF validation, and session handling.

---

## 🛠️ Tech Stack Breakdown

### **Frontend**
- **Languages:** HTML5, CSS3, JavaScript (ES6+)
- **Templating Engine:** Jinja2 (Server-side rendering)
- **Styling:** Custom CSS with responsive design for different user roles.

### **Backend**
- **Framework:** Flask 3.0.0 (Python)
- **WSGI Utility:** Werkzeug
- **Session Management:** Flask-Session (Server-side filesystem sessions)
- **CORS:** Flask-CORS for API security

### **Database**
- **Engine:** SQLite (Development/Production-ready for low-mid traffic)
- **ORM/Driver:** Native `sqlite3` with custom context managers for connection pooling.

### **DevOps & Tooling**
- **Containerization:** Docker
- **Testing:** Pytest, Flake8
- **Environment:** Python-dotenv for configuration management

---

## ✨ Core Features

### **Functional Features**
- **Smart Dashboarding:**
    - **Student:** Apply for leave, view history, download approved letters.
    - **Staff:** Bulk view pending requests, quick approve/reject actions.
    - **Admin:** Oversight of all leaves, final approval authority, staff management.
- **Leave Calculator:** Automatically calculates total leave days excluding weekends/holidays (logic extensible).
- **Document Generation:** Dynamic creation of PDF acceptance letters using `ReportLab`.

### **Internal System Features**
- **Security Hardening:**
    - **CSRF Protection:** Token-based verification for all state-changing requests.
    - **XSS Prevention:** Strict Content Security Policy (CSP) and input sanitization.
    - **Secure Headers:** HSTS, X-Frame-Options, X-Content-Type-Options.
- **Scalable Session Management:** Server-side sessions to prevent cookie tampering.
- **Error Handling:** Custom 404, 500, and 403 error pages.

---

## 🧠 Algorithms & Techniques Used

### **1. Security Architecture (Cryptography)**
- **Password Hashing:** Uses **PBKDF2-HMAC-SHA256** with a unique salt for every user. This renders rainbow table attacks ineffective.
- **Session Security:** Implements session regeneration on login to prevent **Session Fixation** attacks.

### **2. State Machine Workflow**
The leave application follows a strict state transition logic to ensure integrity:
- `pending` → `staff_approved` (Only by Staff)
- `pending` → `rejected` (By Staff)
- `staff_approved` → `approved` (Only by Admin)
- `staff_approved` → `rejected` (By Admin)
- *Invalid transitions (e.g., Student approving their own leave) are blocked at the API level.*

### **3. Database Optimization**
- **Connection Pooling Pattern:** Uses Python context managers (`with self.get_connection()`) to ensure connections are always closed, preventing leaks.
- **Indexing:** SQL indices on `reg_no`, `status`, and `staff_id` to optimize lookup speeds for dashboards.

---

## ⚙️ Installation & Setup

### **Prerequisites**
- Python 3.10+
- Docker (Optional)

### **Step-by-Step Setup**

#### **1. Clone the Repository**
```bash
git clone https://github.com/yourusername/slap.git
cd slap
```

#### **2. Environment Configuration**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your_super_secure_random_string
FLASK_ENV=development
```

#### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

#### **4. Initialize Database**
The application automatically initializes the SQLite database and tables on the first run via `models.py`.

#### **5. Run the Application**
```bash
python app_refactored.py
```
Access the portal at `http://localhost:7000`.

### **Docker Setup**
```bash
docker build -t leave-portal .
docker run -p 7000:7000 leave-portal
```

---

## 🔍 How the Project Works (Internals)

### **1. Authentication Flow**
- User submits credentials via AJAX.
- Backend retrieves the user's salt and hash.
- Re-computes hash of input password.
- If match: Session is regenerated, user ID/Role stored in server-side session file.

### **2. Leave Submission & Processing**
- **Input:** JSON payload `{fromDate, toDate, reason, category}`.
- **Validation:** `ValidationUtils` checks date logic (Start < End) and sanitizes text.
- **Persistence:** `LeaveApplicationModel` inserts row with `status='pending'`.

### **3. Approval Logic**
- Staff dashboard polls `/api/get_pending_applications`.
- Staff action triggers `update_leave_status`.
- Backend verifies `session['user_type'] == 'staff'` before committing change.

---

## 💡 Use Cases

1.  **Medical Leave:** A student falls ill, uploads a medical certificate (future scope), and applies. The advisor approves it, and the admin finalizes it for attendance records.
2.  **On-Duty (OD):** A student attending a hackathon applies for OD. The system tracks this separately from casual leave.
3.  **Emergency:** Quick approval workflow allows staff to see urgent requests immediately.

---

## 🔮 Future Scope & Improvements

-   **Email Notifications:** Integrate SMTP to send email alerts on status changes.
-   **File Attachments:** Allow students to upload medical certificates or event tickets securely.
-   **Calendar Integration:** Sync approved leaves with Google/Outlook calendars.
-   **Analytics Dashboard:** Visual graphs for admins to see leave trends (e.g., "Peak leave months").
-   **Migration to PostgreSQL:** For high-concurrency production environments.

---

## 🤝 Contribution

Contributions are welcome! Please fork the repository and submit a Pull Request. Ensure all security tests pass before submission.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
