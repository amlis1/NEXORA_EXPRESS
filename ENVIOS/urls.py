from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.register_view, name="register"),
    path("crear-envio/", views.crear_envio, name="crear_envio"),
    path("mis-envios/", views.mis_envios, name="mis_envios"),
    path("rastrear/", views.rastrear_envio, name="rastrear_envio"),
    path("rastrear/<str:tracking_code>/", views.rastrear_envio, name="rastrear_envio_codigo"),
    path("panel/envios/", views.admin_envios, name="admin_envios"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("panel/envio/<int:envio_id>/actualizar/", views.admin_actualizar_envio, name="admin_actualizar_envio"),
    path("panel/envio/<int:envio_id>/eliminar/", views.eliminar_envio, name="eliminar_envio"),
    path("panel/envio/<int:envio_id>/reenviar/", views.reenviar_guia, name="reenviar_guia"),
    path("pdf/<str:tracking_code>/", views.descargar_guia_pdf, name="descargar_guia_pdf"),
    path("panel/reporte-ingresos/", views.reporte_ingresos_pdf, name="reporte_ingresos_pdf"),
]

