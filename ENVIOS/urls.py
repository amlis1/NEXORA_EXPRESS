from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.register_view, name="register"),
    path("crear-envio/", views.crear_envio, name="crear_envio"),
    path("mis-envios/", views.mis_envios, name="mis_envios"),
    path("panel/envios/", views.admin_envios, name="admin_envios"),
    path("panel/envio/<int:envio_id>/actualizar/", views.admin_actualizar_envio, name="admin_actualizar_envio"),
]
