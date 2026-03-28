# System Architecture & Workflow

## 🏗️ High-Level Architecture
The system follows a classic Model-View-Controller (MVC) pattern adapted for web application structure.
1. **Frontend (View)**: HTML5 templates rendered server-side with Jinja2, utilizing Tailwind CSS for responsive and modern semantic design. File uploads will leverage Vanilla JS `fetch()` (AJAX) for seamless payload transport.
2. **Backend (Controller)**: A Python Flask server functioning as the orchestration layer to process HTTP requests, parse bulk binary files (Excel), validate schemas, execute GPA computations, and enforce Role-Based Access Controls (RBAC).
3. **Database (Model)**: A relational paradigm (currently SQLite/SQLAlchemy) that models Students, Teachers, Subjects, raw numerical imports (AnonymousMarkData, StudentMapping), and finalized computed values (Marks, Result).

---

## 🔄 Proposed Workflow

### The "Teacher-First" Processing Flow
Traditionally, Admin roles ingest data. Because of the technical granularity required in subject-level mapping, the workflow architecture is refactored to place domain experts (Teachers) in control of data integrity prior to Admin publication.

#### 1. Teacher Responsibilities
- **Data Ingestion**: Teacher uploads three required artifacts:
  1. `External Marks` sheet (`Unique_ID` mapped to `External_Marks`).
  2. `Student Mapping` sheet (`Unique_ID` mapped to `Roll_Number`).
  3. `Internal Marks` sheet (`Roll_Number` mapped to `Internal_Marks`).
- **Data Validation & Computation**: The system will automatically detect missing columns, unmapped Unique IDs, or duplicate entries. Once validated, it automatically calculates the `Total_Marks` (Internal + External) and the discrete `Subject Grade`.
- **Submission**: Teacher generates a localized Result Sheet and an Error Report (if applicable). Once manually verified, the Teacher changes the status of the Subject to `SUBMITTED`.

#### 2. Administrator Responsibilities
- **Oversight**: Admin monitors a global "Submissions Inbox".
- **Verification**: Admin reviews submitted computational outcomes (Teacher's generated sheets) for systemic anomalies. 
- **Approval Engine**: 
  - **Approve**: If correct, the Admin approves the subject, enabling the final calculation of SGPA and CGPA. 
  - **Reject**: If flawed, the Admin sends it back to the `DRAFT` bucket, noting a rejection reason.
- **Publication**: Admin globally releases the finalized Semester Result, allowing students view access.

#### 3. Student Responsibilities
- **Access**: Securely logs into a locked-down viewer using `Roll_Number` and the trailing 4 digits of a government-issued `Aadhar` number to view their finalized, Read-Only transcripts.
