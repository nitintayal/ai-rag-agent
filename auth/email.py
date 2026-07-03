"""Send emails via Resend."""

import logging

logger = logging.getLogger(__name__)

APP_NAME = "AI Personal Assistant"


def _get_client():
    from configs.config import settings
    if not settings.RESEND_API_KEY:
        return None
    import resend
    resend.api_key = settings.RESEND_API_KEY
    return resend


def send_verification_email(to_email: str, code: str, frontend_url: str = "") -> bool:
    resend = _get_client()
    if not resend:
        logger.warning(f"No RESEND_API_KEY — verification code for {to_email}: {code}")
        return False

    from configs.config import settings
    verify_link = f"{frontend_url}?verify_email={to_email}&code={code}" if frontend_url else ""

    try:
        resend.Emails.send({
            "from": f"{APP_NAME} <{settings.RESEND_FROM_EMAIL}>",
            "to": to_email,
            "subject": f"Verify your email — {APP_NAME}",
            "html": f"""
            <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
                <h2 style="color: #0f172a;">Verify your email</h2>
                <p style="color: #475569; line-height: 1.6;">
                    Thanks for signing up for {APP_NAME}. Click the button below to verify your email address.
                </p>
                {f'<a href="{verify_link}" style="display: inline-block; background: #0f172a; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 16px 0;">Verify Email</a>' if verify_link else ''}
                <p style="color: #94a3b8; font-size: 13px; margin-top: 24px;">
                    If the button doesn't work, use this code: <strong>{code}</strong>
                </p>
                <p style="color: #cbd5e1; font-size: 12px; margin-top: 32px;">
                    This code expires in 1 hour. If you didn't create an account, ignore this email.
                </p>
            </div>
            """,
        })
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


def send_task_reminder_email(to_email: str, name: str, tasks: list) -> bool:
    resend = _get_client()
    if not resend:
        logger.warning(f"No RESEND_API_KEY — skipping reminder for {to_email}")
        return False

    from configs.config import settings

    def _task_row(t):
        due = t.get("due_date", "")
        overdue = due and due < __import__("datetime").date.today().isoformat()
        label = f'<span style="color:{"#dc2626" if overdue else "#d97706"};font-weight:600;">{"⚠ Overdue" if overdue else "Due today"}</span>'
        return f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #f1f5f9;">
            <strong style="color:#0f172a;">{t.get("title","")}</strong><br>
            <span style="font-size:13px;color:#64748b;">{label} · {due} · {t.get("priority","medium")} priority</span>
          </td>
        </tr>"""

    rows = "".join(_task_row(t) for t in tasks)
    try:
        resend.Emails.send({
            "from": f"{APP_NAME} <{settings.RESEND_FROM_EMAIL}>",
            "to": to_email,
            "subject": f"📋 {len(tasks)} task{'s' if len(tasks) != 1 else ''} due today — {APP_NAME}",
            "html": f"""
            <div style="font-family:-apple-system,sans-serif;max-width:520px;margin:0 auto;padding:40px 20px;">
              <h2 style="color:#0f172a;margin-bottom:4px;">Hi {name},</h2>
              <p style="color:#475569;line-height:1.6;margin-top:8px;">
                You have <strong>{len(tasks)}</strong> task{'s' if len(tasks) != 1 else ''} due today or overdue.
              </p>
              <table style="width:100%;border-collapse:collapse;margin:20px 0;">
                {rows}
              </table>
              <a href="{settings.FRONTEND_URL}" style="display:inline-block;background:#0f172a;color:white;
                 padding:12px 24px;border-radius:8px;text-decoration:none;margin-top:8px;">
                Open Task Manager
              </a>
              <p style="color:#cbd5e1;font-size:12px;margin-top:32px;">
                You're receiving this because you have tasks due in {APP_NAME}.
              </p>
            </div>""",
        })
        logger.info(f"Task reminder sent to {to_email} ({len(tasks)} tasks)")
        return True
    except Exception as e:
        logger.error(f"Failed to send task reminder: {e}")
        return False


def send_password_reset_email(to_email: str, code: str, frontend_url: str = "") -> bool:
    resend = _get_client()
    if not resend:
        logger.warning(f"No RESEND_API_KEY — reset code for {to_email}: {code}")
        return False

    from configs.config import settings
    reset_link = f"{frontend_url}?reset_email={to_email}&code={code}" if frontend_url else ""

    try:
        resend.Emails.send({
            "from": f"{APP_NAME} <{settings.RESEND_FROM_EMAIL}>",
            "to": to_email,
            "subject": f"Reset your password — {APP_NAME}",
            "html": f"""
            <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px;">
                <h2 style="color: #0f172a;">Reset your password</h2>
                <p style="color: #475569; line-height: 1.6;">
                    We received a request to reset your password. Click the button below to set a new one.
                </p>
                {f'<a href="{reset_link}" style="display: inline-block; background: #0f172a; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 16px 0;">Reset Password</a>' if reset_link else ''}
                <p style="color: #94a3b8; font-size: 13px; margin-top: 24px;">
                    If the button doesn't work, use this code: <strong>{code}</strong>
                </p>
                <p style="color: #cbd5e1; font-size: 12px; margin-top: 32px;">
                    This code expires in 1 hour. If you didn't request a reset, ignore this email.
                </p>
            </div>
            """,
        })
        logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")
        return False
