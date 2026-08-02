# Marks Management System - Developer Guide 🛠️

This guide is designed for developers who wish to maintain, test, or extend the Marks Management System.

---

## 🏗️ Architecture Overview

The system is structured as a standard MVC application built on Flask:
- **`app.py`**: Routing, HTTP controllers, session-based authentication/guards, setting configurations, activity logging, and export wrappers.
- **`models.py`**: SQLAlchemy database model definitions with SQLite index mapping and foreign key constraint listeners.
- **`services.py`**: Core domain logic including:
  - `ProcessingService`: Handlers for calculating final total grades, processing GPA mappings, and batch/semester determinations.
  - `ValidationService`: 3-stage upload verification, validating structures of incoming internal/external files and mapping sheets.
  - `TabulationRegisterService`: Cohort matrix generation and Excel grid styling logic using openpyxl.
  - `AnalyticsService`: Aggregating cohort statistics and top merit logs.
- **`validators.py`**: Schema check logic for spreadsheet uploads.

---

## 📦 Setting Up Environment

1. **Virtual Environment Setup:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Installation of Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Database Initialization:**
   ```bash
   python seed.py
   ```
   *Note: `seed.py` pre-populates default admin credentials, teachers, and mock students for sandbox testing.*

---

## 🧪 Running Tests

The test suite covers full integration and unit testing using Flask's test client:
- **Workflow verification**: `venv\Scripts\python.exe test_workflow.py`
- **Analytics checks**: `venv\Scripts\python.exe test_analytics.py`
- **Tabulation Register verification**: `venv\Scripts\python.exe test_tabulation_register.py`
- **Result releasing**: `venv\Scripts\python.exe test_release.py` and `test_release_phase6.py`

---

## 🛠️ Modifying Grading & Validation Rules

### 1. Changing Letter Grades Scale
The logic mapping a total score (out of 100) to a letter grade and grade point is located in `services.py` inside `ProcessingService.calculate_grade`. To modify grade scales, edit the conditional checks in this function.

### 2. Custom Excel Schema Validation
To adjust mandatory columns or data types, edit the schema configurations inside `validators.py` (e.g., `validate_excel_file`).
