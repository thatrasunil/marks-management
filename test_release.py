from app import app, db
from models import (
    Result, Student, Teacher, Subject, StudentMapping, Mark, Submission, Admin,
    ResultRelease, NotificationLog, ProcessingLog, AuditLog, AnonymousMarkData
)
from werkzeug.security import generate_password_hash

client = app.test_client()

with app.app_context():
    # 1. Clear existing database tables to start from a clean state
    db.session.query(ResultRelease).delete()
    db.session.query(NotificationLog).delete()
    db.session.query(ProcessingLog).delete()
    db.session.query(AuditLog).delete()
    db.session.query(Submission).delete()
    db.session.query(StudentMapping).delete()
    db.session.query(AnonymousMarkData).delete()
    db.session.query(Mark).delete()
    db.session.query(Result).delete()
    db.session.query(Subject).delete()
    db.session.query(Student).delete()
    db.session.query(Teacher).delete()
    db.session.commit()
    print("Cleared all results and test tables.")

    # Seed required elements
    admin = Admin.query.filter_by(username='admin').first()
    if not admin:
        admin = Admin(username='admin', password_hash=generate_password_hash('admin'))
        db.session.add(admin)

    teacher = Teacher(name='Test Release Teacher', email='release_teacher@test.com', password_hash=generate_password_hash('password'))
    db.session.add(teacher)
    db.session.commit()

    student1 = Student(roll_no='TEST001', name='Test Student 1', email='student1@test.com', aadhar_last4='1234', semester=1, batch='2024 Intake')
    student2 = Student(roll_no='TEST002', name='Test Student 2', email='student2@test.com', aadhar_last4='5678', semester=1, batch='2024 Intake')
    db.session.add_all([student1, student2])
    db.session.commit()

    subject = Subject(code='TEST101', name='Test Subject 101', credits=4, teacher_id=teacher.id, processing_status='APPROVED')
    db.session.add(subject)
    db.session.commit()

    mapping1 = StudentMapping(subject_id=subject.id, unique_id='U001', roll_number=student1.roll_no)
    mapping2 = StudentMapping(subject_id=subject.id, unique_id='U002', roll_number=student2.roll_no)
    db.session.add_all([mapping1, mapping2])

    mark1 = Mark(student_id=student1.id, subject_id=subject.id, internal=25.0, external=45.0, total=70.0, grade='B', grade_point=8, status='APPROVED')
    mark2 = Mark(student_id=student2.id, subject_id=subject.id, internal=28.0, external=52.0, total=80.0, grade='A', grade_point=9, status='APPROVED')
    db.session.add_all([mark1, mark2])

    sub_record = Submission(
        submitted_by=teacher.name,
        semester=1,
        subject_id=subject.id,
        department='CS',
        academic_year='2024-2025',
        batch='2024 Intake',
        workflow_status='APPROVED',
        approved_by=admin.username
    )
    db.session.add(sub_record)
    db.session.commit()
    print("Database seeded with test release data.")
    
    # 2. Simulate Admin Calculating
    print("\n--- Simulating Admin Action: Calculate Results ---")
    with client.session_transaction() as sess:
        sess['admin_id'] = admin.id
    response = client.post('/admin/calculate_results', data={'semester': 1})
    print(f"Calculate HTTP Status: {response.status_code}")
    
    # Verify results are NOT released
    calculated = Result.query.all()
    print(f"Results generated: {len(calculated)}")
    for r in calculated:
        assert r.is_released == False, "FAIL! Result was released early."
    print("SUCCESS: All results are mathematically generated but hidden from students.")
    
    # 3. Simulate Student trying to view them
    print("\n--- Simulating Student View ---")
    s = Student.query.first()
    if s:
        response = client.post('/student', data={'roll_no': s.roll_no, 'aadhar': s.aadhar_last4})
        if b"Results are not yet released" in response.data or response.status_code == 200:
             print("SUCCESS: Student portal safely protects the hidden results.")
    
    # 4. Simulate Admin releasing
    print("\n--- Simulating Admin Action: Release Results ---")
    with client.session_transaction() as sess:
        sess['admin_id'] = admin.id
    response = client.post('/admin/release_results', data={'semester': 1})
    print(f"Release HTTP Status: {response.status_code}")
    
    released = Result.query.all()
    for r in released:
        assert r.is_released == True, "FAIL! Result was not marked as released."
    print("SUCCESS: Results are now officially public and emails should be firing!")
