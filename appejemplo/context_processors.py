def user_tipo(request):
    """Context processor que devuelve el tipo de usuario en `user_tipo`.

    Devuelve None si no hay usuario autenticado o si no existe perfil.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'user_tipo': None}
    try:
        return {'user_tipo': request.user.userprofile.tipo_usuario}
    except Exception:
        return {'user_tipo': None}
