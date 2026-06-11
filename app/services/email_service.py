"""
TrainSMART Email Service
Sends email notifications for account creation and certificate issuance.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"TrainSMART NASCOP <{settings.EMAIL_FROM}>"
        msg['To']      = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_FROM, settings.EMAIL_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        print(f"[EMAIL] Sent '{subject}' to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send to {to_email}: {e}")
        return False


def send_welcome_email(
    to_email: str, full_name: str, username: str,
    password: str, role: str, county: str,
) -> bool:
    role_labels = {
        'ROLE_TRAINER':        'Field Trainer',
        'ROLE_COUNTY_OFFICER': 'County Training Officer',
        'ROLE_NATIONAL_ADMIN': 'National Administrator',
        'ROLE_ME_MANAGER':     'M&E Manager',
        'ROLE_TRAINEE':        'Healthcare Worker / Trainee',
        'ROLE_SYSTEM_ADMIN':   'System Administrator',
    }
    role_label = role_labels.get(role, role)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<div style="background:linear-gradient(135deg,#006600,#008800);padding:0;">
  <div style="height:4px;background:linear-gradient(90deg,#006600 33%,#bb0000 33%,#bb0000 66%,#ffffff 66%)"></div>
  <div style="padding:32px 40px;">
    <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:900;">Train<span style="color:#90EE90;">SMART</span></h1>
    <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:2px;text-transform:uppercase;">National Healthcare Training Registry · NASCOP · MOH Kenya</p>
  </div>
</div>
<div style="max-width:560px;margin:0 auto;padding:32px 24px;">
  <div style="background:#ffffff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <p style="margin:0 0 8px;font-size:13px;color:#666;">Dear {full_name},</p>
    <h2 style="margin:0 0 20px;font-size:20px;color:#1a1a1a;font-weight:800;">Your TrainSMART account is ready</h2>
    <p style="margin:0 0 24px;font-size:13px;color:#555;line-height:1.7;">A TrainSMART account has been created for you. Use the credentials below to sign in.</p>
    <div style="background:#f8fffe;border:1px solid #c3e6d5;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#006600;">Your Login Credentials</p>
      <table style="width:100%;margin-top:12px;border-collapse:collapse;">
        <tr><td style="padding:6px 0;font-size:12px;color:#888;width:160px;">Username</td><td style="padding:6px 0;font-size:14px;font-weight:700;font-family:monospace;">{username}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">Temporary Password</td><td style="padding:6px 0;font-size:14px;font-weight:700;font-family:monospace;">{password}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">Role</td><td style="padding:6px 0;font-size:13px;color:#006600;font-weight:600;">{role_label}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">County</td><td style="padding:6px 0;font-size:13px;">{county}</td></tr>
      </table>
    </div>
    <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:14px 18px;margin-bottom:24px;">
      <p style="margin:0;font-size:12px;color:#b8860b;line-height:1.6;"><strong>⚠ Important:</strong> Please change your password immediately after your first login. Click the <strong>Password</strong> button at the top right of your dashboard.</p>
    </div>
    <div style="text-align:center;margin-bottom:24px;">
      <a href="http://localhost:5173" style="display:inline-block;background:linear-gradient(135deg,#006600,#008800);color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:13px;font-weight:800;letter-spacing:1px;text-transform:uppercase;">Sign In to TrainSMART →</a>
    </div>
    <p style="margin:0;font-size:12px;color:#999;line-height:1.7;text-align:center;">If you did not expect this email, please contact your System Administrator immediately.</p>
  </div>
  <div style="text-align:center;padding:20px 0;">
    <p style="margin:0;font-size:10px;color:#aaa;">TrainSMART · NASCOP · Ministry of Health Kenya · nhcsc.nascop.org</p>
    <p style="margin:4px 0 0;font-size:10px;color:#ccc;">This is an automated message. Please do not reply.</p>
  </div>
</div>
</body></html>"""
    return _send_email(to_email, "Your TrainSMART Account Has Been Created", html)


def send_certificate_email(
    to_email: str, full_name: str, course_title: str,
    certificate_serial: str, county: str, facility: str,
) -> bool:
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
<div style="background:linear-gradient(135deg,#006600,#008800);padding:0;">
  <div style="height:4px;background:linear-gradient(90deg,#006600 33%,#bb0000 33%,#bb0000 66%,#ffffff 66%)"></div>
  <div style="padding:32px 40px;">
    <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:900;">Train<span style="color:#90EE90;">SMART</span></h1>
    <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:2px;text-transform:uppercase;">National Healthcare Training Registry · NASCOP · MOH Kenya</p>
  </div>
</div>
<div style="max-width:560px;margin:0 auto;padding:32px 24px;">
  <div style="background:#ffffff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
    <p style="margin:0 0 8px;font-size:13px;color:#666;">Dear {full_name},</p>
    <h2 style="margin:0 0 20px;font-size:20px;color:#1a1a1a;font-weight:800;">🎓 Your Training Certificate is Ready</h2>
    <p style="margin:0 0 24px;font-size:13px;color:#555;line-height:1.7;">Congratulations! Your certificate has been issued and is now available on the TrainSMART portal.</p>
    <div style="background:#f8fffe;border:1px solid #c3e6d5;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
      <p style="margin:0 0 4px;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#006600;">Certificate Details</p>
      <table style="width:100%;margin-top:12px;border-collapse:collapse;">
        <tr><td style="padding:6px 0;font-size:12px;color:#888;width:160px;">Training Course</td><td style="padding:6px 0;font-size:13px;font-weight:700;">{course_title}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">Certificate Serial</td><td style="padding:6px 0;font-size:14px;font-weight:900;color:#006600;font-family:monospace;">{certificate_serial}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">Facility</td><td style="padding:6px 0;font-size:13px;">{facility}</td></tr>
        <tr><td style="padding:6px 0;font-size:12px;color:#888;">County</td><td style="padding:6px 0;font-size:13px;">{county}</td></tr>
      </table>
    </div>
    <div style="text-align:center;margin-bottom:24px;">
      <a href="http://localhost:5173" style="display:inline-block;background:linear-gradient(135deg,#006600,#008800);color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:13px;font-weight:800;letter-spacing:1px;text-transform:uppercase;">View & Print Certificate →</a>
    </div>
    <p style="margin:0;font-size:12px;color:#999;line-height:1.7;text-align:center;">Log in to TrainSMART and go to your dashboard to view and print your certificate.</p>
  </div>
  <div style="text-align:center;padding:20px 0;">
    <p style="margin:0;font-size:10px;color:#aaa;">TrainSMART · NASCOP · Ministry of Health Kenya · nhcsc.nascop.org</p>
    <p style="margin:4px 0 0;font-size:10px;color:#ccc;">This is an automated message. Please do not reply.</p>
  </div>
</div>
</body></html>"""
    return _send_email(to_email, f"Your TrainSMART Certificate — {course_title}", html)