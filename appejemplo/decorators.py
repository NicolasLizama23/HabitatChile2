from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.utils import timezone
from django.conf import settings
import datetime


def check_session_expired(request):
    """Verifica si la sesión ha expirado"""
    last_activity = request.session.get('last_activity')
    if last_activity:
        # Convertir last_activity a datetime aware
        last_activity_dt = timezone.make_aware(datetime.datetime.fromtimestamp(last_activity))
        elapsed = timezone.now() - last_activity_dt
        if elapsed.seconds > settings.SESSION_COOKIE_AGE:
            logout(request)
            return True
    request.session['last_activity'] = timezone.now().timestamp()
    return False


def role_required(*allowed_roles):
    """Decorador que permite el acceso solo a usuarios con userprofile.tipo_usuario en allowed_roles.
    También verifica la sesión y los permisos del usuario.

    Uso: @role_required('usuario') o @role_required('empresa','admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Debe iniciar sesión para acceder a esta página')
                return redirect('gestion:login')

            try:
                tipo = request.user.userprofile.tipo_usuario
            except Exception:
                tipo = None

            # Verificar si la sesión ha expirado
            if check_session_expired(request):
                messages.error(request, 'Tu sesión ha expirado. Por favor, inicia sesión nuevamente.')
                return redirect('gestion:login')

            # Verificar roles y permisos
            if tipo in allowed_roles or request.user.is_superuser or (request.user.is_staff and 'admin' in allowed_roles):
                # Actualizar última actividad
                request.session['last_activity'] = timezone.now().timestamp()
                return view_func(request, *args, **kwargs)

            messages.error(request, 'No tienes los permisos necesarios para acceder a esta página')
            return redirect('gestion:dashboard')

        return _wrapped
    return decorator
