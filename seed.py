from app import app, db
from models import Admin, Teacher, Student, Subject
from werkzeug.security import generate_password_hash

def seed_database():
    with app.app_context():
        # Clear existing non-admin data if testing
        db.session.query(Student).delete()
        db.session.query(Subject).delete()
        db.session.query(Teacher).delete()
        db.session.commit()

        # Check Admin
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
            db.session.add(admin)

        # Add Teacher
        teacher1 = Teacher(name='Dr. Ravi Sharma', email='ravi@college.edu', password_hash=generate_password_hash('ravi123'))
        db.session.add(teacher1)
        db.session.commit() # Commit to get teacher ID
        
        # Add Subjects
        ds = Subject(code='CS101', name='Data Structures', credits=4, teacher_id=teacher1.id)
        maths = Subject(code='MA101', name='Engineering Mathematics', credits=4, teacher_id=teacher1.id)
        dld = Subject(code='EC101', name='Digital Logic Design', credits=3, teacher_id=teacher1.id)
        db.session.add_all([ds, maths, dld])
        
        # Add Student
        student = Student(
            roll_no='24AK1A30F1', 
            name='Sunil Kumar', 
            email='sunil@college.edu', 
            aadhar_last4='1234'
        )
        db.session.add(student)
        
        db.session.commit()
        print("Database seeded successfully!")
        print("Admin Login: admin / admin")
        print("Teacher Login: ravi@college.edu / ravi123")
        print("Student Portal checking with Roll No: 24AK1A30F1, Aadhar ends in: 1234")

if __name__ == '__main__':
    seed_database()
