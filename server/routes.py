from flask import Blueprint
from server.oauth import handle_oauth2_callback

routes = Blueprint('routes', __name__)

@routes.route('/oauth2callback')
def oauth2callback():
    """Маршрут для обработки авторизации через OAuth2."""
    return handle_oauth2_callback()
