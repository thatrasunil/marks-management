import sys
from unittest.mock import patch
from app import app, db
from models import Subject, Submission, AuditLog, Mark, Teacher

client = app.test_client()

print("\n=== STARTING END-TO-END WORKFLOW TESTS (PHASE 5) ===")

with app.app_context():
    # 1. Setup/Identify a test subject and teacher
    teacher = Teacher.query.first()
    if not teacher:
        print("ERROR: No teacher found in database. Seed the database first.")
        sys.exit(1)
        
    subject = Subject.query.filter_by(teacher_id=teacher.id).first()
    if not subject:
        # Create a mock subject
        subject = Subject(code="TEST101", name="Test Subject", credits=4, teacher_id=teacher.id, processing_status="NOT_PROCESSED")
        db.session.add(subject)
        db.session.commit()
        print("Created mock subject TEST101.")

    print(f"Testing workflow on subject: {subject.code} - {subject.name}")
    
    # Reset any existing state for clean test run
    subject.processing_status = "DRAFT"
    db.session.query(Submission).filter_by(subject_id=subject.id).delete()
    db.session.query(AuditLog).filter_by(subject_id=subject.id).delete()
    db.session.commit()
    print("Subject status reset to DRAFT.")

    # 2. Simulate submission from teacher (fails without login/owner checks)
    print("\n--- Step 1: Submit Results (Teacher) ---")
    with client.session_transaction() as sess:
        sess['teacher_id'] = teacher.id

    # Patch the validation check so we can submit mock/empty subjects
    with patch('app.ValidationService.validate_subject_processing') as mock_val:
        mock_val.return_value = True
        
        response = client.post(f'/teacher/submit_results/{subject.id}', data={
            'comments': 'Initial submission for evaluation.'
        })
        print(f"Submit HTTP Status: {response.status_code}")
        assert response.status_code == 200, f"Failed to submit: Status {response.status_code}"
    
    # Reload subject
    db.session.refresh(subject)
    print(f"Subject status after submission: {subject.processing_status}")
    assert subject.processing_status == "SUBMITTED", "Fail: Subject processing status should be SUBMITTED."
    
    # Check submission table
    sub_record = Submission.query.filter_by(subject_id=subject.id, workflow_status="SUBMITTED").first()
    assert sub_record is not None, "Fail: Submission record should be created."
    assert sub_record.comments == "Initial submission for evaluation.", "Fail: Comments not captured correctly."
    print("SUCCESS: Result submission verified.")

    # 3. Simulate rejection from admin (fails if not logged in as admin)
    print("\n--- Step 2: Reject Results (Admin) ---")
    # Reset session for admin
    with client.session_transaction() as sess:
        sess.clear()
        sess['admin_id'] = 1

    response = client.post(f'/admin/reject_subject/{subject.id}', data={
        'reason': 'Incorrect marks',
        'comments': 'Please re-verify Student ID roll no 101 marks.'
    })
    print(f"Reject HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to reject: Status {response.status_code}"
    
    db.session.refresh(subject)
    print(f"Subject status after rejection: {subject.processing_status}")
    assert subject.processing_status == "REJECTED", "Fail: Subject processing status should be REJECTED."
    
    sub_record = Submission.query.filter_by(subject_id=subject.id).order_by(Submission.id.desc()).first()
    assert sub_record.workflow_status == "REJECTED", "Fail: Latest submission should be updated to REJECTED."
    assert sub_record.rejection_reason == "Incorrect marks", "Fail: Rejection reason not saved."
    assert sub_record.comments == "Please re-verify Student ID roll no 101 marks.", "Fail: Comments not saved."
    print("SUCCESS: Admin rejection verified.")

    # 4. Simulate Unlock Action (Teacher)
    print("\n--- Step 3: Unlock Subject (Teacher) ---")
    with client.session_transaction() as sess:
        sess.clear()
        sess['teacher_id'] = teacher.id

    response = client.post(f'/teacher/unlock_subject/{subject.id}')
    print(f"Unlock HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to unlock: Status {response.status_code}"
    
    db.session.refresh(subject)
    print(f"Subject status after unlocking: {subject.processing_status}")
    assert subject.processing_status == "DRAFT", "Fail: Subject processing status should transition back to DRAFT."
    
    # Check Audit log
    audit = AuditLog.query.filter_by(subject_id=subject.id).order_by(AuditLog.id.desc()).first()
    assert audit.new_status == "DRAFT", "Fail: Audit log should capture transition to DRAFT."
    print("SUCCESS: Unlock action verified.")

    # 5. Re-submit (Teacher)
    print("\n--- Step 4: Re-Submit Results (Teacher) ---")
    with patch('app.ValidationService.validate_subject_processing') as mock_val:
        mock_val.return_value = True
        response = client.post(f'/teacher/submit_results/{subject.id}', data={
            'comments': 'Corrected student 101 marks as requested.'
        })
        print(f"Re-submit HTTP Status: {response.status_code}")
        assert response.status_code == 200, f"Failed to re-submit."
    
    db.session.refresh(subject)
    assert subject.processing_status == "SUBMITTED"
    print("SUCCESS: Resubmission verified.")

    # 6. Approve Action (Admin)
    print("\n--- Step 5: Approve Results (Admin) ---")
    with client.session_transaction() as sess:
        sess.clear()
        sess['admin_id'] = 1

    response = client.post(f'/admin/approve_subject/{subject.id}')
    print(f"Approve HTTP Status: {response.status_code}")
    assert response.status_code == 200, f"Failed to approve."
    
    db.session.refresh(subject)
    print(f"Subject status after approval: {subject.processing_status}")
    assert subject.processing_status == "APPROVED", "Fail: Subject processing status should be APPROVED."
    
    sub_record = Submission.query.filter_by(subject_id=subject.id).order_by(Submission.id.desc()).first()
    assert sub_record.workflow_status == "APPROVED", "Fail: Submission workflow status should be APPROVED."
    assert sub_record.approved_by is not None, "Fail: approved_by must be set."
    print("SUCCESS: Admin approval verified.")

    # 7. Check if locked post-approval (no editing allowed)
    print("\n--- Step 6: Verify Modifications are Locked ---")
    # Teacher tries to submit again or reprocess
    with client.session_transaction() as sess:
        sess.clear()
        sess['teacher_id'] = teacher.id
        
    response = client.post(f'/teacher/submit_results/{subject.id}', data={'comments': 'Trying to force change.'})
    print(f"Force submit status: {response.status_code}")
    # Should return an error (400) because it's approved and locked.
    assert response.status_code == 400
    
    response = client.post(f'/teacher/unlock_subject/{subject.id}')
    print(f"Force unlock status: {response.status_code}")
    # Only rejected can be unlocked
    assert response.status_code == 400

    print("SUCCESS: Edit lock post-approval verified.")
    print("\n=== ALL WORKFLOW TESTS PASSED SUCCESSFULLY! ===")
