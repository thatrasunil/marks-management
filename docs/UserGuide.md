# Marks Management System - User Guide 📖

Welcome to the **Marks Management System (MMS)** User Guide. This guide covers how to use the system from the perspective of Teachers, Administrators, and Students.

---

## 👩‍🏫 Teacher Workflow

The Teacher portal manages marks upload, student mapping, validation, grading, and submission of results for processing.

### 1. Login
- Navigate to `/teacher/login`.
- Enter your registered Teacher email and password.
- Upon authentication, you will be redirected to the **Teacher Dashboard**.

### 2. Dashboard Overview
- View all subjects assigned to you.
- Monitor processing status of each subject:
  - `NOT_PROCESSED`: Marks have not been uploaded or processed.
  - `DRAFT`: Marks have been processed and saved locally for review.
  - `SUBMITTED`: Marks have been submitted to the Admin for approval. Editing is locked.
  - `REJECTED`: The Admin rejected the submission. You can unlock and re-edit/re-upload.
  - `APPROVED`: The Admin approved the marks. Results are locked and ready for release.

### 3. Uploading Marks & Mappings (3-Stage Ingestion)
To process marks for a subject:
1. Click **Manage** next to the target subject.
2. Under the upload area, import the three required Excel sheets in any order:
   - **External Marks**: Sheet containing unique anonymous IDs and external grades/marks.
   - **Student Mapping**: Sheet mapping Student Roll Numbers to anonymous IDs.
   - **Internal Marks**: Sheet containing Student Roll Numbers and internal grades/marks.
3. Click **Validate Upload** to test file formats and view real-time validation status (catches duplicates, missing students, invalid scores).

### 4. Marks Processing
- Once all three stages are uploaded and valid, click **Process Results**.
- The grading engine will automatically compute the total marks, letter grades (A+ to F), and GPAs based on institutional rules.
- Review the marks in the **Marks Preview** table.

### 5. Final Submission
- Once satisfied with the preview, click **Submit to Admin** from the submission preview panel.
- Enter any comments or notes.
- The subject status changes to `SUBMITTED`, and editing is locked pending Admin review.

---

## 🔐 Administrator Workflow

The Admin portal has ultimate oversight to review submissions, manage settings, audit logs, and release grades to students.

### 1. Submissions Inbox
- View all teacher submissions in the dashboard.
- Review the pass rate, average scores, and audit logs.
- Click **Review** to inspect the detailed marks sheet.
- **Approve**: If correct, approve the marks. They are locked and marked as `APPROVED`.
- **Reject**: If errors exist, reject the marks, specify a reason, and return them to the teacher as `REJECTED` for correction.

### 2. Calculating & Releasing Results
- Once subjects are approved, go to the **Release Results** section.
- Click **Calculate Results** to compute SGPAs and CGPAs for students.
- Click **Release Results** to make them public.
- The system will automatically lock all grades and send notification emails to students asynchronously.

### 3. Tabulation Register (TR)
- Navigate to **Tabulation Register** from the sidebar.
- Filter by Academic Year, Semester, Department, Batch, etc.
- View the dynamic cohort marks grid.
- Sort columns, search by name/roll number, or filter by grades and GPAs.
- Export to formatted Excel (`.xlsx`) or print/save as PDF.

### 4. Settings Panel
- Manage institution configuration (Institution Name, Academic Years list, SMTP server parameters, Memo Footer, Export Naming rules).

---

## 👨‍🎓 Student Workflow

The Student portal allows students to securely view their transcripts.

### 1. Authentication
- Navigate to `/student`.
- Enter your **Roll Number** and the last 4 digits of your **Aadhar Card**.
- Enter your email address for verification.

### 2. Viewing Results
- View current semester SGPA, CGPA, registered credits, and earned credits.
- View subject-wise breakdown of internal, external, and total marks along with letter grades.

### 3. Downloading Memo
- Click **Print Result Memo** to download or print your official semester report card.
