from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subjects = db.relationship('Subject', backref='teacher', lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    aadhar_last4 = db.Column(db.String(4), nullable=False)
    batch = db.Column(db.String(20), nullable=False, default="2024 Intake")
    semester = db.Column(db.Integer, nullable=False, default=1)  # Current semester (1-8)
    marks = db.relationship('Mark', backref='student', lazy=True)
    results = db.relationship('Result', backref='student', uselist=False)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    processing_status = db.Column(db.String(20), default='NOT_PROCESSED') # NOT_PROCESSED, PROCESSING, COMPLETED
    marks = db.relationship('Mark', backref='subject', lazy=True)

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

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    sgpa = db.Column(db.Float, nullable=False, default=0.0)
    cgpa = db.Column(db.Float, nullable=False, default=0.0)
    semester = db.Column(db.Integer, nullable=False, default=1)
    is_released = db.Column(db.Boolean, default=False)

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

class StudentMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    unique_id = db.Column(db.String(50), nullable=False)
    roll_number = db.Column(db.String(20), db.ForeignKey('student.roll_no'), nullable=False)
    upload_version = db.Column(db.Integer, default=1)

    __table_args__ = (
        db.UniqueConstraint('unique_id', 'subject_id', name='uq_student_mapping_subject_unique_id'),
    )
