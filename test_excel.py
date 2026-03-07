from app import app
import os

print("Running test client...")
client = app.test_client()

# Forge a session with admin logged in
with client.session_transaction() as sess:
    sess['admin_id'] = 1

# Hit the export endpoint
response = client.get('/admin/export_results')
print(f"Status Code: {response.status_code}")

# See if the file was created locally
file_path = os.path.join(app.root_path, "student_results.xlsx")
if os.path.exists(file_path):
    print(f"Success! File generated at {file_path}")
else:
    print("Failure! File not found.")
