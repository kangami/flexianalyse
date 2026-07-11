"""Service d'envoi d'emails transactionnels via Resend."""
import os
import logging

logger = logging.getLogger(__name__)

# Adresse d'expédition par défaut (format Resend : "Nom <email>").
DEFAULT_FROM = "FlexiAnalyse <contact@flexianalyse.com>"
REPLY_TO = "contact@flexianalyse.com"
# Destinataire des notifications internes (nouveau lead).
DEFAULT_NOTIFY_TO = "contact@flexianalyse.com"


class EmailService:
    """Envoi d'emails via Resend. Les échecs sont journalisés mais ne lèvent jamais."""

    def __init__(self):
        self._api_key = os.getenv("RESEND_API_KEY")
        self._from = os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM)
        self._notify_to = os.getenv("LEAD_NOTIFICATION_EMAIL", DEFAULT_NOTIFY_TO)

    def _client(self):
        """Retourne le module resend configuré, ou None si indisponible."""
        if not self._api_key:
            return None
        try:
            import resend
        except ImportError:
            logger.error("Le paquet 'resend' n'est pas installé — email ignoré.")
            return None
        resend.api_key = self._api_key
        return resend

    def send_welcome_email(self, to_email: str, first_name: str | None = None) -> bool:
        """Envoie l'email de bienvenue à un nouveau lead. Ne lève jamais d'exception."""
        client = self._client()
        if client is None:
            logger.warning(
                "RESEND_API_KEY absent ou paquet manquant — email de bienvenue non envoyé à %s",
                to_email,
            )
            return False

        name = (first_name or "").strip() or "there"
        try:
            client.Emails.send({
                "from": self._from,
                "to": [to_email],
                "reply_to": REPLY_TO,
                "subject": "Welcome to FlexiAnalyse 👋",
                "html": self._welcome_html(name),
            })
            logger.info("Email de bienvenue envoyé à %s", to_email)
            return True
        except Exception as e:
            logger.error("Échec de l'envoi de l'email de bienvenue à %s: %s", to_email, e)
            return False

    def send_new_lead_notification(self, lead) -> bool:
        """Notifie l'équipe qu'un nouveau lead a été capturé. Ne lève jamais."""
        client = self._client()
        if client is None:
            logger.warning(
                "RESEND_API_KEY absent ou paquet manquant — notification de lead non envoyée."
            )
            return False

        full_name = f"{lead.first_name or ''} {lead.last_name or ''}".strip() or "—"
        try:
            client.Emails.send({
                "from": self._from,
                "to": [self._notify_to],
                "reply_to": lead.work_email,
                "subject": f"New lead: {full_name} ({lead.work_email})",
                "html": self._new_lead_html(lead, full_name),
            })
            logger.info("Notification de nouveau lead envoyée à %s", self._notify_to)
            return True
        except Exception as e:
            logger.error("Échec de l'envoi de la notification de lead: %s", e)
            return False

    @staticmethod
    def _new_lead_html(lead, full_name: str) -> str:
        def row(label: str, value) -> str:
            safe = (str(value).strip() if value else "") or "—"
            return (
                f'<tr>'
                f'<td style="padding:8px 12px;color:#6b7280;font-size:13px;'
                f'white-space:nowrap;vertical-align:top;">{label}</td>'
                f'<td style="padding:8px 12px;color:#1f2937;font-size:14px;">{safe}</td>'
                f'</tr>'
            )

        return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:560px;margin:0 auto;color:#1f2937;">
  <h1 style="font-size:20px;font-weight:800;margin:0 0 4px;">New lead captured 🎉</h1>
  <p style="font-size:14px;color:#6b7280;margin:0 0 20px;">Someone just submitted the Get Started form.</p>
  <table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;">
    {row("Name", full_name)}
    {row("Work email", lead.work_email)}
    {row("Company size", lead.company_size)}
    {row("Country", lead.country)}
    {row("Message", lead.message)}
  </table>
  <p style="font-size:12px;color:#9ca3af;margin:20px 0 0;">Reply to this email to reach the lead directly.</p>
</div>"""

    @staticmethod
    def _welcome_html(name: str) -> str:
        return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:520px;margin:0 auto;color:#1f2937;">
  <h1 style="font-size:22px;font-weight:800;margin:0 0 16px;">Welcome to FlexiAnalyse, {name} 👋</h1>
  <p style="font-size:15px;line-height:1.6;color:#374151;margin:0 0 16px;">
    Thank you for reaching out. We're excited to help you connect your systems and put AI to work across your organization.
  </p>
  <p style="font-size:15px;line-height:1.6;color:#374151;margin:0 0 16px;">
    Our team has received your information and will get back to you shortly. In the meantime, if you have any questions,
    just reply to this email or write to
    <a href="mailto:contact@flexianalyse.com" style="color:#2563eb;text-decoration:none;">contact@flexianalyse.com</a>.
  </p>
  <p style="font-size:15px;line-height:1.6;color:#374151;margin:0 0 24px;">
    Talk soon,<br/>
    <strong>The FlexiAnalyse Team</strong>
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:0 0 16px;"/>
  <p style="font-size:12px;color:#9ca3af;margin:0;">
    FlexiAnalyse — You bring your systems. We make them work together, intelligently.
  </p>
</div>"""
