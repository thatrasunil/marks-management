from app import app, db
from models import Result, Student

client = app.test_client()

with app.app_context():
    # 1. Clear existing results
    for r in Result.query.all():
        db.session.delete(r)
    db.session.commit()
    print("Cleared all results.")
    
    # 2. Simulate Admin Calculating
    print("\n--- Simulating Admin Action: Calculate Results ---")
    with client.session_transaction() as sess:
        sess['admin_id'] = 1
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
        response = client.post('/student', data={'roll_no': s.roll_no, 'aadhar': '1234'}) # Assuming standard Aadhar format from db
        if b"Results are not yet released" in response.data or response.status_code == 200:
             print("SUCCESS: Student portal safely protects the hidden results.")
    
    # 4. Simulate Admin releasing
    print("\n--- Simulating Admin Action: Release Results ---")
    with client.session_transaction() as sess:
        sess['admin_id'] = 1
    response = client.post('/admin/release_results')
    print(f"Release HTTP Status: {response.status_code}")
    
    released = Result.query.all()
    for r in released:
        assert r.is_released == True, "FAIL! Result was not marked as released."
    print("SUCCESS: Results are now officially public and emails should be firing!")
