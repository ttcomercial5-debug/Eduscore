"""
Django settings for school_system project.
SaaS Multi-Escolas - Produção Comercial
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================
# SEGURANÇA
# =====================================================

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-dev-key-change-in-production')

DEBUG = True

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

# =====================================================
# APLICAÇÕES
# =====================================================

INSTALLED_APPS = [

    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',


    # Terceiros
    'rest_framework',

    # Apps do sistema
    'core',
    'users',
    'academic',
    'finance',
    'channels',


]

ASGI_APPLICATION = "school_system.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# =====================================================
# BANCO DE DADOS
# =====================================================

# IMPORTANTE:
# Para produção SaaS use PostgreSQL
# Exemplo já preparado abaixo

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Trocar para PostgreSQL em produção
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

"""
# EXEMPLO PRODUÇÃO POSTGRESQL

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'eduscore',
        'USER': 'eduscore_user',
        'PASSWORD': 'ManoChaba2018G',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
"""

# =====================================================
# USER MODEL CUSTOM
# =====================================================

AUTH_USER_MODEL = 'users.User'

# =====================================================
# REST FRAMEWORK (API)
# =====================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# =====================================================
# MIDDLEWARE
# =====================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.EscolaAtivaMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AdminRestritoMiddleware',

    # Futuro middleware para bloqueio de escola
    # 'core.middleware.EscolaAtivaMiddleware',
]

# =====================================================
# URLS
# =====================================================

ROOT_URLCONF = 'school_system.urls'

# =====================================================
# TEMPLATES
# =====================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Pasta global opcional
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'school_system.wsgi.application'

# =====================================================
# SENHAS
# =====================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# =====================================================
# INTERNACIONALIZAÇÃO
# =====================================================

LANGUAGE_CODE = 'pt-pt'

TIME_ZONE = 'Africa/Luanda'

USE_I18N = True
USE_TZ = True

# =====================================================
# ARQUIVOS ESTÁTICOS
# =====================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================
# LOGIN
# =====================================================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'


# =====================================
# KAMBAS SMS CONFIGURATION
# =====================================


KAMBAS_SMS_URL = ""

KAMBAS_SMS_TOKEN = ""

KAMBAS_SMS_SENDER = "EdusCel"