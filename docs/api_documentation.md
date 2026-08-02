# API Documentation

Complete API specification for the Marks Management System, including Phase 10 additions for Global Search, Settings management, Activity Log audits, and standardized Export configurations.

---

## 🔐 Authorization & Authentication

- **Session Cookies**: Managed natively.
- **RBAC**: Checks `session['admin_id']`, `session['teacher_id']`, and `session['student_id']` values to enforce role constraints.

---

## 📜 Search & Filter API (Phase 10)

### 1. Global Search Endpoint
- **Endpoint**: `GET /api/search`
- **Authorization**: Logged-in session required (Admin/Teacher/Student).
- **Query Parameters**:
  - `q` (str): Search string (minimum 2 characters).
- **Response Schema** (`application/json`):
  ```json
  {
    "students": [
      {
        "id": 1,
        "name": "Sunil Kumar",
        "roll_no": "24AK1A30F1",
        "batch": "2024 Intake",
        "semester": 1,
        "email": "sunil@college.edu"
      }
    ],
    "teachers": [
      {
        "id": 1,
        "name": "Dr. Ravi Sharma",
        "email": "ravi@college.edu",
        "subjects": ["Data Structures"]
      }
    ],
    "subjects": [
      {
        "id": 1,
        "code": "CS101",
        "name": "Data Structures",
        "credits": 4,
        "teacher": "Dr. Ravi Sharma",
        "status": "APPROVED"
      }
    ]
  }
  ```

---

## ⚙️ Settings & Audits API (Phase 10)

### 1. Update System Settings
- **Endpoint**: `POST /admin/settings`
- **Authorization**: Admin Only (`session['admin_id']`)
- **Payload** (`application/x-www-form-urlencoded`):
  - `institution_name` (str)
  - `academic_years` (str)
  - `grading_rules` (str)
  - `memo_footer` (str)
  - `export_naming` (str)
- **Response**: Redirects to `/admin/dashboard#settings` with Flash status feedback.

### 2. Fetch System Activity Logs
- **Endpoint**: `GET /api/admin/activity`
- **Authorization**: Admin Only (`session['admin_id']`)
- **Response Schema** (`application/json`):
  ```json
  [
    {
      "id": 1,
      "username": "admin",
      "action": "Logged in to Admin Portal",
      "timestamp": "2026-08-02 22:50:11",
      "status": "SUCCESS"
    }
  ]
  ```

---

## 📤 Standardized Export APIs (Phase 10)

All Excel and CSV exports support the `format` query parameter and generated metadata headers (User info and Timestamp).

### 1. Export Student Results
- **Endpoint**: `GET /admin/export_results`
- **Authorization**: Admin Only
- **Query Parameters**:
  - `batch` (str, optional): Batch filter.
  - `format` (str, optional): `excel` (default) or `csv`.

### 2. Export Tabulation Register
- **Endpoint**: `GET /admin/tabulation_register/export`
- **Authorization**: Admin Only
- **Query Parameters**: Same filters as TR generation, plus `format` (`excel` or `csv`).
