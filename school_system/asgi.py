import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import core.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_system.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(
        core.routing.websocket_urlpatterns
    )
})
