"""
Django settings for school_system project.

EdusCel
SaaS Multi-Escolas
Configuração preparada para Produção com PostgreSQL
"""

from pathlib import Path
import os

from dotenv import load_dotenv


# =====================================================
# CARREGAR VARIÁVEIS DE AMBIENTE
# =====================================================

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent



# =====================================================
# SEGURANÇA
# =====================================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-dev-key-change-in-production"
)


DEBUG = os.getenv(
    "DEBUG",
    "False"
) == "True"



ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "142.93.254.1,127.0.0.1,localhost"
).split(",")



# Segurança adicional

SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"



# =====================================================
# APLICAÇÕES
# =====================================================

INSTALLED_APPS = [


    # Django

    "django.contrib.admin",

    "django.contrib.auth",

    "django.contrib.contenttypes",

    "django.contrib.sessions",

    "django.contrib.messages",

    "django.contrib.staticfiles",

    "django.contrib.humanize",



    # Terceiros

    "rest_framework",



    # Sistema EdusCel

    "core",

    "users",

    "academic",

    "finance",


    # WebSocket

    "channels",

]



# =====================================================
# CHANNELS
# =====================================================


ASGI_APPLICATION = (
    "school_system.asgi.application"
)


CHANNEL_LAYERS = {

    "default": {

        "BACKEND":
            "channels.layers.InMemoryChannelLayer"

    }

}



# =====================================================
# BANCO DE DADOS
# PostgreSQL obrigatório no servidor
# SQLite apenas quando definido manualmente
# =====================================================


USE_POSTGRES = os.getenv(
    "USE_POSTGRES",
    "True"
) == "True"



if USE_POSTGRES:


    DATABASES = {

        "default": {


            "ENGINE":
                "django.db.backends.postgresql",



            "NAME":
                os.getenv(
                    "POSTGRES_DB",
                    "eduscore"
                ),



            "USER":
                os.getenv(
                    "POSTGRES_USER",
                    "eduscore_user"
                ),



            "PASSWORD":
                os.getenv(
                    "POSTGRES_PASSWORD",
                    ""
                ),



            "HOST":
                os.getenv(
                    "POSTGRES_HOST",
                    "localhost"
                ),



            "PORT":
                os.getenv(
                    "POSTGRES_PORT",
                    "5432"
                ),



            "CONN_MAX_AGE":
                600,



            "CONN_HEALTH_CHECKS":
                True,

        }

    }



else:


    DATABASES = {

        "default": {


            "ENGINE":
                "django.db.backends.sqlite3",



            "NAME":
                BASE_DIR / "db.sqlite3",

        }

    }

# =====================================================
# USER MODEL CUSTOM
# =====================================================

AUTH_USER_MODEL = "users.User"



# =====================================================
# REST FRAMEWORK (API)
# =====================================================

REST_FRAMEWORK = {


    "DEFAULT_AUTHENTICATION_CLASSES": (

        "rest_framework_simplejwt.authentication.JWTAuthentication",

    ),



    "DEFAULT_PERMISSION_CLASSES": (

        "rest_framework.permissions.IsAuthenticated",

    ),

}



# =====================================================
# MIDDLEWARE
# =====================================================

MIDDLEWARE = [


    "django.middleware.security.SecurityMiddleware",


    "django.contrib.sessions.middleware.SessionMiddleware",


    "django.middleware.common.CommonMiddleware",


    "django.middleware.csrf.CsrfViewMiddleware",


    "django.contrib.auth.middleware.AuthenticationMiddleware",



    # Middleware EdusCel
    # Verificação de escola ativa
    "core.middleware.EscolaAtivaMiddleware",



    "django.contrib.messages.middleware.MessageMiddleware",


    "django.middleware.clickjacking.XFrameOptionsMiddleware",



    # Restrição de acesso administrativo
    "core.middleware.AdminRestritoMiddleware",


]



# =====================================================
# URLS
# =====================================================

ROOT_URLCONF = "school_system.urls"



# =====================================================
# TEMPLATES
# =====================================================

TEMPLATES = [


    {


        "BACKEND":
            "django.template.backends.django.DjangoTemplates",



        "DIRS": [

            BASE_DIR / "templates",

        ],



        "APP_DIRS": True,



        "OPTIONS": {


            "context_processors": [


                "django.template.context_processors.request",


                "django.contrib.auth.context_processors.auth",


                "django.contrib.messages.context_processors.messages",


            ],

        },


    },

]



# =====================================================
# WSGI / ASGI
# =====================================================

WSGI_APPLICATION = (
    "school_system.wsgi.application"
)



ASGI_APPLICATION = (
    "school_system.asgi.application"
)



# =====================================================
# CONFIGURAÇÃO DE SENHAS
# =====================================================

AUTH_PASSWORD_VALIDATORS = [



    {


        "NAME":
        "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",

    },



    {


        "NAME":
        "django.contrib.auth.password_validation.MinimumLengthValidator",


        "OPTIONS": {

            "min_length": 8

        },

    },



    {


        "NAME":
        "django.contrib.auth.password_validation.CommonPasswordValidator",

    },



    {


        "NAME":
        "django.contrib.auth.password_validation.NumericPasswordValidator",

    },


]



# =====================================================
# INTERNACIONALIZAÇÃO
# =====================================================

LANGUAGE_CODE = "pt-pt"



TIME_ZONE = "Africa/Luanda"



USE_I18N = True


USE_TZ = True



# =====================================================
# SESSÕES E SEGURANÇA DE LOGIN
# =====================================================

SESSION_COOKIE_AGE = 1800


# Expira ao fechar navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# Proteção adicional

SESSION_COOKIE_HTTPONLY = True


CSRF_COOKIE_HTTPONLY = False

# =====================================================
# ARQUIVOS ESTÁTICOS
# =====================================================

STATIC_URL = "/static/"


STATIC_ROOT = BASE_DIR / "staticfiles"



STATICFILES_DIRS = [

    BASE_DIR / "static",

]



# =====================================================
# MEDIA (UPLOADS)
# =====================================================

MEDIA_URL = "/media/"


MEDIA_ROOT = BASE_DIR / "media"



# =====================================================
# DEFAULT PRIMARY KEY
# =====================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)



# =====================================================
# LOGIN / LOGOUT
# =====================================================

LOGIN_URL = "/login/"


LOGIN_REDIRECT_URL = "/dashboard/"


LOGOUT_REDIRECT_URL = "/login/"



# =====================================================
# CONFIGURAÇÃO DE EMAIL
# Preparado para recuperação de senha
# =====================================================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)


EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    ""
)


EMAIL_PORT = int(
    os.getenv(
        "EMAIL_PORT",
        587
    )
)


EMAIL_USE_TLS = True


EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    ""
)


EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    ""
)



# =====================================================
# KAMBAS SMS CONFIGURATION
# =====================================================

KAMBAS_SMS_URL = os.getenv(
    "KAMBAS_SMS_URL",
    ""
)


KAMBAS_SMS_TOKEN = os.getenv(
    "KAMBAS_SMS_TOKEN",
    ""
)


KAMBAS_SMS_SENDER = os.getenv(
    "KAMBAS_SMS_SENDER",
    "EdusCel"
)



# =====================================================
# LOGGING
# Registo de erros para produção
# =====================================================

LOGGING = {


    "version": 1,


    "disable_existing_loggers": False,


    "handlers": {


        "file": {


            "class":
            "logging.FileHandler",


            "filename":
            BASE_DIR / "logs" / "django_errors.log",


        },

    },



    "loggers": {


        "django": {


            "handlers": [

                "file"

            ],


            "level":
            "ERROR",


            "propagate": True,

        },

    },

}



# =====================================================
# PRODUÇÃO HTTPS (ativar quando tiver SSL)
# =====================================================

# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True