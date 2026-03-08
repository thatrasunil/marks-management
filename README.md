# Marks Management System 🏫

A comprehensive, web-based examination and marks management system built with **Flask**. This application streamlines the process of entering marks, calculating grades/GPA, and communicating results to students.

## ✨ Key Features

### 👨‍🎓 Student Portal
- **Instant Result Access:** Students can view their marks securely using their Roll Number and Aadhar validation.
- **Detailed Marksheets:** Displays subject-wise internal, external, total marks, and grades.
- **GPA Tracking:** Shows SGPA and CGPA (calculated automatically).

### 👩‍🏫 Teacher Dashboard
- **Subject Management:** Teachers can manage marks for subjects assigned to them.
- **Advanced Marks Entry:** New flow allowing student-by-student mark editing for precise control.
- **Smart Entry:** Interactive marks entry with real-time feedback.
- **Auto-Grading:** Automatically calculates totals and grades (A+ to F) based on a 100-mark scale.

### 🔐 Admin Dashboard
- **Centralized Management:** Full CRUD operations for Teachers, Students, and Subjects.
- **Result Processing:** Batch calculation of SGPA/CGPA for specific semesters and batches.
- **Secure Publication:** One-click "Release Results" to make grades visible on the public portal.
- **Professional Reports:** Export student results to beautifully formatted **Excel (.xlsx)** sheets.

### 🧪 Data & Utilities
- **Excel Simulation:** Generate comprehensive simulated student data using `simulate_excel.py` for testing and demonstration.
- **Bulk Imports:** Scripts for automated student data ingestion and cleanup.

### 📧 Automated Notifications
- **Email Delivery:** Integrated with **Flask-Mail** to send results directly to student email addresses upon release.
- **Background Dispatch:** Robust email handling to prevent server timeouts.

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite (SQLAlchemy ORM)
- **Email:** Flask-Mail (SMTP Integration)
- **Reports:** Openpyxl (Excel Processing)
- **Frontend:** HTML5, CSS3 (Responsive Design)
- **Environment:** Python-Dotenv for secure configuration

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Gmail App Password (for email features)

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

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

5. **Initialize Database (Optional):**
   ```bash
   python seed.py
   ```

6. **Run the Application:**
   ```bash
   python app.py
   ```
   Access the portal at `http://localhost:5000`.

## 📁 Project Structure

### Core Files
- `app.py`: Main application logic, routes, and controllers.
- `models.py`: Database schema and SQLAlchemy models.
- `mail_sender.py`: Email notification utilities and background tasks.

### Utilities & Scripts
- `simulate_excel.py`: Generates simulated marks and SGPA/CGPA for testing.
- `import_students.py`: Bulk import students from external sources.
- `remove_students.py`: Utility for database cleanup.
- `seed.py`: Populates the database with initial sample data.
- `save_logo.py`: Helper for managing system branding.

### Assets
- `templates/`: Jinja2 HTML templates.
- `static/`: CSS styles, JavaScript, and images.
- `instance/`: Local database instance (SQLite).

---
Built with ❤️ by [Sunil](https://github.com/thatrasunil)
