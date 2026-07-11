"""Logique métier — Leads (formulaire Get Started)."""
import re
from models.lead import Lead
from services.email_service import EmailService


# ─── Free email domains (non-company) ────────────────────────────────────────
FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'yahoo.fr', 'hotmail.com', 'hotmail.fr',
    'outlook.com', 'live.com', 'aol.com', 'icloud.com', 'me.com',
    'mail.com', 'protonmail.com', 'proton.me', 'zoho.com', 'yandex.com',
    'gmx.com', 'gmx.fr', 'free.fr', 'orange.fr', 'wanadoo.fr',
    'laposte.net', 'sfr.fr', 'msn.com', 'comcast.net', 'att.net',
    'verizon.net', 'qq.com', '163.com', '126.com', 'inbox.com',
    'mail.ru', 'tutanota.com', 'fastmail.com', 'hey.com',
}

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class LeadService:
    def __init__(self, locator):
        self._loc = locator
        self._email = EmailService()

    # ─── Validation helpers ───────────────────────────────────────────────────

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        return bool(EMAIL_REGEX.match(email))

    @staticmethod
    def _is_company_email(email: str) -> bool:
        """Return True if the email domain is NOT a free provider."""
        try:
            domain = email.strip().lower().split('@')[1]
            return domain not in FREE_EMAIL_DOMAINS
        except (IndexError, AttributeError):
            return False

    # ─── Public API ───────────────────────────────────────────────────────────

    def submit(self, first_name: str, last_name: str, work_email: str,
               company_size: str | None = None, country: str | None = None,
               message: str | None = None) -> dict:
        """
        Validate and save a new lead.
        Returns a dict with keys: exists (bool), message (str), lead_id (str|None).
        Raises ValueError on validation failure.
        """
        # Clean inputs
        first_name = (first_name or '').strip()
        last_name = (last_name or '').strip()
        work_email = (work_email or '').strip().lower()
        company_size = (company_size or '').strip() or None
        country = (country or '').strip() or None
        message = (message or '').strip() or None

        # Required fields
        if not first_name or not last_name or not work_email:
            raise ValueError("firstName, lastName, and workEmail are required")

        # Email format
        if not self._is_valid_email(work_email):
            raise ValueError("Invalid email format")

        # Company email check
        if not self._is_company_email(work_email):
            raise ValueError("Please use a company email address (not personal like Gmail, Yahoo, etc.)")

        # Check duplicate
        existing = self._loc.leads.get_by_email(work_email)
        if existing:
            return {
                'exists': True,
                'message': 'We already have your information — we will connect with you ASAP!',
                'lead_id': str(existing.id),
            }

        # Create
        lead = Lead(
            first_name=first_name,
            last_name=last_name,
            work_email=work_email,
            company_size=company_size,
            country=country,
            message=message,
        )
        created = self._loc.leads.create(lead)

        # Emails (échec silencieux — ne bloque jamais la soumission) :
        #  - bienvenue au lead, - notification à l'équipe.
        self._email.send_welcome_email(work_email, first_name)
        self._email.send_new_lead_notification(created)

        return {
            'exists': False,
            'message': 'Thank you! Our team will reach out shortly.',
            'lead_id': str(created.id),
        }
