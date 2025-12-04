from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Avg, Sum, Q
from rest_framework import viewsets, filters, status
from rest_framework import permissions
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import *
from .serializers import *
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from django.urls import reverse
from django.views.decorators.http import require_POST
import datetime
import calendar
from .matching_algorithm import MatchingAlgorithm
from .models import LogAuditoria, Notificacion
import folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# ===== VISTAS WEB (Templates) =====

from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token

from django.views.decorators.csrf import csrf_protect
from django.template.context_processors import csrf
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotAllowed
from django.views.decorators.http import require_http_methods
import json


# Helper: normalizar roles a claves canónicas usadas por frontend/backend
def _canonical_role_from_string(raw):
    if not raw:
        return None
    try:
        r = str(raw).strip().lower()
    except Exception:
        return None
    role_map = {
        'empresa_constructora': 'empresa',
        'empresa': 'empresa',
        'beneficiario': 'beneficiario',
        'beneficiarios': 'beneficiario',
        'jefe_proyecto': 'jefe_proyecto',
        'jefe': 'jefe_proyecto',
        'ministro': 'ministro',
        'admin': 'admin',
        'superuser': 'admin',
        'usuario': 'usuario',
    }
    return role_map.get(r, r)


@login_required
def notifications(request):
    """Vista mínima de notificaciones (placeholder).

    Por ahora devuelve una lista estática para poder mostrar la UI. Se puede
    reemplazar luego por un modelo real Notification y APIs.
    """
    notifs = [
        { 'id': 1, 'title': 'Bienvenido', 'body': 'Gracias por usar el sistema', 'read': False },
    ]
    context = {'notifications': notifs}
    return render(request, 'gestion/notifications.html', context)


@login_required
def settings_view(request):
    """Página mínima de configuración de usuario (placeholder)."""
    if request.method == 'POST':
        # Procesar cambios mínimos y notificar al usuario
        messages.success(request, 'Configuración guardada')
        return redirect('gestion:settings')
    return render(request, 'gestion/settings.html')


@login_required
def reportes(request):
    """Página de reportes mínima (placeholder)."""
    # Aquí puedes agregar lógica para generar reportes reales o dashboards.
    context = {}
    return render(request, 'gestion/reportes.html', context)

@ensure_csrf_cookie
@csrf_protect
def login_view(request):
    """Vista de login con manejo específico de CSRF y validación mejorada."""
    
    # Si el usuario ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('gestion:dashboard')
    
    context = {}
    context.update(csrf(request))
    
    if request.method == 'GET':
        # Generar nuevo token CSRF en cada visita a la página de login
        token = get_token(request)
        request.session['csrf_token'] = token
        
        # Si hay un mensaje de "next", mostrarlo
        next_url = request.GET.get('next')
        if next_url:
            messages.info(request, 'Por favor inicia sesión para acceder a esa página')
    
    elif request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember') == 'on'
        
        if not username or not password:
            messages.error(request, 'Por favor completa todos los campos')
        else:
            user = authenticate(request=request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Configurar la sesión según la opción "recordar"
                    if not remember:
                        request.session.set_expiry(0)
                    
                    # Regenerar token CSRF después del login
                    get_token(request)
                    
                    # Redireccionar a next_url o dashboard
                    next_url = request.GET.get('next') or 'gestion:dashboard'
                    return redirect(next_url)
                else:
                    messages.error(request, 'Tu cuenta está desactivada')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
    
    # Asegurar que el token está en el contexto
    if 'csrf_token' not in context:
        context['csrf_token'] = get_token(request)
    
    return render(request, 'registration/login.html', context)

@login_required
def dashboard(request):
    """Dashboard principal con estadísticas (requiere login)"""
    from django.utils import timezone
    import datetime
    
    try:
        # Estadísticas generales con manejo de errores
        total_beneficiarios = Beneficiarios.objects.count()
        total_proyectos = ProyectosHabitacionales.objects.count()
        total_postulaciones = Postulaciones.objects.count()
        total_empresas = EmpresasConstructoras.objects.count()
    except:
        total_beneficiarios = 0
        total_proyectos = 0
        total_postulaciones = 0
        total_empresas = 0
    
    # Estadísticas de beneficiarios por estado
    beneficiarios_por_estado = dict(
        Beneficiarios.objects.values('estado_beneficiario')
        .annotate(total=Count('id_beneficiario'))
        .values_list('estado_beneficiario', 'total')
    )
    
    # Proyectos por estado
    proyectos_por_estado = dict(
        ProyectosHabitacionales.objects.values('estado_proyecto')
        .annotate(total=Count('id_proyecto'))
        .values_list('estado_proyecto', 'total')
    )
    
    # Postulaciones recientes
    postulaciones_recientes = Postulaciones.objects.select_related(
        'id_beneficiario', 'id_proyecto'
    ).order_by('-fecha_postulacion')[:10]
    
    # Proyectos activos con cálculo de progreso
    proyectos_activos = ProyectosHabitacionales.objects.filter(
        estado_proyecto__in=['En Planificación', 'En Construcción', 'Activo', 'Terminado']
    ).select_related('id_municipio', 'id_empresa_constructora')[:5]
    
    for proyecto in proyectos_activos:
        if proyecto.estado_proyecto == 'Terminado':
            proyecto.progreso = 100
        elif proyecto.estado_proyecto == 'En Construcción':
            proyecto.progreso = 50
        elif proyecto.estado_proyecto == 'En Planificación':
            proyecto.progreso = 25
        else:
            proyecto.progreso = 0
    
    # Distribución regional
    distribucion_regional = Beneficiarios.objects.values(
        'id_municipio__id_region__nombre_region'
    ).annotate(total=Count('id_beneficiario')).order_by('-total')[:10]
    # Datos para gráficos: beneficiarios por estado y proyectos por estado (ya dicts)
    beneficiarios_por_estado = dict(
        Beneficiarios.objects.values('estado_beneficiario')
        .annotate(total=Count('id_beneficiario'))
        .values_list('estado_beneficiario', 'total')
    )

    proyectos_por_estado = dict(
        ProyectosHabitacionales.objects.values('estado_proyecto')
        .annotate(total=Count('id_proyecto'))
        .values_list('estado_proyecto', 'total')
    )

    # Tendencia de postulaciones: últimos 10 meses
    today = datetime.date.today()
    months = []
    month_labels = []
    postulaciones_counts = []
    # generar de 9 meses atrás hasta este mes
    for i in range(9, -1, -1):
        # calcular año/mes
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))
        month_labels.append(calendar.month_abbr[m])
        c = Postulaciones.objects.filter(fecha_postulacion__year=y, fecha_postulacion__month=m).count()
        postulaciones_counts.append(c)
    
    # Estadísticas adicionales
    viviendas_entregadas = ProyectosHabitacionales.objects.filter(estado_proyecto='Terminado').aggregate(total=Sum('numero_viviendas'))['total'] or 0
    postulaciones_aprobadas = Postulaciones.objects.filter(estado_postulacion='Aprobada').count()
    postulaciones_revision = Postulaciones.objects.filter(estado_postulacion='Pendiente').count()
    casos_atencion = Postulaciones.objects.filter(estado_postulacion='Requiere Atención').count()
    
    # Top municipios por beneficiarios
    top_municipios = []
    municipios_data = Beneficiarios.objects.values('id_municipio__nombre_municipio').annotate(
        total=Count('id_beneficiario')
    ).order_by('-total')[:5]
    
    max_beneficiarios = max([m['total'] for m in municipios_data]) if municipios_data else 1
    for m in municipios_data:
        top_municipios.append({
            'nombre': m['id_municipio__nombre_municipio'],
            'total': m['total'],
            'porcentaje': (m['total'] / max_beneficiarios) * 100
        })

    # Actividades recientes con manejo seguro de valores nulos
    actividades_recientes = []
    
    # Últimas postulaciones
    postulaciones = Postulaciones.objects.select_related('id_beneficiario', 'id_proyecto').order_by('-fecha_postulacion')[:3]
    for p in postulaciones:
        beneficiario_nombre = f"{p.id_beneficiario.nombre} {p.id_beneficiario.apellidos}" if p.id_beneficiario else "Beneficiario no especificado"
        proyecto_nombre = p.id_proyecto.nombre_proyecto if p.id_proyecto else "Proyecto no especificado"
        actividades_recientes.append({
            'descripcion': f"Nueva postulación de {beneficiario_nombre} para {proyecto_nombre}",
            'fecha': p.fecha_postulacion or datetime.date.today(),
            'icon': 'file-earmark-text'
        })

    # Últimos beneficiarios registrados
    beneficiarios = Beneficiarios.objects.order_by('-fecha_registro')[:3]
    for b in beneficiarios:
        actividades_recientes.append({
            'descripcion': f"Nuevo beneficiario registrado: {b.nombre} {b.apellidos}",
            'fecha': b.fecha_registro,
            'icon': 'person-plus'
        })

    # Últimos proyectos
    proyectos = ProyectosHabitacionales.objects.order_by('-fecha_inicio')[:3]
    for p in proyectos:
        actividades_recientes.append({
            'descripcion': f"Nuevo proyecto: {p.nombre_proyecto}",
            'fecha': p.fecha_inicio,
            'icon': 'building'
        })

    # Ordenar actividades por fecha
    actividades_recientes = sorted(
        [a for a in actividades_recientes if a['fecha']], 
        key=lambda x: x['fecha'], 
        reverse=True
    )[:5]

    # determinar rol canónico del usuario (usar UsuariosSistema.tipo_usuario si existe)
    raw_role = (getattr(getattr(getattr(request.user, 'userprofile', None), 'usuariosistema', None), 'tipo_usuario', None)
                or getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None))
    canonical_role = _canonical_role_from_string(raw_role) or ''

    context = {
        'total_beneficiarios': total_beneficiarios,
        'total_proyectos': total_proyectos,
        'total_postulaciones': total_postulaciones,
        'total_empresas': total_empresas,
        'beneficiarios_por_estado': beneficiarios_por_estado,
        'proyectos_por_estado': proyectos_por_estado,
        'postulaciones_recientes': postulaciones_recientes,
        'proyectos_activos': proyectos_activos,
        'distribucion_regional': distribucion_regional,
        'trend_labels': month_labels,
        'trend_data': postulaciones_counts,
        'viviendas_entregadas': viviendas_entregadas,
        'postulaciones_aprobadas': postulaciones_aprobadas,
        'postulaciones_revision': postulaciones_revision,
        'casos_atencion': casos_atencion,
        'top_municipios': top_municipios,
        'actividades_recientes': actividades_recientes,
        'today': datetime.date.today()
    }
    
    return render(request, 'gestion/dashboard.html', context)


@login_required
def calendar_view(request):
    """Vista del calendario: muestra eventos, proyectos y usuarios para agendar visitas."""
    from django.utils import timezone
    today = datetime.date.today()

    # Consultas básicas
    projects = ProyectosHabitacionales.objects.order_by('nombre_proyecto')
    users_qs = User.objects.filter(is_active=True).order_by('username')
    # construir lista de usuarios con rol canónico para el select
    users = []
    for u in users_qs:
        role_raw = None
        try:
            role_raw = getattr(getattr(u, 'userprofile', None), 'usuariosistema', None).tipo_usuario
        except Exception:
            try:
                role_raw = getattr(getattr(u, 'userprofile', None), 'tipo_usuario', None)
            except Exception:
                role_raw = None
        canonical = _canonical_role_from_string(role_raw) or ''
        display = u.get_full_name() or u.username
        users.append({'id': u.id, 'display': display, 'role': canonical})
    events_qs = Evento.objects.order_by('-fecha_inicio')

    total_events = events_qs.count()
    upcoming_events = events_qs.filter(fecha_inicio__gte=today).count()
    overdue_events = events_qs.filter(fecha_fin__lt=today).count()
    today_events = events_qs.filter(fecha_inicio=today).count()

    # Serializar eventos para uso en JS
    events_list = []
    for e in events_qs[:1000]:
        events_list.append({
            'date': e.fecha_inicio.isoformat(),
            'end_date': e.fecha_fin.isoformat() if e.fecha_fin else None,
            'title': e.titulo,
            'type': e.tipo or 'task',
            'time': e.hora_inicio.strftime('%H:%M') if e.hora_inicio else None,
            'project_id': e.proyecto.id_proyecto if e.proyecto else None,
        })

    # determinar rol canónico del usuario (usar UsuariosSistema.tipo_usuario si existe)
    raw_role = (getattr(getattr(getattr(request.user, 'userprofile', None), 'usuariosistema', None), 'tipo_usuario', None)
                or getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None))
    canonical_role = _canonical_role_from_string(raw_role)

    context = {
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'overdue_events': overdue_events,
        'today_events': today_events,
        'projects': projects,
        'users': users,
        'events_json': json.dumps(events_list, default=str),
        'user_type': getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None),
        'user_tipo': getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None),
        # current_user_role: prefer UsuariosSistema.tipo_usuario (más granular), fallback to UserProfile.tipo_usuario
        'current_user_role': canonical_role,
        'user_company_id': getattr(getattr(request.user, 'userprofile', None), 'usuariosistema', None).id_empresa_id if getattr(getattr(request.user, 'userprofile', None), 'usuariosistema', None) else None,
    }
    # Determine create permissions for event types (so template can disable buttons server-side)
    creator = canonical_role
    is_staff = request.user.is_staff
    def allowed(role_list):
        return is_staff or (creator in role_list if creator else False)

    context.update({
        'can_create_task': allowed(['jefe_proyecto', 'ministro', 'admin']),
        'can_create_meeting': allowed(['empresa', 'admin']),
        'can_create_deadline': allowed(['empresa', 'admin']),
        'can_create_agenda': allowed(['beneficiario', 'admin']),
    })
    return render(request, 'gestion/calendar.html', context)


@login_required
def events_api(request):
    """API mínima para listar y crear eventos via JSON (GET/POST)."""
    if request.method == 'GET':
        qs = Evento.objects.order_by('-fecha_inicio')[:1000]
        data = []
        for e in qs:
            data.append({
                'id': e.id_evento,
                'title': e.titulo,
                'type': e.tipo,
                'start': e.fecha_inicio.isoformat(),
                'end': e.fecha_fin.isoformat() if e.fecha_fin else None,
                'time': e.hora_inicio.strftime('%H:%M') if e.hora_inicio else None,
                'project_id': e.proyecto.id_proyecto if e.proyecto else None,
            })
        return JsonResponse({'events': data})

    if request.method == 'POST':
        # aceptar JSON o form-data
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = request.POST.dict()

        # Campos básicos
        titulo = payload.get('title') or payload.get('titulo')
        if not titulo:
            return JsonResponse({'error': 'title is required'}, status=400)

        fecha_inicio = payload.get('start') or payload.get('fecha_inicio')
        if not fecha_inicio:
            return JsonResponse({'error': 'fecha_inicio is required'}, status=400)
        try:
            fecha_inicio_obj = datetime.date.fromisoformat(str(fecha_inicio))
        except Exception:
            return JsonResponse({'error': 'fecha_inicio inválida'}, status=400)

        fecha_fin = payload.get('end') or payload.get('fecha_fin')
        fecha_fin_obj = None
        if fecha_fin:
            try:
                fecha_fin_obj = datetime.date.fromisoformat(str(fecha_fin))
            except Exception:
                return JsonResponse({'error': 'fecha_fin inválida'}, status=400)
            if fecha_fin_obj < fecha_inicio_obj:
                return JsonResponse({'error': 'fecha_fin no puede ser anterior a fecha_inicio'}, status=400)

        # Hora
        hora_inicio = payload.get('time') or payload.get('hora_inicio')
        hora_fin = payload.get('end_time') or payload.get('hora_fin')
        hora_inicio_obj = None
        hora_fin_obj = None
        try:
            if hora_inicio:
                hora_inicio_obj = datetime.time.fromisoformat(str(hora_inicio))
            if hora_fin:
                hora_fin_obj = datetime.time.fromisoformat(str(hora_fin))
            if hora_inicio_obj and hora_fin_obj and (datetime.datetime.combine(datetime.date.today(), hora_fin_obj) < datetime.datetime.combine(datetime.date.today(), hora_inicio_obj)):
                return JsonResponse({'error': 'hora_fin no puede ser anterior a hora_inicio'}, status=400)
        except Exception:
            return JsonResponse({'error': 'hora inválida, usar HH:MM'}, status=400)

        # Proyecto
        proyecto_id = payload.get('project') or payload.get('project_id')
        proyecto_obj = None
        if proyecto_id:
            try:
                proyecto_obj = ProyectosHabitacionales.objects.get(pk=int(proyecto_id))
            except Exception:
                return JsonResponse({'error': 'proyecto no encontrado'}, status=400)

        # All day
        all_day = payload.get('all_day') or payload.get('allDay') or payload.get('all-day')
        if isinstance(all_day, str):
            all_day = all_day.lower() in ['1', 'true', 'yes', 'on']
        else:
            all_day = bool(all_day)

        # Assigned users
        assigned_raw = payload.get('assigned_to') or payload.get('assigned') or payload.get('assigned_to[]')
        assigned_ids = []
        if assigned_raw:
            if isinstance(assigned_raw, str):
                # comma separated or single
                if ',' in assigned_raw:
                    assigned_ids = [int(x) for x in assigned_raw.split(',') if x.strip().isdigit()]
                elif assigned_raw.isdigit():
                    assigned_ids = [int(assigned_raw)]
            elif isinstance(assigned_raw, list):
                assigned_ids = [int(x) for x in assigned_raw if str(x).isdigit()]

        # Permisos: quién puede crear/asignar
        is_staff = request.user.is_staff
        user_type = getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None)
        user_company = getattr(getattr(request.user, 'userprofile', None), 'usuariosistema', None)
        # usar el id raw del FK para comparar correctamente
        user_company_id = user_company.id_empresa_id if user_company else None

        # Empresa users only create events for their own projects
        if (user_type == 'empresa') and proyecto_obj:
            try:
                proj_company = proyecto_obj.id_empresa_constructora
                if not proj_company or (proj_company.id_empresa != user_company_id):
                    return JsonResponse({'error': 'No autorizado para crear eventos en este proyecto'}, status=403)
            except Exception:
                return JsonResponse({'error': 'Error verificando proyecto/empresa'}, status=403)

        # Validate event type permissions and assignees by role
        event_type = (payload.get('type') or payload.get('tipo') or '').lower()

        # Determine creator role (prefer UsuariosSistema.tipo_usuario then UserProfile.tipo_usuario)
        # normalize creator role to canonical string
        try:
            raw_creator_role = getattr(request.user.userprofile.usuariosistema, 'tipo_usuario', None) or getattr(request.user.userprofile, 'tipo_usuario', None)
        except Exception:
            raw_creator_role = getattr(getattr(request.user, 'userprofile', None), 'tipo_usuario', None)
        creator_role = _canonical_role_from_string(raw_creator_role)

        # Allowed creators per event type
        allowed_creators = {
            'task': ['jefe_proyecto', 'ministro', 'admin'],
            'meeting': ['empresa', 'admin'],
            'deadline': ['empresa', 'admin'],
            'agenda': ['beneficiario', 'admin']
        }

        # Allowed assignee roles per event type
        allowed_assignees = {
            'task': ['jefe_proyecto', 'ministro', 'admin'],
            'meeting': ['empresa', 'admin'],
            'deadline': ['empresa', 'admin'],
            'agenda': ['beneficiario']
        }

        # If event_type is provided, enforce creation permission (admins always allowed)
        if event_type:
            if not request.user.is_staff:
                allowed = allowed_creators.get(event_type)
                if allowed and (creator_role not in allowed):
                    return JsonResponse({'error': f'No autorizado para crear eventos de tipo {event_type}'}, status=403)

        # Validate assigned users' roles match allowed assignees for this event type
        if assigned_ids and event_type:
            # fetch assignee roles
            bad_assignees = []
            for uid in assigned_ids:
                try:
                    u = User.objects.get(pk=uid)
                    ar = None
                    try:
                        ar = getattr(u.userprofile.usuariosistema, 'tipo_usuario', None) or getattr(u.userprofile, 'tipo_usuario', None)
                    except Exception:
                        ar = getattr(getattr(u, 'userprofile', None), 'tipo_usuario', None)
                    # normalizar rol del asignado antes de comparar
                    ar_canonical = _canonical_role_from_string(ar)
                    allowed = allowed_assignees.get(event_type)
                    if allowed and (ar_canonical not in allowed):
                        bad_assignees.append({'id': uid, 'role': ar, 'role_canonical': ar_canonical})
                except User.DoesNotExist:
                    bad_assignees.append({'id': uid, 'missing': True})
            if bad_assignees:
                return JsonResponse({'error': 'assigned_to contiene usuarios no permitidos para este tipo de evento', 'details': bad_assignees}, status=403)

        # Non-staff regular users cannot assign other users
        if not is_staff and user_type != 'empresa':
            # assigned_ids must be empty or only contain the requester
            if assigned_ids and not (len(assigned_ids) == 1 and assigned_ids[0] == request.user.id):
                return JsonResponse({'error': 'No autorizado para asignar otros usuarios'}, status=403)

        # Create event
        ev = Evento(
            titulo=titulo,
            tipo=payload.get('type') or payload.get('tipo'),
            descripcion=payload.get('description') or payload.get('descripcion'),
            fecha_inicio=fecha_inicio_obj,
            fecha_fin=fecha_fin_obj,
            hora_inicio=hora_inicio_obj,
            hora_fin=hora_fin_obj,
            proyecto=proyecto_obj,
            ubicacion=payload.get('location') or payload.get('ubicacion'),
            all_day=all_day,
            creado_por=request.user
        )
        try:
            ev.full_clean()
        except Exception as e:
            return JsonResponse({'error': 'validacion modelo', 'details': str(e)}, status=400)
        ev.save()

        if assigned_ids:
            users_qs = User.objects.filter(id__in=assigned_ids)
            ev.asignados.set(users_qs)

        return JsonResponse({'ok': True, 'id': ev.id_evento})

    return HttpResponseNotAllowed(['GET', 'POST'])


def beneficiarios_list(request):
    """Lista de beneficiarios con filtros por rol"""

    # Base queryset
    beneficiarios = Beneficiarios.objects.select_related('id_municipio')

    # Filtrar según rol del usuario
    if request.user.is_authenticated:
        if request.user.is_staff:
            # Admin ve todos los beneficiarios
            pass
        else:
            try:
                user_tipo = request.user.userprofile.tipo_usuario
                if user_tipo == 'empresa':
                    # Empresa ve beneficiarios que postularon a sus proyectos
                    us = request.user.userprofile.usuariosistema
                    if us and us.id_empresa:
                        beneficiarios = beneficiarios.filter(
                            postulaciones__id_proyecto__id_empresa_constructora=us.id_empresa
                        ).distinct()
                    else:
                        beneficiarios = beneficiarios.none()
                elif user_tipo == 'usuario':
                    # Usuario no puede ver la lista de beneficiarios
                    beneficiarios = beneficiarios.none()
                else:
                    # Otros tipos no ven beneficiarios
                    beneficiarios = beneficiarios.none()
            except:
                beneficiarios = beneficiarios.none()
    else:
        beneficiarios = beneficiarios.none()

    # Filtros adicionales
    estado = request.GET.get('estado')
    municipio = request.GET.get('municipio')
    buscar = request.GET.get('q')

    if estado:
        beneficiarios = beneficiarios.filter(estado_beneficiario=estado)

    if municipio:
        beneficiarios = beneficiarios.filter(id_municipio__id_municipio=municipio)

    if buscar:
        beneficiarios = beneficiarios.filter(
            Q(nombre__icontains=buscar) |
            Q(apellidos__icontains=buscar) |
            Q(rut__icontains=buscar)
        )

    # Obtener opciones para filtros
    estados = Beneficiarios.objects.values_list('estado_beneficiario', flat=True).distinct()
    municipios = Municipios.objects.all()

    context = {
        'beneficiarios': beneficiarios,
        'estados': estados,
        'municipios': municipios,
    }

    return render(request, 'gestion/beneficiarios_list.html', context)


@ensure_csrf_cookie
def beneficiario_detail(request, pk):
    """Detalle de un beneficiario"""

    beneficiario = get_object_or_404(Beneficiarios.objects.select_related('id_municipio'), pk=pk)

    # Verificar si el usuario tiene permiso para ver las postulaciones
    puede_ver_postulaciones = False
    if request.user.is_authenticated:
        if request.user.is_staff:
            puede_ver_postulaciones = True
        elif hasattr(request.user, 'userprofile'):
            try:
                # Usuario puede ver sus propias postulaciones
                user_beneficiario = request.user.userprofile.usuariosistema.beneficiario
                if user_beneficiario and user_beneficiario.id_beneficiario == beneficiario.id_beneficiario:
                    puede_ver_postulaciones = True
            except:
                pass

    # Postulaciones del beneficiario (solo si tiene permiso)
    postulaciones = None
    if puede_ver_postulaciones:
        postulaciones = Postulaciones.objects.filter(
            id_beneficiario=beneficiario
        ).select_related('id_proyecto').order_by('-fecha_postulacion')

    # Generar mapa si tiene coordenadas
    mapa_html = None
    if beneficiario.latitud and beneficiario.longitud:
        popup_text = f"{beneficiario.nombre} {beneficiario.apellidos}<br>{beneficiario.direccion}"
        mapa_html = generar_mapa(beneficiario.latitud, beneficiario.longitud, popup_text)
    elif beneficiario.direccion:
        # Intentar geocodificar si no tiene coordenadas
        lat, lng = geocodificar_direccion(
            beneficiario.direccion,
            beneficiario.id_municipio.nombre_municipio if beneficiario.id_municipio else None,
            beneficiario.id_municipio.id_region.nombre_region if beneficiario.id_municipio and beneficiario.id_municipio.id_region else None
        )
        if lat and lng:
            beneficiario.latitud = lat
            beneficiario.longitud = lng
            beneficiario.save()
            popup_text = f"{beneficiario.nombre} {beneficiario.apellidos}<br>{beneficiario.direccion}"
            mapa_html = generar_mapa(lat, lng, popup_text)

    context = {
        'beneficiario': beneficiario,
        'postulaciones': postulaciones,
        'mapa_html': mapa_html,
    }
    # asegurar que el token CSRF esté disponible en la plantilla (meta tag)
    try:
        context['csrf_token'] = get_token(request)
    except Exception:
        pass

    return render(request, 'gestion/beneficiario_detail.html', context)


@login_required
@require_http_methods(["POST"])
def beneficiario_update(request, pk):
    """Actualizar campos básicos del beneficiario vía AJAX (JSON o form-data).

    Permisos: staff o usuario vinculado al beneficiario.
    """
    try:
        ben = Beneficiarios.objects.get(pk=pk)
    except Beneficiarios.DoesNotExist:
        return JsonResponse({'error': 'Beneficiario no encontrado'}, status=404)

    # permiso sencillo
    allowed = False
    if request.user.is_authenticated:
        if request.user.is_staff:
            allowed = True
        else:
            try:
                us = request.user.userprofile.usuariosistema
                if us and us.beneficiario and us.beneficiario.id_beneficiario == ben.id_beneficiario:
                    allowed = True
            except Exception:
                allowed = False
    if not allowed:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    # soportar JSON
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST.dict()

    # campos permitidos
    fields = ['nombre', 'apellidos', 'telefono', 'email', 'direccion', 'ingresos_familiares', 'numero_integrantes']
    for f in fields:
        if f in data:
            setattr(ben, f, data.get(f) or None)
    try:
        ben.save()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # devolver representación mínima
    return JsonResponse({
        'id': ben.id_beneficiario,
        'nombre': ben.nombre,
        'apellidos': ben.apellidos,
        'telefono': ben.telefono,
        'email': ben.email,
        'direccion': ben.direccion,
        'ingresos_familiares': str(ben.ingresos_familiares) if ben.ingresos_familiares is not None else None,
        'numero_integrantes': ben.numero_integrantes,
    })


@login_required
@require_http_methods(["POST"])
def beneficiario_delete(request, pk):
    """Eliminar beneficiario (solo staff)."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'No autorizado'}, status=403)
    try:
        ben = Beneficiarios.objects.get(pk=pk)
    except Beneficiarios.DoesNotExist:
        return JsonResponse({'error': 'Beneficiario no encontrado'}, status=404)
    ben.delete()
    return JsonResponse({'ok': True})


# ---- API ViewSets para DRF ----
class ProyectoPermission(permissions.BasePermission):
    """Permiso fino para ProyectosHabitacionales:

    - Lectura: permitida para cualquier solicitud segura (GET, HEAD, OPTIONS).
    - Escritura (POST/PUT/PATCH/DELETE): permitida si el usuario es staff (admin) o
    si el usuario está vinculado a una `EmpresasConstructoras` que corresponde
    al `id_empresa_constructora` del proyecto.
    Para `create` se permite a usuarios empresa pero se valida/forza que el
    proyecto quede asociado a su empresa.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Para operaciones que no tienen objeto aún (create), permitimos que
        # staff y usuarios tipo 'empresa' continúen; la verificación final se
        # hace en has_object_permission / perform_create.
        if request.user and request.user.is_authenticated:
            if request.user.is_staff:
                return True
            try:
                up = request.user.userprofile
                if getattr(up, 'tipo_usuario', None) == 'empresa':
                    return True
            except Exception:
                pass
        return False

    def has_object_permission(self, request, view, obj):
        # obj es una instancia de ProyectosHabitacionales
        if request.method in permissions.SAFE_METHODS:
            return True
        # staff tiene todo permiso
        if request.user and request.user.is_authenticated and request.user.is_staff:
            return True
        # usuarios empresa sólo pueden modificar/borrar si pertenecen a la misma empresa
        try:
            up = request.user.userprofile
            if getattr(up, 'tipo_usuario', None) == 'empresa':
                us = getattr(up, 'usuariosistema', None)
                if us and us.id_empresa and obj.id_empresa_constructora:
                    return us.id_empresa.id_empresa == obj.id_empresa_constructora.id_empresa
        except Exception:
            pass
        return False


class ProyectosHabitacionalesViewSet(viewsets.ModelViewSet):
    """API CRUD para ProyectosHabitacionales."""
    queryset = ProyectosHabitacionales.objects.all().select_related('id_municipio', 'id_empresa_constructora', 'id_terreno')
    serializer_class = globals().get('ProyectosHabitacionalesSerializer')
    permission_classes = [ProyectoPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_proyecto', 'descripcion', 'estado_proyecto']
    ordering_fields = ['fecha_inicio', 'nombre_proyecto']

    def perform_create(self, serializer):
        # Si el request proviene de un usuario empresa, forzamos la asociación
        # del proyecto a la empresa del usuario para evitar elevación de permisos.
        request = None
        try:
            request = self.request
        except Exception:
            request = None

        if request and getattr(request.user, 'is_authenticated', False):
            try:
                up = request.user.userprofile
                if getattr(up, 'tipo_usuario', None) == 'empresa':
                    us = getattr(up, 'usuariosistema', None)
                    if us and us.id_empresa:
                        # Forzamos id_empresa_constructora a la empresa del usuario
                        proj = serializer.save(id_empresa_constructora=us.id_empresa)
                    else:
                        proj = serializer.save()
                else:
                    proj = serializer.save()
            except Exception:
                proj = serializer.save()
        else:
            proj = serializer.save()
        try:
            LogAuditoria.objects.create(id_usuario=None, accion='create_proyecto', tabla='proyectos_habitacionales', registro_afectado=proj.id_proyecto)
        except Exception:
            pass

    def create(self, request, *args, **kwargs):
        # Para mayor determinismo: si el usuario es empresa, forzamos el campo
        # `id_empresa_constructora` en los datos antes de serializar.
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        try:
            up = request.user.userprofile
            if getattr(up, 'tipo_usuario', None) == 'empresa':
                us = getattr(up, 'usuariosistema', None)
                if us and us.id_empresa:
                    data['id_empresa_constructora'] = us.id_empresa.id_empresa
        except Exception:
            pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)



def proyectos_list(request):
    """Lista de proyectos habitacionales (público)"""
    
    proyectos = ProyectosHabitacionales.objects.select_related(
        'id_municipio', 'id_empresa_constructora', 'id_terreno'
    ).all()
    
    # Filtros
    estado = request.GET.get('estado')
    municipio = request.GET.get('municipio')
    tipo = request.GET.get('tipo')
    
    if estado:
        proyectos = proyectos.filter(estado_proyecto=estado)
    
    if municipio:
        proyectos = proyectos.filter(id_municipio__id_municipio=municipio)
    
    if tipo:
        proyectos = proyectos.filter(tipo_vivienda=tipo)
    
    # Opciones para filtros
    estados = ProyectosHabitacionales.objects.values_list('estado_proyecto', flat=True).distinct()
    municipios = Municipios.objects.all()
    tipos = ProyectosHabitacionales.objects.values_list('tipo_vivienda', flat=True).distinct()
    
    context = {
        'proyectos': proyectos,
        'estados': estados,
        'municipios': municipios,
        'tipos': tipos,
    }
    
    return render(request, 'gestion/proyectos_list.html', context)


def proyecto_detail(request, pk):
    """Detalle de un proyecto"""

    proyecto = get_object_or_404(
        ProyectosHabitacionales.objects.select_related(
            'id_municipio', 'id_empresa_constructora', 'id_terreno'
        ),
        pk=pk
    )

    # Postulaciones del proyecto (solo visibles para admin y empresa dueña)
    postulaciones = None
    if request.user.is_authenticated:
        if request.user.is_staff or (
            hasattr(request.user, 'userprofile') and
            request.user.userprofile.tipo_usuario == 'empresa' and
            hasattr(request.user.userprofile, 'usuariosistema') and
            request.user.userprofile.usuariosistema.id_empresa == proyecto.id_empresa_constructora
        ):
            postulaciones = Postulaciones.objects.filter(
                id_proyecto=proyecto
            ).select_related('id_beneficiario').order_by('-fecha_postulacion')

    # Verificar si el usuario ya postuló
    ya_postulado = False
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        try:
            beneficiario = request.user.userprofile.usuariosistema.beneficiario
            if beneficiario:
                ya_postulado = Postulaciones.objects.filter(
                    id_proyecto=proyecto,
                    id_beneficiario=beneficiario
                ).exists()
        except:
            pass

    # Obtener user_tipo para el template
    user_tipo = None
    if request.user.is_authenticated and hasattr(request.user, 'userprofile'):
        try:
            user_tipo = request.user.userprofile.tipo_usuario
        except:
            user_tipo = None

    # Generar mapa si el terreno tiene coordenadas
    mapa_html = None
    map_lat = None
    map_lng = None
    if proyecto.id_terreno and proyecto.id_terreno.latitud and proyecto.id_terreno.longitud:
        popup_text = f"Proyecto: {proyecto.nombre_proyecto}<br>Dirección: {proyecto.id_terreno.direccion}"
        mapa_html = generar_mapa(proyecto.id_terreno.latitud, proyecto.id_terreno.longitud, popup_text)
        map_lat = float(proyecto.id_terreno.latitud)
        map_lng = float(proyecto.id_terreno.longitud)
    elif proyecto.id_terreno and proyecto.id_terreno.direccion:
        # Intentar geocodificar si no tiene coordenadas
        lat, lng = geocodificar_direccion(
            proyecto.id_terreno.direccion,
            proyecto.id_municipio.nombre_municipio if proyecto.id_municipio else None,
            proyecto.id_municipio.id_region.nombre_region if proyecto.id_municipio and proyecto.id_municipio.id_region else None
        )
        if lat and lng:
            proyecto.id_terreno.latitud = lat
            proyecto.id_terreno.longitud = lng
            proyecto.id_terreno.save()
            popup_text = f"Proyecto: {proyecto.nombre_proyecto}<br>Dirección: {proyecto.id_terreno.direccion}"
            mapa_html = generar_mapa(lat, lng, popup_text)
            try:
                map_lat = float(lat)
                map_lng = float(lng)
            except Exception:
                map_lat = None
                map_lng = None
    else:
        # Fall back: try proyecto coordinates or empresa coordinates
        try:
            if proyecto.latitud and proyecto.longitud:
                map_lat = float(proyecto.latitud)
                map_lng = float(proyecto.longitud)
            elif proyecto.id_empresa_constructora and proyecto.id_empresa_constructora.latitud and proyecto.id_empresa_constructora.longitud:
                map_lat = float(proyecto.id_empresa_constructora.latitud)
                map_lng = float(proyecto.id_empresa_constructora.longitud)
        except Exception:
            map_lat = None
            map_lng = None

    context = {
        'proyecto': proyecto,
        'postulaciones': postulaciones,
        'ya_postulado': ya_postulado,
        'total_postulaciones': postulaciones.count() if postulaciones else 0,
        'postulaciones_aprobadas': postulaciones.filter(estado_postulacion='Aprobada').count() if postulaciones else 0,
        'user_tipo': user_tipo,
        'mapa_html': mapa_html,
        'map_lat': map_lat,
        'map_lng': map_lng,
    }

    return render(request, 'gestion/proyecto_detail.html', context)


def register(request):
    """Registro simple: crea User + UsuariosSistema + UserProfile.tipo_usuario"""
    if request.method == 'POST':
        tipo = request.POST.get('tipo_usuario', 'usuario')

        try:
            if tipo == 'usuario':
                username = request.POST.get('username')
                password = request.POST.get('password')
                email = request.POST.get('email')
                nombre = request.POST.get('nombre')
                apellidos = request.POST.get('apellidos')
                rut = request.POST.get('rut')
            elif tipo == 'empresa':
                username = request.POST.get('username_empresa')
                password = request.POST.get('password_empresa')
                email = request.POST.get('email_empresa')
                razon_social = request.POST.get('razon_social')
                rut_empresa = request.POST.get('rut_empresa')
                telefono_empresa = request.POST.get('telefono_empresa')
                nombre = razon_social  # usar razon_social como nombre
                apellidos = ''  # empresas no tienen apellidos
            else:
                messages.error(request, 'Tipo de usuario no válido')
                return redirect('gestion:register')

            if User.objects.filter(username=username).exists():
                messages.error(request, 'El nombre de usuario ya existe')
                return redirect('gestion:register')

            user = User.objects.create_user(username=username, email=email, password=password, first_name=nombre, last_name=apellidos)

            # crear entrada en UsuariosSistema y vincular al perfil
            us = UsuariosSistema.objects.create(username=username, email=email, nombre=nombre, apellidos=apellidos, tipo_usuario=tipo)
            try:
                profile = user.userprofile
                profile.tipo_usuario = tipo
                profile.usuariosistema = us
                profile.save()
            except Exception:
                # crear por si acaso
                from .models import UserProfile
                UserProfile.objects.create(user=user, tipo_usuario=tipo, usuariosistema=us)

            if tipo == 'usuario':
                # Si se proporciona RUT, crear/actualizar Beneficiario asociado
                if rut:
                    b, created = Beneficiarios.objects.get_or_create(rut=rut, defaults={
                        'nombre': nombre,
                        'apellidos': apellidos,
                        'email': email,
                    })
                    if not created:
                        # actualizar datos básicos
                        b.nombre = b.nombre or nombre
                        b.apellidos = b.apellidos or apellidos
                        b.email = b.email or email
                        b.save()
                    # vincular el UsuariosSistema al beneficiario creado/actualizado
                    try:
                        us.beneficiario = b
                        us.save()
                    except Exception:
                        pass
            elif tipo == 'empresa':
                # Crear empresa constructora
                if razon_social and rut_empresa:
                    empresa, created = EmpresasConstructoras.objects.get_or_create(rut_empresa=rut_empresa, defaults={
                        'razon_social': razon_social,
                        'telefono': telefono_empresa,
                        'email': email,
                    })
                    if not created:
                        # actualizar datos básicos
                        empresa.razon_social = empresa.razon_social or razon_social
                        empresa.telefono = empresa.telefono or telefono_empresa
                        empresa.email = empresa.email or email
                        empresa.save()
                    # vincular el UsuariosSistema a la empresa
                    try:
                        us.id_empresa = empresa
                        us.save()
                    except Exception:
                        pass

            login(request, user)
            messages.success(request, 'Registro exitoso. Bienvenido!')
            return redirect('gestion:dashboard')
        except Exception as e:
            messages.error(request, f'Error al crear la cuenta: {str(e)}')
            return redirect('gestion:register')

    return render(request, 'registration/register.html')


@login_required
def profile(request):
    """Mostrar perfil del usuario autenticado."""
    # obtener UsuariosSistema si existe
    us = None
    try:
        us = request.user.userprofile.usuariosistema
    except Exception:
        us = None

    # permitir editar perfil (POST)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        apellidos = request.POST.get('apellidos')
        email = request.POST.get('email')
        rut = request.POST.get('rut')

        # actualizar User
        u = request.user
        u.first_name = nombre or u.first_name
        u.last_name = apellidos or u.last_name
        u.email = email or u.email
        u.save()

        # actualizar o crear beneficiario por RUT
        if rut:
            b, created = Beneficiarios.objects.get_or_create(rut=rut, defaults={
                'nombre': nombre,
                'apellidos': apellidos,
                'email': email,
            })
            if not created:
                b.nombre = nombre or b.nombre
                b.apellidos = apellidos or b.apellidos
                b.email = email or b.email
                b.save()

            # vincular UsuariosSistema si existe
            try:
                us = request.user.userprofile.usuariosistema
                if us:
                    us.beneficiario = b
                    us.save()
            except Exception:
                pass

        messages.success(request, 'Perfil actualizado')
        return redirect('gestion:profile')

    # intentar obtener RUT/beneficiario asociado
    rut_value = None
    try:
        if us and us.username:
            b = Beneficiarios.objects.filter(rut=us.username).first()
            if b:
                rut_value = b.rut
    except Exception:
        rut_value = None

    context = {
        'usuariosistema': us,
        'rut_value': rut_value,
    }
    return render(request, 'gestion/profile.html', context)


def logout_view(request):
    """Cerrar sesión de forma segura mediante POST. Si recibe GET redirige al dashboard."""
    if request.method == 'POST':
        try:
            logout(request)
        except Exception:
            pass
        messages.success(request, 'Sesión cerrada')
        return redirect('gestion:dashboard')
    return redirect('gestion:dashboard')


@login_required
def create_beneficiario(request):
    """Crear beneficiario desde formulario en el panel (restringido a staff/admin por plantilla)."""
    if request.method == 'POST':
        rut = request.POST.get('rut')
        nombre = request.POST.get('nombre')
        apellidos = request.POST.get('apellidos')
        email = request.POST.get('email')

        if not rut:
            messages.error(request, 'RUT es requerido')
            return redirect('gestion:beneficiarios_list')

        b, created = Beneficiarios.objects.get_or_create(rut=rut, defaults={
            'nombre': nombre,
            'apellidos': apellidos,
            'email': email,
        })
        if not created:
            messages.info(request, 'Beneficiario ya existente; se actualizó información básica')
            b.nombre = nombre or b.nombre
            b.apellidos = apellidos or b.apellidos
            b.email = email or b.email
            b.save()
        else:
            messages.success(request, 'Beneficiario creado')

    return redirect('gestion:beneficiarios_list')


@login_required
@role_required('empresa','admin')
def proyecto_create(request):
    """Crear nuevo proyecto (solo empresas y admin)."""
    if request.method == 'POST':
        # Obtener todos los campos del formulario
        nombre_proyecto = request.POST.get('nombre_proyecto')
        descripcion = request.POST.get('descripcion')
        tipo_vivienda = request.POST.get('tipo_vivienda')
        estado_proyecto = request.POST.get('estado_proyecto')
        numero_viviendas = request.POST.get('numero_viviendas')
        superficie_vivienda = request.POST.get('superficie_vivienda')
        precio_unitario = request.POST.get('precio_unitario')
        id_municipio = request.POST.get('id_municipio')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin_estimada = request.POST.get('fecha_fin_estimada')
        direccion = request.POST.get('direccion')
        id_empresa_constructora = request.POST.get('id_empresa_constructora')

        # Validaciones básicas
        if not nombre_proyecto or not tipo_vivienda or not estado_proyecto:
            messages.error(request, 'Los campos nombre del proyecto, tipo de vivienda y estado del proyecto son obligatorios')
            return redirect('gestion:proyecto_create')

        try:
            # Crear el proyecto con todos los campos
            proyecto = ProyectosHabitacionales(
                nombre_proyecto=nombre_proyecto,
                descripcion=descripcion,
                tipo_vivienda=tipo_vivienda,
                estado_proyecto=estado_proyecto,
                numero_viviendas=numero_viviendas if numero_viviendas else None,
                superficie_vivienda=superficie_vivienda if superficie_vivienda else None,
                precio_unitario=precio_unitario if precio_unitario else None,
                id_municipio_id=id_municipio if id_municipio else None,
                fecha_inicio=fecha_inicio if fecha_inicio else None,
                fecha_fin_estimada=fecha_fin_estimada if fecha_fin_estimada else None,
                latitud=request.POST.get('latitud') or None,
                longitud=request.POST.get('longitud') or None,
            )
            # Validar antes de guardar
            try:
                proyecto.full_clean()
            except Exception as e:
                messages.error(request, f'Error de validación: {str(e)}')
                return redirect('gestion:proyecto_create')
            proyecto.save()

            # Asignar empresa constructora si se especificó o si el usuario es empresa
            if id_empresa_constructora:
                proyecto.id_empresa_constructora_id = id_empresa_constructora
            else:
                # Si el creador es empresa y tiene empresa vinculada, asignarla al proyecto
                try:
                    profile = request.user.userprofile
                    us = profile.usuariosistema
                    if us and us.id_empresa:
                        proyecto.id_empresa_constructora = us.id_empresa
                except Exception:
                    pass

            proyecto.save()

            messages.success(request, 'Proyecto creado exitosamente')
            return redirect('gestion:proyecto_detail', pk=proyecto.id_proyecto)

        except Exception as e:
            messages.error(request, f'Error al crear el proyecto: {str(e)}')
            return redirect('gestion:proyecto_create')

    # Para GET, obtener datos para los selects
    context = {
        'action': 'Crear',
        'regiones': Regiones.objects.all(),
        'empresas': EmpresasConstructoras.objects.all(),
        'municipios': Municipios.objects.all(),
    }
    return render(request, 'gestion/proyecto_form.html', context)


@login_required
@role_required('empresa','admin')
def proyecto_edit(request, pk):
    proyecto = get_object_or_404(ProyectosHabitacionales, pk=pk)
    # permisos: admin puede editar todo; empresa sólo puede editar proyectos de su empresa
    if not request.user.is_staff:
        try:
            user_tipo = request.user.userprofile.tipo_usuario
        except Exception:
            user_tipo = None

        if user_tipo == 'empresa':
            try:
                us = request.user.userprofile.usuariosistema
                if not us or not us.id_empresa or proyecto.id_empresa != us.id_empresa:
                    messages.error(request, 'No tienes permiso para editar este proyecto')
                    return redirect('gestion:proyecto_detail', pk=pk)
            except Exception:
                messages.error(request, 'No tienes permiso para editar este proyecto')
                return redirect('gestion:proyecto_detail', pk=pk)
        else:
            messages.error(request, 'No tienes permiso para editar este proyecto')
            return redirect('gestion:proyecto_detail', pk=pk)
    if request.method == 'POST':
        proyecto.nombre_proyecto = request.POST.get('nombre_proyecto') or proyecto.nombre_proyecto
        proyecto.descripcion = request.POST.get('descripcion') or proyecto.descripcion
        proyecto.numero_viviendas = request.POST.get('numero_viviendas') or proyecto.numero_viviendas
        proyecto.superficie_vivienda = request.POST.get('superficie_vivienda') or proyecto.superficie_vivienda
        proyecto.precio_unitario = request.POST.get('precio_unitario') or proyecto.precio_unitario
        proyecto.tipo_vivienda = request.POST.get('tipo_vivienda') or proyecto.tipo_vivienda
        proyecto.latitud = request.POST.get('latitud') or proyecto.latitud
        proyecto.longitud = request.POST.get('longitud') or proyecto.longitud
        # Validar antes de guardar cambios
        try:
            proyecto.full_clean()
        except Exception as e:
            messages.error(request, f'Error de validación: {str(e)}')
            return redirect('gestion:proyecto_edit', pk=pk)
        id_municipio = request.POST.get('id_municipio')
        if id_municipio:
            proyecto.id_municipio_id = id_municipio
        id_empresa_constructora = request.POST.get('id_empresa_constructora')
        if id_empresa_constructora:
            proyecto.id_empresa_constructora_id = id_empresa_constructora
        proyecto.save()
        messages.success(request, 'Proyecto actualizado')
        return redirect('gestion:proyecto_detail', pk=proyecto.id_proyecto)

    # Para GET, obtener datos para los selects
    context = {
        'action': 'Editar',
        'proyecto': proyecto,
        'regiones': Regiones.objects.all(),
        'empresas': EmpresasConstructoras.objects.all(),
        'municipios': Municipios.objects.all(),
    }
    return render(request, 'gestion/proyecto_form.html', context)


@login_required
@require_POST
@role_required('usuario')
def postular(request, pk):
    """Crear una postulación para el proyecto pk por el beneficiario asociado al usuario.

    Si no existe un `UsuariosSistema` asociado, se crea una postulación con id_beneficiario NULL.
    """
    proyecto = get_object_or_404(ProyectosHabitacionales, pk=pk)

    # intentar obtener beneficiario desde perfil
    beneficiario = None
    try:
        perfil = request.user.userprofile
        us = perfil.usuariosistema
        if us:
            # intentar mapear a Beneficiarios por rut/username
            beneficiario = Beneficiarios.objects.filter(rut=us.username).first()
            if not beneficiario:
                try:
                    # crear beneficiario mínimo para este usuario
                    beneficiario = Beneficiarios.objects.create(rut=us.username, nombre=us.nombre or request.user.first_name, apellidos=us.apellidos or request.user.last_name)
                except Exception as e:
                    beneficiario = None
    except Exception:
        beneficiario = None

    try:
        Postulaciones.objects.create(id_beneficiario=beneficiario, id_proyecto=proyecto, fecha_postulacion=datetime.date.today(), estado_postulacion='Pendiente')
        messages.success(request, 'Postulación registrada correctamente')
    except Exception as e:
        messages.error(request, f'Error al registrar postulación: {str(e)}')

    return redirect('gestion:proyecto_detail', pk=pk)


def postulaciones_list(request):
    """Lista de postulaciones con filtros por rol"""

    # Base queryset
    postulaciones = Postulaciones.objects.select_related(
        'id_beneficiario', 'id_proyecto'
    )

    # Filtrar según rol del usuario
    if request.user.is_authenticated:
        if request.user.is_staff:
            # Admin ve todas las postulaciones
            pass
        else:
            try:
                user_tipo = request.user.userprofile.tipo_usuario
                if user_tipo == 'empresa':
                    # Empresa ve postulaciones de sus proyectos
                    us = request.user.userprofile.usuariosistema
                    if us and us.id_empresa:
                        postulaciones = postulaciones.filter(
                            id_proyecto__id_empresa_constructora=us.id_empresa
                        )
                    else:
                        postulaciones = postulaciones.none()
                elif user_tipo == 'usuario':
                    # Usuario ve solo sus propias postulaciones
                    try:
                        beneficiario = request.user.userprofile.usuariosistema.beneficiario
                        if beneficiario:
                            postulaciones = postulaciones.filter(id_beneficiario=beneficiario)
                        else:
                            postulaciones = postulaciones.none()
                    except:
                        postulaciones = postulaciones.none()
                else:
                    # Otros tipos no ven postulaciones
                    postulaciones = postulaciones.none()
            except:
                postulaciones = postulaciones.none()
    else:
        postulaciones = postulaciones.none()

    # Filtros adicionales
    estado = request.GET.get('estado')

    if estado:
        postulaciones = postulaciones.filter(estado_postulacion=estado)

    # Opciones para filtros
    estados = Postulaciones.objects.values_list('estado_postulacion', flat=True).distinct()

    # Obtener proyectos para el modal de nueva postulación
    proyectos = ProyectosHabitacionales.objects.select_related('id_municipio', 'id_empresa_constructora').all()

    context = {
        'postulaciones': postulaciones,
        'estados': estados,
        'proyectos': proyectos,
    }

    return render(request, 'gestion/postulaciones_list.html', context)


@login_required
@require_POST
def postulacion_update(request, pk):
    """Actualizar estado de una postulacion (POST): 'estado' en POST.

    Permisos: staff o empresa dueña del proyecto.
    Redirige de vuelta a la página del proyecto.
    """
    try:
        postulacion = Postulaciones.objects.select_related('id_proyecto').get(pk=pk)
    except Postulaciones.DoesNotExist:
        return JsonResponse({'error': 'Postulación no encontrada'}, status=404)

    # permiso: staff o empresa dueña
    allowed = False
    if request.user.is_authenticated:
        if request.user.is_staff:
            allowed = True
        else:
            try:
                user_tipo = request.user.userprofile.tipo_usuario
            except Exception:
                user_tipo = None
            if user_tipo == 'empresa':
                try:
                    us = request.user.userprofile.usuariosistema
                    if us and us.id_empresa and postulacion.id_proyecto and postulacion.id_proyecto.id_empresa_constructora:
                        if us.id_empresa.id_empresa == postulacion.id_proyecto.id_empresa_constructora.id_empresa:
                            allowed = True
                except Exception:
                    allowed = False

    if not allowed:
        messages.error(request, 'No autorizado para modificar esta postulación')
        return redirect('gestion:proyecto_detail', pk=postulacion.id_proyecto.id_proyecto if postulacion.id_proyecto else None)

    estado = request.POST.get('estado')
    if estado:
        postulacion.estado_postulacion = estado
        try:
            postulacion.save()
            messages.success(request, 'Estado de postulación actualizado')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    else:
        messages.error(request, 'Falta el parámetro estado')

    return redirect('gestion:proyecto_detail', pk=postulacion.id_proyecto.id_proyecto if postulacion.id_proyecto else None)


# ===== API REST VIEWSETS =====

class BeneficiariosViewSet(viewsets.ModelViewSet):
    queryset = Beneficiarios.objects.select_related('id_municipio').all()
    serializer_class = BeneficiariosSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'apellidos', 'rut', 'email']
    ordering_fields = ['fecha_registro', 'puntaje_socioeconomico']
    ordering = ['-fecha_registro']
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de beneficiarios"""
        total = self.queryset.count()
        por_estado = dict(self.queryset.values('estado_beneficiario').annotate(total=Count('id_beneficiario')).values_list('estado_beneficiario', 'total'))
        puntaje_promedio = self.queryset.aggregate(Avg('puntaje_socioeconomico'))['puntaje_socioeconomico__avg']
        
        return Response({
            'total': total,
            'por_estado': por_estado,
            'puntaje_promedio': puntaje_promedio,
        })


class ProyectosHabitacionalesViewSet(viewsets.ModelViewSet):
    queryset = ProyectosHabitacionales.objects.select_related(
        'id_municipio', 'id_empresa_constructora', 'id_terreno'
    ).all()
    serializer_class = ProyectosHabitacionalesSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre_proyecto', 'descripcion']
    ordering_fields = ['fecha_inicio', 'numero_viviendas']
    ordering = ['-fecha_inicio']
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de proyectos"""
        total = self.queryset.count()
        por_estado = dict(self.queryset.values('estado_proyecto').annotate(total=Count('id_proyecto')).values_list('estado_proyecto', 'total'))
        total_viviendas = self.queryset.aggregate(Sum('numero_viviendas'))['numero_viviendas__sum'] or 0
        
        return Response({
            'total': total,
            'por_estado': por_estado,
            'total_viviendas': total_viviendas,
        })


class PostulacionesViewSet(viewsets.ModelViewSet):
    queryset = Postulaciones.objects.select_related('id_beneficiario', 'id_proyecto').all()
    serializer_class = PostulacionesSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['fecha_postulacion', 'puntaje_asignado']
    ordering = ['-fecha_postulacion']
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de postulaciones"""
        total = self.queryset.count()
        por_estado = dict(self.queryset.values('estado_postulacion').annotate(total=Count('id_postulacion')).values_list('estado_postulacion', 'total'))
        puntaje_promedio = self.queryset.aggregate(Avg('puntaje_asignado'))['puntaje_asignado__avg']
        
        return Response({
            'total': total,
            'por_estado': por_estado,
            'puntaje_promedio': puntaje_promedio,
        })


class MunicipiosViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Municipios.objects.select_related('id_region').all()
    serializer_class = MunicipiosSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['nombre_municipio', 'codigo_municipio']


class RegionesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Regiones.objects.all()
    serializer_class = RegionesSerializer


class EmpresasConstructorasViewSet(viewsets.ModelViewSet):
    queryset = EmpresasConstructoras.objects.all()
    serializer_class = EmpresasConstructorasSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['razon_social', 'rut_empresa']


class TerrenosViewSet(viewsets.ModelViewSet):
    queryset = Terrenos.objects.select_related('id_municipio').all()
    serializer_class = TerrenosSerializer


class LogAuditoriaViewSet(viewsets.ModelViewSet):
    queryset = LogAuditoria.objects.select_related('id_usuario').all()
    serializer_class = LogAuditoriaSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['accion', 'tabla', 'id_usuario__username']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']


class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.select_related('id_usuario').all()
    serializer_class = NotificacionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['tipo', 'mensaje', 'id_usuario__username']
    ordering_fields = ['fecha_envio']
    ordering = ['-fecha_envio']


class MatchingViewSet(viewsets.ModelViewSet):
    queryset = Matching.objects.select_related('id_beneficiario', 'id_proyecto').all()
    serializer_class = MatchingSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['id_beneficiario__nombre', 'id_proyecto__nombre_proyecto']
    ordering_fields = ['fecha_matching', 'puntaje_compatibilidad']
    ordering = ['-fecha_matching']


# ===== API Endpoints adicionales =====

@api_view(['GET'])
def dashboard_api(request):
    """API del dashboard con todas las estadísticas"""

    stats = {
        'totales': {
            'beneficiarios': Beneficiarios.objects.count(),
            'proyectos': ProyectosHabitacionales.objects.count(),
            'postulaciones': Postulaciones.objects.count(),
            'empresas': EmpresasConstructoras.objects.count(),
            'matchings': Matching.objects.count(),
            'notificaciones': Notificacion.objects.count(),
        },
        'beneficiarios': {
            'por_estado': dict(Beneficiarios.objects.values('estado_beneficiario').annotate(total=Count('id_beneficiario')).values_list('estado_beneficiario', 'total')),
            'puntaje_promedio': Beneficiarios.objects.aggregate(Avg('puntaje_socioeconomico'))['puntaje_socioeconomico__avg'],
            'ingresos_promedio': Beneficiarios.objects.aggregate(Avg('ingresos_familiares'))['ingresos_familiares__avg'],
        },
        'proyectos': {
            'por_estado': dict(ProyectosHabitacionales.objects.values('estado_proyecto').annotate(total=Count('id_proyecto')).values_list('estado_proyecto', 'total')),
            'total_viviendas': ProyectosHabitacionales.objects.aggregate(Sum('numero_viviendas'))['numero_viviendas__sum'] or 0,
        },
        'postulaciones': {
            'por_estado': dict(Postulaciones.objects.values('estado_postulacion').annotate(total=Count('id_postulacion')).values_list('estado_postulacion', 'total')),
        },
        'matching': {
            'por_estado': dict(Matching.objects.values('estado').annotate(total=Count('id_matching')).values_list('estado', 'total')),
            'puntaje_promedio': Matching.objects.aggregate(Avg('puntaje_compatibilidad'))['puntaje_compatibilidad__avg'],
        },
        'auditoria': {
            'total_logs': LogAuditoria.objects.count(),
            'logs_recientes': LogAuditoria.objects.order_by('-timestamp')[:5].values('accion', 'tabla', 'timestamp'),
        },
    }

    return Response(stats)


@api_view(['POST'])
def ejecutar_matching_api(request):
    """API para ejecutar el algoritmo de matching automático"""
    try:
        region_id = request.data.get('region_id')
        municipio_id = request.data.get('municipio_id')
        limite_proyectos = request.data.get('limite_proyectos')

        # Ejecutar matching
        resultados = MatchingAlgorithm.ejecutar_matching(
            region_id=region_id,
            municipio_id=municipio_id,
            limite_proyectos=limite_proyectos
        )

        # Log de auditoría
        LogAuditoria.objects.create(
            id_usuario=request.user.userprofile.usuariosistema if request.user.is_authenticated and hasattr(request.user, 'userprofile') else None,
            accion='EJECUTAR_MATCHING',
            tabla='Matching',
            registro_afectado=None,
            datos_anteriores={},
            datos_nuevos={'procesados': resultados['procesados'], 'matchings_creados': resultados['matchings_creados']}
        )

        return Response({
            'success': True,
            'resultados': resultados
        })

    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['POST'])
def aprobar_matching_api(request, matching_id):
    """API para aprobar un matching"""
    try:
        usuario = request.user if request.user.is_authenticated else None
        success = MatchingAlgorithm.aprobar_matching(matching_id, usuario)

        if success:
            return Response({'success': True, 'message': 'Matching aprobado correctamente'})
        else:
            return Response({'success': False, 'error': 'Error al aprobar matching'}, status=400)

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


@api_view(['POST'])
def rechazar_matching_api(request, matching_id):
    """API para rechazar un matching"""
    try:
        motivo = request.data.get('motivo', 'Rechazado por el sistema')
        usuario = request.user if request.user.is_authenticated else None
        success = MatchingAlgorithm.rechazar_matching(matching_id, motivo, usuario)

        if success:
            return Response({'success': True, 'message': 'Matching rechazado correctamente'})
        else:
            return Response({'success': False, 'error': 'Error al rechazar matching'}, status=400)

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=500)


def generar_mapa(lat, lng, popup_text, zoom_start=15):
    """Genera un mapa con Folium centrado en lat, lng con un marcador."""
    if not lat or not lng:
        return None
    mapa = folium.Map(location=[lat, lng], zoom_start=zoom_start)
    folium.Marker([lat, lng], popup=popup_text).add_to(mapa)
    return mapa._repr_html_()

def geocodificar_direccion(direccion, municipio=None, region=None):
    """Geocodifica una dirección usando geopy."""
    geolocator = Nominatim(user_agent="sistema_habitacional")
    query = direccion
    if municipio:
        query += f", {municipio}"
    if region:
        query += f", {region}, Chile"
    try:
        location = geolocator.geocode(query, timeout=10)
        if location:
            return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderUnavailable):
        pass
    return None, None

# Create your views here.
