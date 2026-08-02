# Marks Management System - LLM Context & Architecture

This document serves as a complete machine-readable context file describing the architecture, database schema, design decisions, and core workflows of the Marks Management System. It is designed to help LLMs quickly understand the system for debugging, feature additions, or refactoring.

---

## 🛠️ Technology Stack
- **Framework:** Flask (Python)
- **Database:** SQLite with SQLAlchemy ORM
- **Processing:** Pandas (for parsing incoming Excel uploads)
- **Formatting & Reports:** Openpyxl (Excel sheet building and formatting)
- **Mailer:** Flask-Mail (daemon thread asynchronous dispatch)
- **Config & Env:** Python-dotenv for variables

---

## 🗃️ Database Schema & Relationships (SQLAlchemy)

### 1. `Admin`
- Stores administrative credentials for overall system management.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `username` (String(50), Unique, Not Null)
  - `password_hash` (String(255), Not Null)

### 2. `Teacher`
- Represents faculty members who manage grades for assigned subjects.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `name` (String(100), Not Null)
  - `email` (String(120), Unique, Not Null)
  - `password_hash` (String(255), Not Null)
- **Relationships:**
  - `subjects`: One-to-many relationship with `Subject` (mapped by backref `teacher`).

### 3. `Student`
- Represents students enrolled in the system.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `roll_no` (String(20), Unique, Not Null)
  - `name` (String(100), Not Null)
  - `email` (String(120), Unique, Not Null)
  - `aadhar_last4` (String(4), Not Null)
  - `batch` (String(20), Default: "2024 Intake")
  - `semester` (Integer, Default: 1)
- **Relationships:**
  - `marks`: One-to-many relationship with `Mark` (mapped by backref `student`).
  - `results`: One-to-one relationship with `Result` (mapped by backref `student`).

### 4. `Subject`
- Course details managed by teachers and approved by the admin.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `code` (String(20), Unique, Not Null)
  - `name` (String(100), Not Null)
  - `credits` (Integer, Not Null)
  - `teacher_id` (Integer, ForeignKey('teacher.id'))
  - `processing_status` (String(20), Default: 'NOT_PROCESSED') 
    - *Status Values:* `NOT_PROCESSED`, `PROCESSING`, `DRAFT`, `SUBMITTED`, `REJECTED`, `APPROVED`
  - `rejection_reason` (String(255), Nullable)
- **Relationships:**
  - `marks`: One-to-many relationship with `Mark` (mapped by backref `subject`).

### 5. `Mark`
- Student performance details in a specific subject.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `student_id` (Integer, ForeignKey('student.id'))
  - `subject_id` (Integer, ForeignKey('subject.id'))
  - `internal` (Float, Default: 0.0, Max: 30.0)
  - `external` (Float, Default: 0.0, Max: 70.0)
  - `total` (Float, Default: 0.0, Max: 100.0)
  - `grade` (String(2), Default: 'F')
  - `grade_point` (Integer, Default: 0)
  - `external_breakup` (Text, Stores JSON string of detailed question-wise marks)

### 6. `Result`
- Overall GPA calculation outcomes for a student's semester.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `student_id` (Integer, ForeignKey('student.id'))
  - `sgpa` (Float, Default: 0.0)
  - `cgpa` (Float, Default: 0.0)
  - `semester` (Integer, Default: 1)
  - `is_released` (Boolean, Default: False)

### 7. `AnonymousMarkData`
- Temporary storage for anonymized external exams before student mapping is matched.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `subject_id` (Integer, ForeignKey('subject.id'))
  - `unique_id` (String(50), Not Null)
  - `marks_data` (Text, JSON string storing question-wise marks)
  - `external_total` (Float, Default: 0.0)
  - `status` (String(20), Default: 'VALID')
  - `upload_version` (Integer, Default: 1)
- **Constraints:**
  - Unique constraint on (`unique_id`, `subject_id`).

### 8. `StudentMapping`
- Maps anonymous code names back to student Roll Numbers.
- **Fields:**
  - `id` (Integer, Primary Key)
  - `subject_id` (Integer, ForeignKey('subject.id'))
  - `unique_id` (String(50), Not Null)
  - `roll_number` (String(20), ForeignKey('student.roll_no'))
  - `upload_version` (Integer, Default: 1)
- **Constraints:**
  - Unique constraint on (`unique_id`, `subject_id`).

---

## 📈 Key Operations & Workflows

### 1. Ingestion Pipeline (3-Stage Validation)
1. **Upload External Marks (`/teacher/upload_external`):** Takes a spreadsheet containing anonymous `Unique_ID`s and question marks columns (prefixed with `Q`). Rejects if columns are missing or if fields are empty. Saves to `AnonymousMarkData`.
2. **Upload Student Mappings (`/teacher/upload_mapping`):** Takes a spreadsheet correlating `Unique_ID` with `Roll_Number`. Saves to `StudentMapping`.
3. **Upload Internal Marks (`/teacher/upload_internal`):** Takes a spreadsheet correlating `Roll_Number` with `Internal_Marks` (max 30). Updates `Mark` records directly.

### 2. Matching and Grading Loop (`/teacher/process_results/<subject_id>`)
1. Fetches all mappings and external marks for the subject.
2. Checks that every `Unique_ID` exists in the mapping registry. If anomalies exist, stores errors in the session and raises a validation error block.
3. Computes final totals: `internal + external`.
4. Calculates grades based on the 100-mark boundary mapping:
   - $\ge 90$: **A+** (GP: 10)
   - $\ge 80$: **A** (GP: 9)
   - $\ge 70$: **B** (GP: 8)
   - $\ge 60$: **C** (GP: 7)
   - $\ge 50$: **D** (GP: 6)
   - $\ge 40$: **E** (GP: 5)
   - $< 40$: **F** (GP: 0)
5. Updates/Creates student `Result` records, marking `is_released = False` and recalculating semester SGPA.
6. Changes Subject status to `DRAFT`.

### 3. Submission approval workflow
1. Teachers transition subject status to `SUBMITTED` (`/teacher/submit_results/<id>`).
2. Admin reviews the entries via the admin inbox.
3. Admin triggers `/admin/approve_subject/<id>` to lock the marks or `/admin/reject_subject/<id>` with a string reason that resets the subject's processing status back to `REJECTED` and exposes the reason to the teacher.

### 4. Background Email Dispatch
- Located in `mail_sender.py` $\rightarrow$ `send_all_results_email(app, mail, students)`.
- Reconstructs student models to pure Python dictionaries to avoid detached session issues.
- Spawns a background thread running as a daemon (`threading.Thread`).
- Sends custom HTML-structured results to the student's email with a 1-second throttle delay to avoid spam filters.

---

## 📂 Project Navigation Rules
- **Route Handlers / Middleware:** Located in [app.py](file:///d:/My_Projects/Marks%20Management%20System/marks-management/app.py)
- **Database Models:** Located in [models.py](file:///d:/My_Projects/Marks%20Management%20System/marks-management/models.py)
- **Background Tasks:** Located in [mail_sender.py](file:///d:/My_Projects/Marks%20Management%20System/marks-management/mail_sender.py)
- **Mock data generation / Seed script:** Located in [simulate_excel.py](file:///d:/My_Projects/Marks%20Management%20System/marks-management/simulate_excel.py) and [seed.py](file:///d:/My_Projects/Marks%20Management%20System/marks-management/seed.py)
- **Frontend templates:** Located in [templates/](file:///d:/My_Projects/Marks%20Management%20System/marks-management/templates)
- **Static assets / custom CSS:** Located in [static/](file:///d:/My_Projects/Marks%20Management%20System/marks-management/static)
