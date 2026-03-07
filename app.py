import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Admin, Teacher, Student, Subject, Mark, Result
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'marks-management-super-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'yourmail@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_app_password')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'yourmail@gmail.com')

mail = Mail(app)

db.init_app(app)

with app.app_context():
    db.create_all()
    # Create default admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
        db.session.add(admin)
        db.session.commit()

# --- Helper Functions ---
def calculate_grade(total):
    """Calculate Grade and Grade Point based on Total Marks (100)"""
    if total >= 90: return 'A+', 10
    elif total >= 80: return 'A', 9
    elif total >= 70: return 'B', 8
    elif total >= 60: return 'C', 7
    elif total >= 50: return 'D', 6
    elif total >= 40: return 'E', 5
    else: return 'F', 0

# --- General Routes ---
@app.route('/')
def index():
    return redirect(url_for('student_portal'))

# --- Student Portal Routes ---
@app.route('/student', methods=['GET', 'POST'])
def student_portal():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no')
        aadhar = request.form.get('aadhar') # Expected as last 4 digits
        
        student = Student.query.filter_by(roll_no=roll_no).first()
        if student and student.aadhar_last4 == aadhar[-4:]:
            result = Result.query.filter_by(student_id=student.id).first()
            if result and result.is_released:
                marks = Mark.query.filter_by(student_id=student.id).all()
                return render_template('result.html', student=student, marks=marks, result=result)
            else:
                flash('Results are not yet released for this roll number.', 'warning')
        else:
            flash('Invalid Roll Number or Aadhar', 'error')
            
    return render_template('student_login.html')

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.id
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials, please try again.', 'error')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    teachers = Teacher.query.all()
    students = Student.query.order_by(Student.semester, Student.roll_no).all()
    subjects = Subject.query.all()
    # Build distinct sorted batch list for dropdowns
    batches = sorted(set(s.batch for s in students if s.batch))
    return render_template('admin_dashboard.html', teachers=teachers, students=students,
                           subjects=subjects, batches=batches)

@app.route('/admin/add_subject', methods=['POST'])
def add_subject():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    code = request.form.get('code')
    name = request.form.get('name')
    credits = request.form.get('credits', type=int)
    teacher_id = request.form.get('teacher_id', type=int)
    
    if Subject.query.filter_by(code=code).first():
        flash('A subject with this Code already exists.', 'error')
    else:
        new_subject = Subject(code=code, name=name, credits=credits, teacher_id=teacher_id)
        db.session.add(new_subject)
        db.session.commit()
        flash(f'Subject {name} added successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#subjects')

@app.route('/admin/edit_subject/<int:id>', methods=['POST'])
def edit_subject(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    subject = Subject.query.get_or_404(id)
    code = request.form.get('code')
    name = request.form.get('name')
    credits = request.form.get('credits', type=int)
    teacher_id = request.form.get('teacher_id', type=int)
    
    existing_code = Subject.query.filter_by(code=code).first()
    if existing_code and existing_code.id != id:
        flash('Course Code is already in use by another subject.', 'error')
    else:
        subject.code = code
        subject.name = name
        subject.credits = credits
        subject.teacher_id = teacher_id
        db.session.commit()
        flash(f'Subject {name} updated successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#subjects')


@app.route('/admin/calculate_results', methods=['POST'])
def calculate_results():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))

    semester = request.form.get('semester', 1, type=int)
    batch    = request.form.get('batch', '').strip()

    # ✅ Filter students by the chosen semester (and optionally batch)
    query = Student.query.filter_by(semester=semester)
    if batch:
        query = query.filter_by(batch=batch)
    students = query.all()

    if not students:
        flash(f'No students found for Semester {semester}' + (f', Batch {batch}' if batch else '') + '.', 'warning')
        return redirect(url_for('admin_dashboard') + '#dashboard')

    calculated_count = 0

    for student in students:
        marks = Mark.query.filter_by(student_id=student.id).all()
        if not marks: continue

        calculated_count += 1
        total_credits      = 0
        total_grade_points = 0
        has_failed         = False

        for mark in marks:
            total_credits      += mark.subject.credits
            total_grade_points += mark.grade_point * mark.subject.credits
            if mark.grade_point == 0:
                has_failed = True

        sgpa = total_grade_points / total_credits if total_credits > 0 else 0.0

        result = Result.query.filter_by(student_id=student.id).first()
        if not result:
            result = Result(student_id=student.id)
            db.session.add(result)

        result.sgpa        = round(sgpa, 2)
        result.cgpa        = round(sgpa, 2)
        result.semester    = semester
        result.is_released = False

    db.session.commit()
    sem_label = f'Semester {semester}' + (f', Batch {batch}' if batch else '')
    flash(f'Calculated grades for {calculated_count} student(s) in {sem_label}. Ready for Review & Export.', 'success')
    return redirect(url_for('admin_dashboard') + '#dashboard')

@app.route('/admin/release_results', methods=['POST'])
def release_results():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    # Only release results that have been calculated
    results = Result.query.all()
    students_to_email = []
    
    for result in results:
        if not result.is_released:
            result.is_released = True
            students_to_email.append(Student.query.get(result.student_id))
            
    if not students_to_email:
        flash('No new results found to release.', 'info')
        return redirect(url_for('admin_dashboard') + '#dashboard')

    db.session.commit()
    
    # Send emails in a background thread so the browser isn't kept waiting
    try:
        from mail_sender import send_all_results_email
        queued, skipped = send_all_results_email(app, mail, students_to_email)
        flash(
            f'Results released! Emails queued for {queued} student(s)'
            + (f' ({skipped} skipped – no marks yet).' if skipped else '.'),
            'success'
        )
    except Exception as e:
        print(f"[MAIL] Error starting mailer: {e}")
        flash(f'Results released to portal, but email dispatch failed: {e}', 'warning')
        
    return redirect(url_for('admin_dashboard') + '#dashboard')

@app.route('/admin/export_results', methods=['GET'])
def export_results():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from flask import send_file
    
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Student Results"
    
    # 1. Main Title Row
    sheet.append(["Student Results Report"])
    sheet.merge_cells('A1:H1')
    title_cell = sheet['A1']
    title_cell.font = Font(size=16, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    title_cell.alignment = Alignment(horizontal='center', vertical='center')
    sheet.row_dimensions[1].height = 30
    
    # 2. Add empty row for spacing
    sheet.append([])
    
    # 3. Header Row
    headers = [
        "Name", "Roll Number", "Internal", "External", "Total", "Grade", "SGPA", "CGPA"
    ]
    sheet.append(headers)
    
    thin_border = Border(left=Side(style='thin', color='D1D5DB'), 
                         right=Side(style='thin', color='D1D5DB'), 
                         top=Side(style='thin', color='D1D5DB'), 
                         bottom=Side(style='thin', color='D1D5DB'))
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    
    # Format Headers (row 3)
    for cell in sheet[3]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border
        
    batch = request.args.get('batch')
    if batch:
        students = Student.query.filter_by(batch=batch).all()
    else:
        students = Student.query.all()
    
    light_gray_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    white_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    current_row = 4
    
    for student in students:
        marks = Mark.query.filter_by(student_id=student.id).all()
        result = Result.query.filter_by(student_id=student.id).first()
        
        # Calculate totals
        internal_sum = sum(m.internal for m in marks) if marks else 0
        external_sum = sum(m.external for m in marks) if marks else 0
        total_sum = sum(m.total for m in marks) if marks else 0
        
        # Determine aggregate grade
        has_failed = any(m.grade == 'F' for m in marks) if marks else False
        overall_grade = 'F' if has_failed else calculate_grade(total_sum / len(marks) if len(marks) > 0 else 0)[0]
        
        sgpa = result.sgpa if result else 0.0
        cgpa = result.cgpa if result else 0.0
        
        row_data = [
            student.name,
            student.roll_no,
            internal_sum,
            external_sum,
            total_sum,
            overall_grade,
            sgpa,
            cgpa
        ]
        sheet.append(row_data)
        
        # Zebra Striping & Borders
        fill_color = light_gray_fill if (current_row % 2 == 0) else white_fill
        for cell in sheet[current_row]:
            cell.fill = fill_color
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
            
        current_row += 1
        
    # Auto-adjust column widths
    from openpyxl.utils import get_column_letter
    for col_idx in range(1, sheet.max_column + 1):
        column = get_column_letter(col_idx)
        max_length = 0
        for row_idx in range(1, sheet.max_row + 1):
            cell = sheet.cell(row=row_idx, column=col_idx)
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    file_path = os.path.join(app.root_path, "student_results.xlsx")
    workbook.save(file_path)
    
    return send_file(file_path, as_attachment=True)

@app.route('/admin/send_single_result', methods=['POST'])
def send_single_result():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    roll_no = request.form.get('roll_no')
    student = Student.query.filter_by(roll_no=roll_no).first()
    
    if not student:
        flash('Student not found with that Roll Number.', 'error')
        return redirect(url_for('admin_dashboard') + '#dashboard')
        
    result = Result.query.filter_by(student_id=student.id).first()
    if not result or not result.is_released:
        flash('Results have not been calculated/released for this student yet.', 'warning')
        return redirect(url_for('admin_dashboard') + '#dashboard')

    try:
        from mail_sender import send_all_results_email
        queued, _ = send_all_results_email(app, mail, [student])
        if queued:
            flash(f'Email queued for {student.name} ({student.email})!', 'success')
        else:
            flash(f'Could not queue email – result may not be marked as released yet.', 'warning')
    except Exception as e:
        print(f"[MAIL] Error: {e}")
        flash(f'Failed to send email: {e}', 'error')
        
    return redirect(url_for('admin_dashboard') + '#dashboard')

@app.route('/admin/add_student', methods=['POST'])
def add_student():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    roll_no = request.form.get('roll_no')
    name = request.form.get('name')
    email = request.form.get('email')
    aadhar = request.form.get('aadhar')
    batch = request.form.get('batch', '2024 Intake')
    semester = request.form.get('semester', 1, type=int)
    
    if Student.query.filter_by(roll_no=roll_no).first():
        flash('A student with this Roll Number already exists.', 'error')
    elif Student.query.filter_by(email=email).first():
        flash('A student with this Email already exists.', 'error')
    else:
        new_student = Student(roll_no=roll_no, name=name, email=email, aadhar_last4=aadhar[-4:] if aadhar else '', batch=batch, semester=semester)
        db.session.add(new_student)
        db.session.commit()
        flash(f'Student {name} added successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#students')

@app.route('/admin/edit_student/<int:id>', methods=['POST'])
def edit_student(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    student = Student.query.get_or_404(id)
    roll_no = request.form.get('roll_no')
    name = request.form.get('name')
    email = request.form.get('email')
    aadhar = request.form.get('aadhar')
    batch = request.form.get('batch')
    semester = request.form.get('semester', type=int)
    
    # Check for duplicate roll_no or email during edit
    existing_roll = Student.query.filter_by(roll_no=roll_no).first()
    if existing_roll and existing_roll.id != id:
        flash('Roll Number is already in use by another student.', 'error')
    else:
        existing_email = Student.query.filter_by(email=email).first()
        if existing_email and existing_email.id != id:
            flash('Email is already in use by another student.', 'error')
        else:
            student.roll_no = roll_no
            student.name = name
            student.email = email
            if batch:
                student.batch = batch
            if semester:
                student.semester = semester
            if aadhar:
                student.aadhar_last4 = aadhar[-4:]
            
            db.session.commit()
            flash(f'Student {name} updated successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#students')

@app.route('/admin/add_teacher', methods=['POST'])
def add_teacher():
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if Teacher.query.filter_by(email=email).first():
        flash('A faculty member with this Email already exists.', 'error')
    else:
        new_teacher = Teacher(
            name=name, 
            email=email, 
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_teacher)
        db.session.commit()
        flash(f'Faculty {name} added successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#faculties')

@app.route('/admin/edit_teacher/<int:id>', methods=['POST'])
def edit_teacher(id):
    if 'admin_id' not in session: return redirect(url_for('admin_login'))
    
    teacher = Teacher.query.get_or_404(id)
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    existing_email = Teacher.query.filter_by(email=email).first()
    if existing_email and existing_email.id != id:
        flash('Email is already in use by another faculty member.', 'error')
    else:
        teacher.name = name
        teacher.email = email
        
        if password and password.strip() != "":
            teacher.password_hash = generate_password_hash(password)
            
        db.session.commit()
        flash(f'Faculty {name} updated successfully!', 'success')
        
    return redirect(url_for('admin_dashboard') + '#faculties')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

# --- Teacher Routes ---
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        teacher = Teacher.query.filter_by(email=email).first()
        if teacher and check_password_hash(teacher.password_hash, password):
            session['teacher_id'] = teacher.id
            return redirect(url_for('teacher_dashboard'))
        flash('Invalid credentials, please try again.', 'error')
    return render_template('teacher_login.html')

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'teacher_id' not in session: return redirect(url_for('teacher_login'))
    teacher = Teacher.query.get(session['teacher_id'])
    
    subjects = Subject.query.filter_by(teacher_id=teacher.id).all()
    return render_template('teacher_dashboard.html', teacher=teacher, subjects=subjects)

@app.route('/teacher/enter_marks/<int:subject_id>', methods=['GET', 'POST'])
def enter_marks(subject_id):
    if 'teacher_id' not in session: return redirect(url_for('teacher_login'))
    
    teacher_id = session['teacher_id']
    subject = Subject.query.filter_by(id=subject_id, teacher_id=teacher_id).first_or_404()
    students = Student.query.all()
    
    if request.method == 'POST':
        for student in students:
            internal_str = request.form.get(f'internal_{student.id}')
            external_str = request.form.get(f'external_{student.id}')
            
            if internal_str and external_str:
                try:
                    internal = float(internal_str)
                    external = float(external_str)
                    
                    if internal > 30.0 or external > 70.0 or internal < 0 or external < 0:
                        flash(f'Invalid marks for {student.name}. Internal (max 30) and External (max 70).', 'error')
                        continue

                    total = internal + external
                    grade, gp = calculate_grade(total)
                    
                    mark = Mark.query.filter_by(student_id=student.id, subject_id=subject.id).first()
                    if not mark:
                        mark = Mark(student_id=student.id, subject_id=subject.id)
                        db.session.add(mark)
                        
                    mark.internal = internal
                    mark.external = external
                    mark.total = total
                    mark.grade = grade
                    mark.grade_point = gp
                except ValueError:
                    flash(f'Invalid numeric format for {student.name}.', 'error')
                    continue # Skip invalid marks
                    
        db.session.commit()
        
        # AUTO-CALCULATE: Compute SGPA/CGPA for each student immediately after marks are saved.
        # Results are kept is_released=False - admin must explicitly publish to students.
        affected_students = set()
        for student in students:
            if request.form.get(f'internal_{student.id}') and request.form.get(f'external_{student.id}'):
                affected_students.add(student.id)
                
        for student in students:
            if student.id not in affected_students:
                continue
                
            # Reset released flag for security
            existing_result = Result.query.filter_by(student_id=student.id).first()
            if existing_result and existing_result.is_released:
                existing_result.is_released = False
                
            # Re-calculate SGPA from ALL subjects (not just this one)
            all_marks = Mark.query.filter_by(student_id=student.id).all()
            if not all_marks:
                continue
            
            total_credits = sum(m.subject.credits for m in all_marks)
            total_grade_points = sum(m.grade_point * m.subject.credits for m in all_marks)
            sgpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0
            
            result = existing_result or Result.query.filter_by(student_id=student.id).first()
            if not result:
                result = Result(student_id=student.id)
                db.session.add(result)
            
            result.sgpa = sgpa
            result.cgpa = sgpa  # simplified single-semester CGPA
            result.is_released = False

        db.session.commit()
        flash('Marks saved & calculated! Review below. Admin must release before students can see results.', 'success')
        return redirect(url_for('marks_preview', subject_id=subject_id))
        
    existing_marks = {m.student_id: m for m in Mark.query.filter_by(subject_id=subject.id).all()}
    return render_template('enter_marks.html', subject=subject, students=students, marks=existing_marks)

@app.route('/teacher/marks_preview/<int:subject_id>')
def marks_preview(subject_id):
    if 'teacher_id' not in session: return redirect(url_for('teacher_login'))

    teacher_id = session['teacher_id']
    subject = Subject.query.filter_by(id=subject_id, teacher_id=teacher_id).first_or_404()
    students = Student.query.all()

    # Build a rich preview structure per student
    preview_data = []
    for student in students:
        mark = Mark.query.filter_by(student_id=student.id, subject_id=subject.id).first()
        result = Result.query.filter_by(student_id=student.id).first()
        preview_data.append({
            'student': student,
            'mark': mark,
            'sgpa': result.sgpa if result else None,
        })

    return render_template('marks_preview.html', subject=subject, preview_data=preview_data)
    
@app.route('/teacher/edit_student_marks/<int:subject_id>/<int:student_id>', methods=['GET', 'POST'])
def edit_student_marks(subject_id, student_id):
    if 'teacher_id' not in session: return redirect(url_for('teacher_login'))
    
    teacher_id = session['teacher_id']
    subject = Subject.query.filter_by(id=subject_id, teacher_id=teacher_id).first_or_404()
    student = Student.query.get_or_404(student_id)
    
    import json
    
    if request.method == 'POST':
        internal_str = request.form.get('internal')
        
        # Section A: 10 Qs, max 2 each
        sec_a_marks = {}
        sec_a_total = 0
        for char in 'abcdefghij':
            val = request.form.get(f'q1{char}', '0')
            try:
                m = float(val)
                sec_a_marks[f'q1{char}'] = m
                sec_a_total += m
            except ValueError:
                sec_a_marks[f'q1{char}'] = 0
        
        # Section B: 5 pairs, Best of Two, max 10 each
        sec_b_marks = {}
        sec_b_total = 0
        pairs = [(2,3), (4,5), (6,7), (8,9), (10,11)]
        for p1, p2 in pairs:
            v1 = float(request.form.get(f'q{p1}', '0') or 0)
            v2 = float(request.form.get(f'q{p2}', '0') or 0)
            sec_b_marks[f'q{p1}'] = v1
            sec_b_marks[f'q{p2}'] = v2
            sec_b_total += max(v1, v2)
            
        external = sec_a_total + sec_b_total
        breakup_json = json.dumps({'sec_a': sec_a_marks, 'sec_b': sec_b_marks})
        
        if internal_str:
            try:
                internal = float(internal_str)
                
                if internal > 30.0 or external > 70.0 or internal < 0 or external < 0:
                    flash(f'Invalid marks. Internal (max 30) and External (max 70).', 'error')
                    return redirect(url_for('edit_student_marks', subject_id=subject_id, student_id=student_id))

                total = internal + external
                grade, gp = calculate_grade(total)
                
                mark = Mark.query.filter_by(student_id=student.id, subject_id=subject.id).first()
                if not mark:
                    mark = Mark(student_id=student.id, subject_id=subject.id)
                    db.session.add(mark)
                    
                mark.internal = internal
                mark.external = external
                mark.total = total
                mark.grade = grade
                mark.grade_point = gp
                mark.external_breakup = breakup_json
                
                # Re-calculate SGPA
                existing_result = Result.query.filter_by(student_id=student.id).first()
                if existing_result and existing_result.is_released:
                    existing_result.is_released = False
                
                all_marks = Mark.query.filter_by(student_id=student.id).all()
                total_credits = sum(m.subject.credits for m in all_marks)
                total_grade_points = sum(m.grade_point * m.subject.credits for m in all_marks)
                sgpa = round(total_grade_points / total_credits, 2) if total_credits > 0 else 0.0
                
                result = existing_result or Result.query.filter_by(student_id=student.id).first()
                if not result:
                    result = Result(student_id=student.id)
                    db.session.add(result)
                
                result.sgpa = sgpa
                result.cgpa = sgpa
                result.is_released = False
                
                db.session.commit()
                flash(f'Marks updated for {student.name}!', 'success')
                return redirect(url_for('marks_preview', subject_id=subject_id))
            except ValueError:
                flash(f'Invalid numeric format.', 'error')
        
    mark = Mark.query.filter_by(student_id=student.id, subject_id=subject.id).first()
    breakup = json.loads(mark.external_breakup) if mark and mark.external_breakup else None
    return render_template('edit_student_marks.html', subject=subject, student=student, mark=mark, breakup=breakup)

@app.route('/teacher/logout')
def teacher_logout():
    session.pop('teacher_id', None)
    return redirect(url_for('teacher_login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
