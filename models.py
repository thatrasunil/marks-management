from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.engine import Engine
from sqlalchemy import event

db = SQLAlchemy()

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __init__(self, username, password_hash):
        self.username = username
        self.password_hash = password_hash

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subjects = db.relationship('Subject', backref='teacher', lazy=True)

    def __init__(self, name, email, password_hash):
        self.name = name
        self.email = email
        self.password_hash = password_hash

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    aadhar_last4 = db.Column(db.String(4), nullable=False)
    batch = db.Column(db.String(20), nullable=False, default="2024 Intake", index=True)
    semester = db.Column(db.Integer, nullable=False, default=1, index=True)  # Current semester (1-8)
    marks = db.relationship('Mark', backref='student', lazy=True)
    results = db.relationship('Result', backref='student', uselist=False)

    def __init__(self, roll_no, name, email, aadhar_last4, batch="2024 Intake", semester=1):
        self.roll_no = roll_no
        self.name = name
        self.email = email
        self.aadhar_last4 = aadhar_last4
        self.batch = batch
        self.semester = semester

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, index=True)
    credits = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    processing_status = db.Column(db.String(20), default='NOT_PROCESSED') # NOT_PROCESSED, DRAFT, SUBMITTED, REJECTED, APPROVED
    rejection_reason = db.Column(db.String(255), nullable=True)
    marks = db.relationship('Mark', backref='subject', lazy=True)

    def __init__(self, code, name, credits, teacher_id, processing_status='NOT_PROCESSED', rejection_reason=None):
        self.code = code
        self.name = name
        self.credits = credits
        self.teacher_id = teacher_id
        self.processing_status = processing_status
        self.rejection_reason = rejection_reason

    @property
    def latest_submission(self):
        return Submission.query.filter_by(subject_id=self.id).order_by(Submission.id.desc()).first()

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    internal = db.Column(db.Float, nullable=False, default=0.0)
    external = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    grade = db.Column(db.String(2), nullable=False, default='F')
    grade_point = db.Column(db.Integer, nullable=False, default=0)
    external_breakup = db.Column(db.Text, nullable=True) # Stores JSON breakup
    status = db.Column(db.String(20), nullable=False, default='DRAFT')

    def __init__(self, student_id, subject_id, internal=0.0, external=0.0, total=0.0, grade='F', grade_point=0, external_breakup=None, status='DRAFT'):
        self.student_id = student_id
        self.subject_id = subject_id
        self.internal = internal
        self.external = external
        self.total = total
        self.grade = grade
        self.grade_point = grade_point
        self.external_breakup = external_breakup
        self.status = status

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    sgpa = db.Column(db.Float, nullable=False, default=0.0)
    cgpa = db.Column(db.Float, nullable=False, default=0.0)
    semester = db.Column(db.Integer, nullable=False, default=1)
    is_released = db.Column(db.Boolean, default=False)
    credits_registered = db.Column(db.Integer, nullable=False, default=0)
    credits_earned = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, student_id, sgpa=0.0, cgpa=0.0, semester=1, is_released=False, credits_registered=0, credits_earned=0):
        self.student_id = student_id
        self.sgpa = sgpa
        self.cgpa = cgpa
        self.semester = semester
        self.is_released = is_released
        self.credits_registered = credits_registered
        self.credits_earned = credits_earned

class AnonymousMarkData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    unique_id = db.Column(db.String(50), nullable=False)
    marks_data = db.Column(db.Text, nullable=False) # JSON
    external_total = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='VALID') # VALID or ERROR
    upload_version = db.Column(db.Integer, default=1)

    __table_args__ = (
        db.UniqueConstraint('unique_id', 'subject_id', name='uq_anonymous_mark_subject_unique_id'),
    )

    def __init__(self, subject_id, unique_id, marks_data, external_total=0.0, status='VALID', upload_version=1):
        self.subject_id = subject_id
        self.unique_id = unique_id
        self.marks_data = marks_data
        self.external_total = external_total
        self.status = status
        self.upload_version = upload_version

class StudentMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    unique_id = db.Column(db.String(50), nullable=False)
    roll_number = db.Column(db.String(20), db.ForeignKey('student.roll_no'), nullable=False)
    upload_version = db.Column(db.Integer, default=1)

    __table_args__ = (
        db.UniqueConstraint('unique_id', 'subject_id', name='uq_student_mapping_subject_unique_id'),
    )

    def __init__(self, subject_id, unique_id, roll_number, upload_version=1):
        self.subject_id = subject_id
        self.unique_id = unique_id
        self.roll_number = roll_number
        self.upload_version = upload_version

class ProcessingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    level = db.Column(db.String(20), nullable=False) # INFO, WARNING, ERROR
    stage = db.Column(db.String(50), nullable=False) # VALIDATION_STARTED, VALIDATION_COMPLETED, etc.
    message = db.Column(db.Text, nullable=False)

    def __init__(self, subject_id, level, stage, message):
        self.subject_id = subject_id
        self.level = level
        self.stage = stage
        self.message = message

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitted_by = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    semester = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    batch = db.Column(db.String(50), nullable=False)
    workflow_status = db.Column(db.String(20), nullable=False, default='SUBMITTED')

    # New fields for Admin Review
    approved_by = db.Column(db.String(100), nullable=True)
    approval_timestamp = db.Column(db.DateTime, nullable=True)
    rejected_by = db.Column(db.String(100), nullable=True)
    rejection_timestamp = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    comments = db.Column(db.Text, nullable=True)

    subject = db.relationship('Subject', backref=db.backref('submissions', lazy=True))

    def __init__(self, submitted_by, semester, subject_id, department, academic_year, batch, workflow_status='SUBMITTED', approved_by=None, approval_timestamp=None, rejected_by=None, rejection_timestamp=None, rejection_reason=None, comments=None):
        self.submitted_by = submitted_by
        self.semester = semester
        self.subject_id = subject_id
        self.department = department
        self.academic_year = academic_year
        self.batch = batch
        self.workflow_status = workflow_status
        self.approved_by = approved_by
        self.approval_timestamp = approval_timestamp
        self.rejected_by = rejected_by
        self.rejection_timestamp = rejection_timestamp
        self.rejection_reason = rejection_reason
        self.comments = comments

    @property
    def student_count(self):
        count = Mark.query.filter_by(subject_id=self.subject_id).count()
        if count == 0:
            count = StudentMapping.query.filter_by(subject_id=self.subject_id).count()
        return count

    @property
    def processing_summary(self):
        marks = Mark.query.filter_by(subject_id=self.subject_id).all()
        if not marks:
            return "No marks processed"
        pass_count = len([m for m in marks if m.grade != 'F'])
        avg_total = sum(m.total for m in marks) / len(marks)
        return f"Pass Rate: {round(pass_count/len(marks)*100, 1)}% | Avg: {round(avg_total, 1)}"

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submitted_by = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    semester = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    previous_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    comments = db.Column(db.Text, nullable=True)

    subject = db.relationship('Subject', backref=db.backref('audit_logs', lazy=True))

    def __init__(self, submitted_by, semester, subject_id, department, previous_status, new_status, comments=None):
        self.submitted_by = submitted_by
        self.semester = semester
        self.subject_id = subject_id
        self.department = department
        self.previous_status = previous_status
        self.new_status = new_status
        self.comments = comments


class ResultRelease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    released_by = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    semester = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    batch = db.Column(db.String(50), nullable=False)
    release_version = db.Column(db.Integer, default=1)
    workflow_status = db.Column(db.String(20), nullable=False, default='RELEASED')

    subject = db.relationship('Subject', backref=db.backref('releases', lazy=True))

    def __init__(self, subject_id, released_by, semester, academic_year, department, batch, release_version=1, workflow_status='RELEASED'):
        self.subject_id = subject_id
        self.released_by = released_by
        self.semester = semester
        self.academic_year = academic_year
        self.department = department
        self.batch = batch
        self.release_version = release_version
        self.workflow_status = workflow_status


class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # PENDING, SENT, FAILED
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    error_message = db.Column(db.Text, nullable=True)

    student = db.relationship('Student', backref=db.backref('notifications', lazy=True))

    def __init__(self, student_id, email, subject, status='PENDING', error_message=None):
        self.student_id = student_id
        self.email = email
        self.subject = subject
        self.status = status
        self.error_message = error_message


class SystemSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    def __init__(self, key, value=None):
        self.key = key
        self.value = value


class SystemActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, index=True)
    action = db.Column(db.String(200), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), index=True)
    status = db.Column(db.String(50), nullable=False, default='SUCCESS')

    def __init__(self, username, action, status='SUCCESS'):
        self.username = username
        self.action = action
        self.status = status



