
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from django.contrib.auth import views as auth_views

# Router para API REST
router = DefaultRouter()
router.register(r'beneficiarios', views.BeneficiariosViewSet)
router.register(r'proyectos', views.ProyectosHabitacionalesViewSet)
router.register(r'postulaciones', views.PostulacionesViewSet)
router.register(r'municipios', views.MunicipiosViewSet)
router.register(r'regiones', views.RegionesViewSet)
router.register(r'empresas', views.EmpresasConstructorasViewSet)
router.register(r'terrenos', views.TerrenosViewSet)
router.register(r'log-auditoria', views.LogAuditoriaViewSet)
router.register(r'notificaciones', views.NotificacionViewSet)
router.register(r'matching', views.MatchingViewSet)

app_name = 'gestion'

urlpatterns = [
    # Vistas web
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
    path('settings/', views.settings_view, name='settings'),
    path('beneficiarios/create/', views.create_beneficiario, name='create_beneficiario'),
    path('proyectos/create/', views.proyecto_create, name='proyecto_create'),
    path('proyectos/<int:pk>/edit/', views.proyecto_edit, name='proyecto_edit'),
    path('beneficiarios/', views.beneficiarios_list, name='beneficiarios_list'),
    path('beneficiarios/<int:pk>/', views.beneficiario_detail, name='beneficiario_detail'),
    path('beneficiarios/<int:pk>/update/', views.beneficiario_update, name='beneficiario_update'),
    path('beneficiarios/<int:pk>/delete/', views.beneficiario_delete, name='beneficiario_delete'),
    path('proyectos/', views.proyectos_list, name='proyectos_list'),
    path('proyectos/<int:pk>/', views.proyecto_detail, name='proyecto_detail'),
    path('proyectos/<int:pk>/postular/', views.postular, name='proyecto_postular'),
    path('postulaciones/<int:pk>/update/', views.postulacion_update, name='postulacion_update'),
    path('postulaciones/', views.postulaciones_list, name='postulaciones_list'),
    path('reportes/', views.reportes, name='reportes'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/events/', views.events_api, name='events_api'),
    
    # Rutas explícitas que deben evaluarse antes del router DRF
    path('api/matching/ejecutar/', views.ejecutar_matching_api, name='ejecutar_matching_api'),
    path('api/matching/<int:matching_id>/aprobar/', views.aprobar_matching_api, name='aprobar_matching_api'),
    path('api/matching/<int:matching_id>/rechazar/', views.rechazar_matching_api, name='rechazar_matching_api'),

    # API REST (router)
    path('api/', include(router.urls)),
    path('api/dashboard/', views.dashboard_api, name='dashboard_api'),
]

