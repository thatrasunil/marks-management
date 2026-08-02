# Changelog

All notable changes to the Marks Management System project are documented in this file.

---

## [Phase 11] - 2026-08-02

### Added
- **Enforced SQLite Foreign Key Constraints**: Added a database connection event listener that runs `PRAGMA foreign_keys=ON` automatically on every SQLite session initialization to prevent orphan records.
- **Comprehensive Project Guides**: Created detailed documentation under `docs/`:
  - `UserGuide.md`: Manual for Teachers, Administrators, and Students.
  - `DeveloperGuide.md`: Technical development, testing, and customization rules.
  - `DeploymentGuide.md`: Production-ready Gunicorn + Nginx configuration details.
  - `testing_report.md`: Complete QA report of E2E workflows, regression validations, and test results.

### Changed
- Updated root `README.md`, `docs/architecture.md`, `docs/api_documentation.md`, and `docs/database.md` to match the finalized, production-ready system state.
- Cleaned up database models and audited endpoint authorization controls.

---

## [Phase 10] - 2026-08-02

### Added
- **Global Search Engine**:
  - Live search (`/api/search`) matching Student Name, Hall Ticket, Teacher Name, Teacher ID, Subject Name, Subject Code, Department, Branch, Semester, Batch, and Academic Year.
  - Interactive glassmorphic search modal triggered globally via `Ctrl+K` or sidebar search button.
- **Advanced UI Filters**:
  - Reusable filtering components across dashboards supporting Academic Year, Semester, Batch, Department, Branch, and Statuses.
- **Standardized Export Operations**:
  - Unified Excel/CSV exporters featuring custom naming formats, user metadata headers, and generated timestamps.
- **Centralized Settings Management**:
  - New admin configuration panel to modify Institution Name, Academic Years, Result Memo Footer, Export Naming conventions, and SMTP email placeholders.
- **Application Activity Auditing**:
  - Integrated `SystemActivityLog` model and Admin dashboard activity log panel to record login attempts, imports, approvals, releases, and file exports.
- **Centralized Error Handlers**:
  - Registered custom 404 and 500 error pages to handle unexpected routing and database failures gracefully.
- **Performance Optimizations**:
  - Added SQLite database indexes on frequently searched attributes (`Student.name`, `Student.batch`, `Student.semester`, `Teacher.name`, `Subject.name`, `SystemActivityLog.timestamp`).

### Changed
- Updated `README.md`, `docs/architecture.md`, `docs/api_documentation.md`, and `docs/database.md` to document Phase 10 production-polish modifications.

---

## [Phase 9] - 2026-08-02

### Added
- **Analytics Dashboard Module**:
  - Global Admin Analytics dashboard available at `/admin/analytics` and Teacher-scoped Analytics dashboard available at `/teacher/analytics`.
  - Real-time aggregation of High-level Summary Metrics (total students, total teachers, total subjects, processed/draft/released/approved/submitted statuses).
  - Academic Cohort statistics (Appeared, Passed, Failed counts, pass/fail percentages, SGPA/Percentage range limits and averages).
  - Rich interactive visualizations using Chart.js (Pass vs Fail rates, Grade Distribution, Subject Averages, Department Pass rates, Semester Performance Trends, and SGPA/Percentage Histograms).
  - Top 10 Merit List ranking sorted by SGPA and Percentage with computed overall, department, and semester ranks.
  - Dynamically adjustable filtering by Academic Year, Semester, Department, Branch, Batch, Subject, and Result Status with instant updates.
  - Three-Sheet openpyxl Excel Export (`/admin/analytics/export`) containing cohort overview, top 10 merit students, and subject statistical breakdowns.
  - Strict Role-Based Access Control (RBAC) ensuring students are denied access, and teachers can only view metrics for subjects assigned to them.
  - Comprehensive automated test suite in `test_analytics.py` verifying calculations, filters, permissions, and spreadsheet exports.

### Changed
- Updated `README.md` with Phase 9 Analytics capabilities, updated workflow flowcharts, and templates project structure.
- Updated `docs/architecture.md` with details on the Analytics Module data aggregation flow, chart pipelines, and RBAC permission models.
- Updated `docs/api_documentation.md` detailing all backend analytics endpoints, parameters, and query responses.
- Updated `docs/database.md` explaining query optimizations and SQL aggregations.
- Integrated sidebar links in `templates/admin_dashboard.html` and `templates/teacher_dashboard.html` for easy dashboard navigation.

---

## [Phase 8] - 2026-08-02

### Added
- **University Tabulation Register (TR) System**:
  - Dedicated admin Tabulation Register module accessible via `/admin/tabulation_register`.
  - Multi-parametric cohort filters: Academic Year, Semester (1-8), Department, Branch, Batch, Section, and Exam Type.
  - Scoped data matrix strictly including officially `RELEASED` examination results.
  - Dynamic 2-tier subject matrix headers (Subject Code + Credits header, Int | Ext | Tot | Grade sub-headers) supporting any number of subjects per semester without code changes.
  - Real-time search by Hall Ticket / Student Name, multi-field filtering (PASS/FAIL, letter grade A+-F, SGPA range, Percentage range), and dynamic multi-column sorting.
  - Live summary statistics panel computing Total Students, Appeared, Passed, Failed, Pass Percentage, SGPA metrics (Highest, Lowest, Average), and Percentage metrics.
  - Professional Openpyxl Excel Export (`/admin/tabulation_register/export`) generating formatted `.xlsx` reports with merged title block, institution details, styled headers, cell borders, color-coded PASS/FAIL badges, and summary statistics section.
  - Print-friendly layout (`/admin/tabulation_register/print`) styled for A4 Landscape printing with page headers, signature blocks, and hidden UI navigation controls.
  - Performance optimization via SQLAlchemy `joinedload` eager fetching to prevent N+1 query overhead on large cohorts.
  - Admin Role-Based Access Control (RBAC) security enforcement across all TR endpoints.
  - Automated unit test suite in `test_tabulation_register.py` covering RBAC, matrix generation, multi-field filtering, summary stats, and openpyxl export.

### Changed
- Updated `README.md` with Phase 8 features, workflow diagram, TR text screenshot, export capabilities, and updated feature checklist.
- Updated `docs/architecture.md` with Tabulation Register system architecture, dynamic matrix transformation pipeline, openpyxl export engine, security/permission model, and performance optimizations.
- Created `docs/api_documentation.md` providing complete API specification for all Phase 8 TR endpoints and core application APIs.
- Created `docs/database.md` documenting table schemas, models, constraints, and eager loading optimization patterns.
- Updated `templates/admin_dashboard.html` with direct navigation link to Tabulation Register.

---

## [Phase 7] - 2026-08-02
- Student Result Portal redesign & enhanced transcript layout.

## [Phase 6] - 2026-08-02
- Single & Bulk Cohort Result Release Engine with Flask-Mail background notification email dispatch.

## [Phase 5] - 2026-08-02
- Admin Submissions Inbox with Approve / Reject workflows and audit log history.

## [Phase 4] - 2026-08-02
- Teacher 3-Stage Excel Processing Engine (External Marks, Student Mapping, Internal Marks) and validation pipeline.
