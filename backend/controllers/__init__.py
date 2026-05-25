from flask import Blueprint, request
from typing import Optional
from services import locator
from controllers.organization_controller import register as _register_orgs
from controllers.department_controller import register as _register_depts
from controllers.user_controller import register as _register_users
from controllers.role_controller import register as _register_roles
from controllers.skeleton_controller import register as _register_skeletons

api_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")


def init_app():
    from config.db import db
    db.init_pool()
    locator.init_db(db)


def get_current_user_id() -> Optional[str]:
    return request.headers.get("X-User-Id")


def get_current_organization_id() -> Optional[str]:
    return request.headers.get("X-Organization-Id")


def register_all():
    _register_orgs(api_bp)
    _register_depts(api_bp)
    _register_users(api_bp)
    _register_roles(api_bp)
    _register_skeletons(api_bp)


register_all()
