"""Email (SMTP) alert provider."""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Optional

from app.alerts import AlertProvider, AlertResult, register_provider


class EmailProvider(AlertProvider):
    """SMTP email alert provider."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.host = config.get("host")
        self.port = config.get("port", 587)
        self.username = config.get("username")
        self.password = config.get("password")
        self.from_addr = config.get("from_addr", self.username)
        self.to_addr = config.get("to_addr")

    async def send(
        self,
        incident_data: dict,
        image_bytes: Optional[bytes] = None,
    ) -> AlertResult:
        if not self.enabled:
            return AlertResult(False, "email", self.to_addr, "Provider disabled")

        if not all([self.host, self.username, self.password, self.to_addr]):
            return AlertResult(False, "email", self.to_addr, "Incomplete SMTP config")

        subject, message = self._build_message(incident_data)

        try:
            msg = MIMEMultipart("related")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = self.to_addr

            # HTML body with inline image
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #dc2626;">🔥 PyroGuard Fire & Smoke Alert</h2>
                <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                    <tr><td style="padding: 8px;"><strong>Camera:</strong></td><td style="padding: 8px;">{incident_data.get('camera_name', incident_data.get('camera_id', 'unknown'))}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Type:</strong></td><td style="padding: 8px;">{incident_data.get('class_name', 'unknown').capitalize()}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Severity:</strong></td><td style="padding: 8px;"><span style="color: {self._severity_color(incident_data.get('severity'))}; font-weight: bold;">{incident_data.get('severity', 'unknown').upper()}</span></td></tr>
                    <tr><td style="padding: 8px;"><strong>Confidence:</strong></td><td style="padding: 8px;">{incident_data.get('confidence', 0):.1%}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Detected:</strong></td><td style="padding: 8px;">{incident_data.get('detected_at', 'unknown')}</td></tr>
                    <tr><td style="padding: 8px;"><strong>Incident ID:</strong></td><td style="padding: 8px;">{incident_data.get('id', 'pending')}</td></tr>
                </table>
                {"<p><img src='cid:detection_image' style='max-width: 100%; border-radius: 8px;'></p>" if image_bytes else ""}
                <hr>
                <p style="color: #666; font-size: 12px;">This is an automated alert from PyroGuard. Do not reply.</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(message, "plain"))
            msg.attach(MIMEText(html, "html"))

            # Attach image if provided
            if image_bytes:
                img = MIMEImage(image_bytes)
                img.add_header("Content-ID", "<detection_image>")
                img.add_header("Content-Disposition", "inline", filename="detection.jpg")
                msg.attach(img)

            # Send via SMTP with STARTTLS
            context = ssl.create_default_context()
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)

            return AlertResult(True, "email", self.to_addr)

        except smtplib.SMTPAuthenticationError as e:
            return AlertResult(False, "email", self.to_addr, f"SMTP auth failed: {e}")
        except smtplib.SMTPException as e:
            return AlertResult(False, "email", self.to_addr, f"SMTP error: {e}")
        except Exception as e:
            return AlertResult(False, "email", self.to_addr, f"Unexpected error: {e}")

    def _severity_color(self, severity: str) -> str:
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#ca8a04",
            "low": "#16a34a",
        }
        return colors.get(severity.lower(), "#666")


register_provider("email", EmailProvider)