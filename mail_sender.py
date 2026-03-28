import time
import threading
import os
from flask_mail import Message


# ─── Background sender ────────────────────────────────────────────────────────
def _send_in_background(app, mail, students_data):
    """
    Runs in a daemon thread so the HTTP request returns immediately.
    `students_data` is a plain list of dicts (no SQLAlchemy objects) so there
    are no detached-session issues after the request context closes.
    """
    with app.app_context():
        sent, failed = 0, 0
        for s in students_data:
            html_body = _build_email_html(s)
            try:
                msg = Message(
                    subject=f"Semester {s['semester']} Result - Annamacharya Institute of Technology & Sciences, Tirupati",
                    recipients=[s['email']],
                    html=html_body,
                )
                mail.send(msg)
                print(f"[MAIL] Sent successfully to {s['email']}")
                sent += 1
                time.sleep(1)          # respect Gmail rate limits
            except Exception as e:
                print(f"[MAIL] ERROR: Failed for {s['email']}: {e}")
                failed += 1

        print(f"[MAIL] SUMMARY: {sent} sent successfully, {failed} failed.")


def send_all_results_email(app, mail, students):
    """
    Public entry point called from app.py.
    Accepts SQLAlchemy Student objects, converts them to plain dicts,
    then fires off a background thread.
    Returns (queued_count, skipped_count).
    """
    students_data = []
    skipped = 0

    for student in students:
        result = student.results          # uselist=False → single Result or None
        if not result or not result.is_released:
            skipped += 1
            continue

        marks = student.marks
        if not marks:
            skipped += 1
            continue

        # Serialise everything we need before leaving the request context
        marks_data = [
            {
                'subject': m.subject.name,
                'internal': m.internal,
                'external': m.external,
                'total': m.total,
                'grade': m.grade,
            }
            for m in marks
        ]

        students_data.append({
            'name': student.name,
            'email': student.email,
            'roll_no': student.roll_no,
            'semester': result.semester,
            'sgpa': result.sgpa,
            'cgpa': result.cgpa,
            'marks': marks_data,
        })

    if students_data:
        t = threading.Thread(
            target=_send_in_background,
            args=(app, mail, students_data),
            daemon=True,
        )
        t.start()
        return t, len(students_data), skipped

    return None, 0, skipped


# ─── HTML email builder ───────────────────────────────────────────────────────
def _build_email_html(s):
    rows = ''.join(
        f"""
        <tr>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;">{m['subject']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;text-align:center;">{m['internal']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;text-align:center;">{m['external']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;text-align:center;font-weight:700;">{m['total']}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="background:{'#dcfce7' if m['grade'] not in ('F','E') else '#fee2e2'};
                         color:{'#166534' if m['grade'] not in ('F','E') else '#991b1b'};
                         padding:2px 10px;border-radius:99px;font-weight:700;font-size:13px;">
              {m['grade']}
            </span>
          </td>
        </tr>"""
        for m in s['marks']
    )

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:12px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e3a8a,#2563eb);
                     padding:28px 32px;text-align:center;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:.5px;">
              Annamacharya Institute of Technology and Sciences, Tirupati
            </h1>
            <p style="margin:6px 0 0;color:#bfdbfe;font-size:13px;">
              Semester {s['semester']} Examination Results
            </p>
          </td>
        </tr>

        <!-- Greeting -->
        <tr>
          <td style="padding:28px 32px 16px;">
            <p style="margin:0;font-size:15px;color:#374151;">Dear <strong>{s['name']}</strong>,</p>
            <p style="margin:10px 0 0;font-size:14px;color:#6b7280;line-height:1.6;">
              Your <strong>Semester {s['semester']}</strong> examination results have been officially
              published. Please find the detailed marksheet below.
            </p>
            <p style="margin:8px 0 0;font-size:13px;color:#9ca3af;">Roll Number: {s['roll_no']}</p>
          </td>
        </tr>

        <!-- Marks table -->
        <tr>
          <td style="padding:0 32px 20px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
              <thead>
                <tr style="background:#1e3a8a;color:#ffffff;">
                  <th style="padding:12px 14px;text-align:left;font-size:13px;font-weight:600;">Subject</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;">Internal (30)</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;">External (70)</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;">Total</th>
                  <th style="padding:12px 14px;text-align:center;font-size:13px;font-weight:600;">Grade</th>
                </tr>
              </thead>
              <tbody>{rows}</tbody>
            </table>
          </td>
        </tr>

        <!-- SGPA / CGPA -->
        <tr>
          <td style="padding:0 32px 28px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
                           padding:16px 20px;text-align:center;width:50%;">
                  <p style="margin:0;font-size:12px;color:#3b82f6;font-weight:600;text-transform:uppercase;
                             letter-spacing:.5px;">SGPA</p>
                  <p style="margin:4px 0 0;font-size:28px;font-weight:800;color:#1e3a8a;">{s['sgpa']}</p>
                </td>
                <td width="16"></td>
                <td style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;
                           padding:16px 20px;text-align:center;width:50%;">
                  <p style="margin:0;font-size:12px;color:#16a34a;font-weight:600;text-transform:uppercase;
                             letter-spacing:.5px;">CGPA</p>
                  <p style="margin:4px 0 0;font-size:28px;font-weight:800;color:#166534;">{s['cgpa']}</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Portal CTA -->
        <tr>
          <td style="padding:0 32px 28px;text-align:center;">
            <p style="margin:0 0 14px;font-size:13px;color:#6b7280;">
              You can also view your full result on the college portal using your
              <strong>Roll Number</strong> and <strong>Aadhar Number</strong>.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;border-top:1px solid #e5e7eb;
                     padding:18px 32px;text-align:center;">
            <p style="margin:6px 0 0;font-size:13px;">This is an automated email from the Examination Branch,<br>
              Annamacharya Institute of Technology and Sciences, Tirupati.<br>
              Please do not reply to this email.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
