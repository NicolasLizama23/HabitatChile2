# pjrEjemplo — Instrucciones rápidas

Este README explica cómo arrancar el proyecto Django `pjrEjemplo` en un entorno de desarrollo local.

Resumen de cambios recientes realizados para facilitar el arranque:
- Se corrigieron referencias residuales a `housing_project` en `pjrEjemplo/pjrEjemplo/settings.py` (ROOT_URLCONF y WSGI_APPLICATION).
- Se eliminó una inclusión a la app `gestion` en `pjrEjemplo/pjrEjemplo/urls.py` porque no existe en este repo.
- Se añadió soporte opcional para usar SQLite en desarrollo mediante la variable de entorno `USE_SQLITE=1`.
- Se creó la carpeta `pjrEjemplo/static` para resolver una advertencia de staticfiles.

Requisitos
- Python 3.10+ (tu instalación actual funciona si ya corriste `manage.py` anteriormente).
- Django y dependencias definidas en tu entorno (rest_framework, drf_yasg, corsheaders, mysqlclient si usas MySQL, etc.).

Arrancar con SQLite (recomendado para desarrollo rápido)

En PowerShell (desde la carpeta `pjrEjemplo`):

```powershell
# Crear migraciones base (si es la primera vez)
$env:USE_SQLITE='1'; python manage.py migrate

# Crear superusuario (opcional)
$env:USE_SQLITE='1'; python manage.py createsuperuser

# Ejecutar servidor de desarrollo
$env:USE_SQLITE='1'; python manage.py runserver
```

Arrancar usando MySQL (si prefieres usar la base de datos configurada en settings)

1. Asegúrate de que MySQL está instalado y corriendo (por ejemplo XAMPP).  
2. Verifica que los parámetros en `pjrEjemplo/pjrEjemplo/settings.py` bajo `MYSQL_DATABASE` (NAME, USER, PASSWORD, HOST, PORT) son correctos.  
3. Ejecuta:

```powershell
# (no establecer USE_SQLITE)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Notas y resolución de problemas comunes
- Error "No module named 'housing_project'": ya corregido. Si encuentras otros "ModuleNotFoundError" revisa `pjrEjemplo/pjrEjemplo/urls.py` y `INSTALLED_APPS` en `settings.py` para referencias a apps que no estén en el repositorio.
- Error de conexión MySQL (10061): indica que MySQL no está corriendo o las credenciales/host están mal. Usa SQLite para desarrollo si no quieres configurar MySQL.
 - Error de conexión MySQL (10061): indica que MySQL no está corriendo o las credenciales/host están mal. Usa SQLite para desarrollo si no quieres configurar MySQL.
 - Error VariableDoesNotExist al ver detalle de un proyecto: si ves una pantalla amarilla con "Failed lookup for key [precio_vivienda]" u otras claves similares, significa que la plantilla intentaba acceder a un atributo que no existe en el modelo. Se corrigió `templates/gestion/proyecto_detail.html` para usar los campos reales (`precio_unitario`) y valores por defecto seguros. Si ves errores parecidos, revisa la plantilla y evita pasar variables inexistentes como argumentos a filtros (`|default:otra_variable`), usa en su lugar `|default:"valor"` o condicionales `{% if %}`.
- Advertencia sobre `STATICFILES_DIRS` inexistente: se creó la carpeta `static`. Puedes añadir tus archivos estáticos ahí.

Siguientes pasos sugeridos
- Si el proyecto realmente necesita la app `gestion`, localiza o restaura esa app y vuelve a incluirla en `urls.py` y `INSTALLED_APPS`.
- Considerar usar un `.env` y `django-environ` o `python-dotenv` para manejar credenciales y la variable `USE_SQLITE` de forma segura.

Integración con API de mapas (Tullim)
 - Objetivo: mostrar la ubicación de los proyectos tanto para usuarios como para empresas usando la API de mapas de Tullim.
 - Implementación incluida: las plantillas `templates/gestion/proyectos_list.html` y `templates/gestion/proyecto_detail.html` ya contienen un mapa cliente que intentará usar el SDK de Tullim si lo cargas; si no, cae en un fallback usando Leaflet (OpenStreetMap).
 - Pasos para integrar Tullim correctamente:
	 1. Obtén tu clave/SDK de Tullim (proporcionada por Tullim).
	 2. En tu `base.html` (o en `proyectos_list.html`), añade la inclusión del SDK de Tullim según la documentación oficial. Ejemplo (placeholder):

```html
<!-- Reemplaza con la URL/forma provista por Tullim -->
<script src="https://sdk.tullim.example/tullim-sdk.js" defer></script>
<meta name="tullim-api-key" content="TU_CLAVE_TULLIM">
```

	 3. El código cliente en las plantillas detecta `window.Tullim` y, si existe, intenta usar funciones genéricas (`createMap`, `addMarker`). Reemplaza las llamadas placeholder por las funciones reales del SDK según la documentación de Tullim.
	 4. Asegúrate de que tus proyectos/terrenos tienen `latitud` y `longitud` en la base de datos. El serializer de proyectos expone ahora `terreno_latitud`, `terreno_longitud`, `empresa_latitud` y `empresa_longitud` para que el front pueda leer coordenadas desde `/api/proyectos/`.

 - Fallback: si no se carga Tullim, el mapa usará Leaflet/OpenStreetMap automáticamente (no necesita clave).

Si quieres, puedo:
 - Añadir una página de configuración en el admin para guardar la `TULLIM_API_KEY` y exponerla automáticamente a las plantillas.
 - Reemplazar los placeholders con la inicialización exacta del SDK de Tullim si me proporcionas la URL del SDK o la documentación de inicialización.

Si quieres, agrego instrucciones en el `manage.py` (comentario) y/o preparo un `.env.example` y la integración con `django-environ`.
