# Marks Management System 🏫

A comprehensive, institutional-grade web-based examination and marks management system built with **Flask**. This application streamlines subject-level marks entry, 3-stage validation, automated GPA/CGPA computation, email notifications, result publication, an official **University Tabulation Register (TR)** system, and real-time **Analytics dashboards**.

---

## ✨ Key Features

### 👨‍🎓 Student Portal
- **Instant Result Access:** Students view finalized transcripts securely using Roll Number and Aadhar validation.
- **Detailed Marksheets:** Displays subject-wise internal, external, total marks, letter grades, and grade points.
- **GPA & Credit Tracking:** Automatically displays Semester Grade Point Average (SGPA), Cumulative GPA (CGPA), and registered vs. earned credits.

### 👩‍🏫 Teacher Dashboard
- **Subject Lifecycle Management:** Complete control over managing marks for assigned subjects.
- **AJAX Processing Engine:** A zero-reload 3-stage validation pipeline ingesting `External Marks`, `Student Mapping`, and `Internal Marks` via Excel.
- **Auto-Grading & Validation:** Automatically catches missing students/mappings, calculates totals, and assigns letter grades (A+ to F) on a 100-mark scale.
- **Submission Workflow:** Teachers gather data into `DRAFT`, review previews, download error reports, and submit to Admin for review.

### 🔐 Admin Dashboard & Approval Workflow
- **Centralized Management:** Complete management for Faculties, Students, and Subjects.
- **Submissions Inbox:** Review, `Approve`, or `Reject` result sets submitted by teachers with real-time feedback loops.
- **Result Release Engine:** One-click release of approved examination results, locking grades and dispatching student notification emails.

### 🔍 Phase 10: Production Polish
- **Global Search Engine:** Press `Ctrl+K` to search across Students, Teachers, and Subjects instantly with partial matching.
- **Advanced UI Filters:** Standardized cohort filters saved across page navigations.
- **Standardized Exports:** Download student reports and tabulation registers in both Excel and CSV formats with audit headers (user metadata, timestamps).
- **Institution Settings Panel:** Manage Institution Name, Academic Years, Memo Footers, and SMTP settings from a dedicated admin interface.
- **Activity & Audit Logging:** Record and display all logins, approvals, releases, and exports in a centralized audit log.
- **Centralized Error Handlers:** Custom, friendly layouts for 404 (Not Found) and 500 (Internal Server Error) with retry hooks.

---

## ✅ Feature Checklist

- [x] Student Result Portal (Aadhar & Roll No auth)
- [x] Teacher Subject Lifecycle & 3-stage validation pipeline
- [x] Teacher Error Report download & preview
- [x] Admin Submissions Inbox (Approve / Reject workflows)
- [x] Result Release Engine & Asynchronous Email Notification
- [x] Phase 8: University Tabulation Register (TR) Module
- [x] Phase 9: Real-time Analytics Dashboard Module
- [x] Phase 10: Production Polish (Search, Settings, Activity Log, Error Handling, Indexed db)
- [x] Phase 11: Final Hardening & Production Readiness (Enforced Constraints, Comprehensive Docs)


---

## 🛠️ Tech Stack

- **Backend:** Flask 3.0 (Python 3.8+)
- **Database:** SQLite with SQLAlchemy ORM
- **Processing:** Pandas (for parsing incoming Excel uploads)
- **Reports & Export:** Openpyxl (Excel Workbook Generation)
- **Email:** Flask-Mail (SMTP Integration)
- **Frontend:** HTML5, CSS3, Tailwind CSS, Vanilla JavaScript (AJAX fetch)

---

## 🚀 Getting Started

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/thatrasunil/marks-management.git
   cd marks-management
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database & Seed:**
   ```bash
   python seed.py
   ```

5. **Run Tests:**
   ```bash
   python test_production_polish.py
   ```

6. **Run the Application:**
   ```bash
   python app.py
   ```
   Access the portal at `http://localhost:5000`.
