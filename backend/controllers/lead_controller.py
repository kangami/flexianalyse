"""Routes — Leads (Get Started form)."""
import logging
from flask import request, jsonify
from services import locator, LeadService

logger = logging.getLogger(__name__)

lead_service = LeadService(locator)


def register(api_bp):
    @api_bp.route("/leads", methods=["POST"])
    def submit_lead():
        data = request.get_json() or {}

        first_name = data.get("firstName")
        last_name = data.get("lastName")
        work_email = data.get("workEmail")
        company_size = data.get("companySize")
        country = data.get("country")
        message = data.get("message")

        try:
            result = lead_service.submit(
                first_name=first_name,
                last_name=last_name,
                work_email=work_email,
                company_size=company_size,
                country=country,
                message=message,
            )
            status_code = 200 if result['exists'] else 201
            return jsonify(result), status_code
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.error(f"Error saving lead: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500
