from django.test import LiveServerTestCase, Client
from django.contrib.auth.models import User
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import time

# webdriver-manager will download the chromedriver automatically if available
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    HAS_WEBDRIVER = True
except Exception:
    HAS_WEBDRIVER = False


class CalendarModalUITest(LiveServerTestCase):
    """UI test que abre el calendario, lanza el modal y verifica que no queden backdrops.

    Requisitos locales antes de ejecutar:
    - Tener Google Chrome instalado (o ajustar para usar otro navegador/local driver).
    - Instalar dependencias: `pip install -r requirements-dev.txt` (incluye selenium, webdriver-manager)

    Ejecutar:
    python manage.py test appejemplo.tests_ui_calendar_modal -v 2
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not HAS_WEBDRIVER:
            raise RuntimeError('webdriver-manager or selenium no disponible; instala dependencies de dev')

        options = ChromeOptions()
        # headless mode is optional; set to False if you want to watch the browser
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1200,900')

        try:
            cls.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            cls.driver.implicitly_wait(5)
        except WebDriverException as e:
            raise RuntimeError(f'No se pudo inicializar Chrome WebDriver: {e}')

    @classmethod
    def tearDownClass(cls):
        try:
            cls.driver.quit()
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        # crear usuario y cliente de test para conseguir cookie de sesión
        self.username = 'uitestuser'
        self.password = 'testpass'
        self.user = User.objects.create_user(self.username, password=self.password)
        self.user.is_staff = True
        self.user.save()

        self.client = Client()
        logged = self.client.login(username=self.username, password=self.password)
        assert logged, 'No se pudo loggear el usuario de test'

    def test_open_close_modal_no_backdrop_left(self):
        # obtener cookie de sesión del cliente Django y añadirla al navegador
        sessionid = self.client.cookies.get(settings.SESSION_COOKIE_NAME).value

        # visitar dominio para poder setear cookies
        self.driver.get(self.live_server_url + '/')
        self.driver.add_cookie({
            'name': settings.SESSION_COOKIE_NAME,
            'value': sessionid,
            'path': '/',
        })

        # abrir la página del calendario
        self.driver.get(self.live_server_url + '/calendar/')

        wait = WebDriverWait(self.driver, 20)

        # esperar que el botón exista (no forzamos clickable para evitar overlays)
        btn = wait.until(EC.presence_of_element_located((By.ID, 'btnOpenAddEvent')))
        # abrir modal mediante el helper expuesto (más robusto en entornos headless)
        self.driver.execute_script('window.modalShow && window.modalShow();')

        # esperar modal visible via stable state token
        wait.until(lambda d: d.execute_script("return window._modalLastAction === 'shown'"))

        # cerrar vía helper expuesto por la plantilla (más robusto que click directo)
        self.driver.execute_script('window.modalHide && window.modalHide();')
        # esperar a que modal indique estado hidden
        wait.until(lambda d: d.execute_script("return window._modalLastAction === 'hidden'"))
        time.sleep(0.5)
        # comprobar que no hay backdrops y que body no contiene clase modal-open
        backdrops = self.driver.find_elements(By.CSS_SELECTOR, '.modal-backdrop')
        body_classes = self.driver.execute_script('return document.body.className')

        self.assertEqual(len(backdrops), 0, f'Quedan backdrops en DOM: {len(backdrops)}')
        self.assertFalse('modal-open' in body_classes.split(), f'body aún tiene modal-open: {body_classes}')

        # Reabrir y cerrar usando helpers
        self.driver.execute_script('window.modalShow && window.modalShow();')
        wait.until(lambda d: d.execute_script("return window._modalLastAction === 'shown'"))
        # usar helper para cerrar (evita problemas con keys in headless)
        self.driver.execute_script('window.modalHide && window.modalHide();')
        wait.until(lambda d: d.execute_script("return window._modalLastAction === 'hidden'"))
        backdrops = self.driver.find_elements(By.CSS_SELECTOR, '.modal-backdrop')
        body_classes = self.driver.execute_script('return document.body.className')
        self.assertEqual(len(backdrops), 0, 'Backdrop leftover after close')
        self.assertFalse('modal-open' in body_classes.split(), 'body.modal-open still present after close')
