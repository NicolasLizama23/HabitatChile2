from django.contrib import admin
from .models import *
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(Regiones)
class RegionesAdmin(admin.ModelAdmin):
    list_display = ['id_region', 'nombre_region', 'codigo_region', 'capital_regional']
    search_fields = ['nombre_region', 'codigo_region']


@admin.register(Municipios)
class MunicipiosAdmin(admin.ModelAdmin):
    list_display = ['id_municipio', 'nombre_municipio', 'codigo_municipio', 'id_region', 'poblacion']
    list_filter = ['id_region']
    search_fields = ['nombre_municipio', 'codigo_municipio']


@admin.register(Beneficiarios)
class BeneficiariosAdmin(admin.ModelAdmin):
    list_display = ['id_beneficiario', 'rut', 'nombre', 'apellidos', 'estado_beneficiario', 'puntaje_socioeconomico', 'fecha_registro']
    list_filter = ['estado_beneficiario', 'estado_civil', 'id_municipio']
    search_fields = ['rut', 'nombre', 'apellidos', 'email']
    date_hierarchy = 'fecha_registro'


@admin.register(EmpresasConstructoras)
class EmpresasConstructorasAdmin(admin.ModelAdmin):
    list_display = ['id_empresa', 'rut_empresa', 'razon_social', 'estado_empresa', 'años_experiencia', 'capacidad_construccion_anual']
    list_filter = ['estado_empresa', 'certificacion_industrializada']
    search_fields = ['rut_empresa', 'razon_social']


@admin.register(Terrenos)
class TerrenosAdmin(admin.ModelAdmin):
    list_display = ['id_terreno', 'direccion', 'id_municipio', 'superficie_total', 'estado_terreno', 'precio_m2']
    list_filter = ['estado_terreno', 'id_municipio']
    search_fields = ['direccion', 'coordenadas_gps']


@admin.register(ProyectosHabitacionales)
class ProyectosHabitacionalesAdmin(admin.ModelAdmin):
    list_display = ['id_proyecto', 'nombre_proyecto', 'id_municipio', 'numero_viviendas', 'estado_proyecto', 'latitud', 'longitud', 'fecha_inicio']
    list_filter = ['estado_proyecto', 'tipo_vivienda', 'id_municipio']
    search_fields = ['nombre_proyecto', 'descripcion']
    date_hierarchy = 'fecha_inicio'
    actions = ['geocode_selected_projects']

    def geocode_selected_projects(self, request, queryset):
        """Admin action: geocode selected projects using Terreno.direccion or municipio+nombre."""
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent='pjrEjemplo-admin-geocode')
        updated = 0
        for p in queryset:
            if p.latitud and p.longitud:
                continue
            q = None
            if p.id_terreno and p.id_terreno.direccion:
                q = f"{p.id_terreno.direccion}, {p.id_municipio.nombre_municipio if p.id_municipio else ''}, Chile"
            else:
                # fallback: municipio + nombre de proyecto
                municipio = p.id_municipio.nombre_municipio if p.id_municipio else ''
                q = f"{p.nombre_proyecto}, {municipio}, Chile"
            try:
                loc = geolocator.geocode(q, timeout=10)
                if loc:
                    p.latitud = round(loc.latitude, 6)
                    p.longitud = round(loc.longitude, 6)
                    p.save()
                    updated += 1
            except Exception:
                # ignorar errores individuales
                continue
        self.message_user(request, f"Geocodificados: {updated} proyectos (si los datos estaban disponibles)")
    geocode_selected_projects.short_description = 'Geocodificar proyectos seleccionados (Nominatim)'


@admin.register(Postulaciones)
class PostulacionesAdmin(admin.ModelAdmin):
    list_display = ['id_postulacion', 'id_beneficiario', 'id_proyecto', 'estado_postulacion', 'puntaje_asignado', 'fecha_postulacion']
    list_filter = ['estado_postulacion', 'fecha_postulacion']
    search_fields = ['id_beneficiario__nombre', 'id_beneficiario__apellidos', 'id_proyecto__nombre_proyecto']
    date_hierarchy = 'fecha_postulacion'


@admin.register(Instituciones)
class InstitucionesAdmin(admin.ModelAdmin):
    list_display = ['id_institucion', 'nombre_institucion', 'tipo_institucion', 'rut_institucion']
    list_filter = ['tipo_institucion']
    search_fields = ['nombre_institucion', 'rut_institucion']


@admin.register(UsuariosSistema)
class UsuariosSistemaAdmin(admin.ModelAdmin):
    list_display = ['id_usuario', 'username', 'nombre', 'apellidos', 'tipo_usuario', 'estado_usuario', 'fecha_ultimo_acceso']
    list_filter = ['tipo_usuario', 'estado_usuario', 'id_institucion']
    search_fields = ['username', 'email', 'nombre', 'apellidos']

# Register your models here.

# Mostrar y poder editar el UserProfile desde el admin del User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfiles de usuario'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


# Re-register User admin con el inline de UserProfile
try:
    admin.site.unregister(User)
except Exception:
    pass

admin.site.register(User, CustomUserAdmin)


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'id_usuario', 'accion', 'tabla', 'registro_afectado']
    list_filter = ['accion', 'tabla', 'timestamp']
    search_fields = ['id_usuario__username', 'accion']
    readonly_fields = ['timestamp']


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['id_usuario', 'tipo', 'fecha_envio', 'leida']
    list_filter = ['tipo', 'leida', 'fecha_envio']
    search_fields = ['id_usuario__username', 'mensaje']


@admin.register(Matching)
class MatchingAdmin(admin.ModelAdmin):
    list_display = ['id_beneficiario', 'id_proyecto', 'puntaje_compatibilidad', 'estado', 'fecha_matching']
    list_filter = ['estado', 'fecha_matching']
    search_fields = ['id_beneficiario__nombre', 'id_proyecto__nombre_proyecto']
    readonly_fields = ['fecha_matching']


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['id_evento', 'titulo', 'tipo', 'fecha_inicio', 'fecha_fin', 'proyecto']
    list_filter = ['tipo', 'fecha_inicio']
    search_fields = ['titulo', 'descripcion', 'ubicacion']
    filter_horizontal = ('asignados',)
