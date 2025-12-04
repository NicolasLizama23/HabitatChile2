UI test para el modal del calendario

Requisitos locales:
- Google Chrome instalado (o ajustar el driver para usar otro navegador).
- Python env con dependencias de dev instaladas.

Instalación rápida:

```powershell
cd c:\Users\Ariel\Downloads\Ev02\Ev02\ejemplodb\pjrEjemplo
python -m pip install -r requirements-dev.txt
```

Ejecutar el test (usa LiveServerTestCase y webdriver-manager para descargar ChromeDriver):

```powershell
python manage.py test appejemplo.tests_ui_calendar_modal -v 2
```

Notas:
- Si ejecutas en modo headless y el test falla por falta de Chrome, intenta ejecutar con un navegador visible (quitar `--headless` en el archivo de test) o instala Chrome en el runner.
- El test usa la cookie de sesión generada por `django.test.Client()` para evitar la pantalla de login.
