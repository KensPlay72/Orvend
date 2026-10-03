from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    """Lee valores booleanos sin duplicar configuraciones por entorno."""
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# SECURITY
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY debe estar definido en el entorno.")

DEBUG = env_bool("DJANGO_DEBUG", False)

# En desarrollo se permiten los hosts locales. Producción debe declarar el
# dominio público explícitamente mediante DJANGO_ALLOWED_HOSTS.
ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1" if DEBUG else ""
)

_csrf_origins = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
# Django no admite '*' como origen CSRF. En desarrollo no es necesario para
# peticiones del mismo origen; en producción se exige URL con http(s).
CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in _csrf_origins
    if origin != "*" and origin.startswith(("http://", "https://"))
]
if not DEBUG and any(origin == "*" for origin in _csrf_origins):
    raise RuntimeError(
        "DJANGO_CSRF_TRUSTED_ORIGINS no puede ser '*'. Usa las URLs HTTPS del dominio."
    )

# APPLICATIONS
INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps propias
    "pages",
    "accounts",
    "manager.apps.ManagerConfig",
]


# MIDDLEWARE
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "manager.middleware.SecurityHeadersMiddleware",
    # Servir archivos static con Gunicorn
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "manager.middleware.SuscripcionActivaMiddleware",
    "manager.middleware.CierreCajaPendienteMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "OrvendMart.urls"


# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Carpeta global templates si existe
        "DIRS": [BASE_DIR / "templates"],
        # Busca templates dentro de las apps
        "APP_DIRS": True,
        "OPTIONS": {
            # esté disponible en todos los templates de manager.
            "libraries": {
                "pagination_tags": "manager.templatetags.pagination_tags",
            },
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "manager.context_processors.tema_empresa",
            ],
        },
    },
]


WSGI_APPLICATION = "OrvendMart.wsgi.application"
ASGI_APPLICATION = "OrvendMart.asgi.application"

REDIS_URL = os.getenv("REDIS_URL", "").strip()
CHANNEL_LAYERS = {
    "default": (
        {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
        if REDIS_URL
        else {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    )
}


# DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        # Docker network
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
    }
}


# PASSWORD VALIDATION
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# LANGUAGE
LANGUAGE_CODE = 'en-us'
# SESSION
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = os.getenv(
    "DJANGO_REFERRER_POLICY", "strict-origin-when-cross-origin"
)
# Solo se envía HSTS en producción HTTPS. Cloudflare transmite el protocolo
# original mediante X-Forwarded-Proto, configurado arriba.
SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data: https://fonts.gstatic.com",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com https://cdn.jsdelivr.net",
        "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.jsdelivr.net",
        "connect-src 'self' ws: wss:",
        "frame-src 'none'",
    ]
)
PERMISSIONS_POLICY = "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

TIME_ZONE = "America/Tegucigalpa"

USE_I18N = True
USE_TZ = True


# STATIC FILES
# -----------------------------

# URL pública
STATIC_URL = "/static/"


# Carpeta donde collectstatic junta todo
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]


# Compresión y cache para producción
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# MEDIA FILES
# -----------------------------

MEDIA_URL = "/manager/media/"
MEDIA_ROOT = BASE_DIR / "manager" / "media"


# AUTH
# -----------------------------

LOGIN_URL = "/accounts/login/"

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/accounts/login/"

PUBLIC_ASSETS_ROOT = BASE_DIR / "public_assets"

# SESSION
# -----------------------------

SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# DEFAULT PRIMARY KEY
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# NEXTCLOUD
NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL")
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD")
NEXTCLOUD_FOLDER_PRODUCTOS = os.getenv("NEXTCLOUD_FOLDER_PRODUCTOS")
NEXTCLOUD_FOLDER_CONFI = os.getenv("NEXTCLOUD_FOLDER_CONFI")


SESSION_COOKIE_AGE = 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# WhatsApp / n8n: credenciales fuera del código fuente.
N8N_FACTURA_WHATSAPP_WEBHOOK_URL = os.getenv("N8N_FACTURA_WHATSAPP_WEBHOOK_URL")
N8N_FACTURA_WHATSAPP_USER = os.getenv("N8N_FACTURA_WHATSAPP_USER")
N8N_FACTURA_WHATSAPP_PASSWORD = os.getenv("N8N_FACTURA_WHATSAPP_PASSWORD")
FACTURA_PUBLIC_BASE_URL = os.getenv("FACTURA_PUBLIC_BASE_URL", "").strip()
N8N_FACTURA_URL_EXPIRA_SEGUNDOS = int(
    os.getenv("N8N_FACTURA_URL_EXPIRA_SEGUNDOS", "60")
)
