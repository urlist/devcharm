"""
Django settings for devcharm project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ADMINS = (
    ('Alberto Granzotto', 'alberto@devcharm.com'),
)

# Email settings, use gmail SMTP
SERVER_EMAIL = 'root@devcharm.com'
EMAIL_HOST_USER = SERVER_EMAIL


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'XXX'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = not os.path.exists(os.path.join(BASE_DIR, "PRODUCTION"))
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = [
    'devcharm.com',
    'django.devcharm.com',
    'www.devcharm.com',
]

INTERNAL_IPS = [
    '127.0.0.1',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'pipeline',

    #'django_extensions',
    'social.apps.django_app.default',
    'gunicorn',
    #'debug_toolbar',
    'south',

    'static_pages',
    'articles',
    'tags',
    'profiles',
    'scoring',
    'docs',

    'styleguide',
]

MIDDLEWARE_CLASSES = (
    #'debug_toolbar.middleware.DebugToolbarMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

ROOT_URLCONF = 'devcharm.urls'

WSGI_APPLICATION = 'devcharm.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'devcharm',
        'USER': 'devcharm',
        'PASSWORD': '33fb59ea',
    }
}

SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 52 * 10

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'devcharm/static'),
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'stylus'),
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'social.apps.django_app.context_processors.backends',
)

AUTHENTICATION_BACKENDS = (
    'social.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_STRATEGY = 'social.strategies.django_strategy.DjangoStrategy'
SOCIAL_AUTH_STORAGE = 'social.apps.django_app.default.models.DjangoStorage'

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.user_details',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'profiles.pipeline.complete_profile',
)

if DEBUG:
    SOCIAL_AUTH_GITHUB_KEY = 'XXX'
    SOCIAL_AUTH_GITHUB_SECRET = 'XXX'
else:
    SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
    SOCIAL_AUTH_GITHUB_KEY = 'XXX'
    SOCIAL_AUTH_GITHUB_SECRET = 'XXX'

SOCIAL_AUTH_GITHUB_SCOPE = ['user:email', ]

LOGIN_URL = '/login/github'
LOGIN_REDIRECT_URL = '/'

# Settings for Django Pipeline
PIPELINE_COMPILERS = (
    'pipeline.compilers.stylus.StylusCompiler',
)

PIPELINE_CSS = {
    'waffle': {
        'source_filenames': (
            'waffle/waffle.styl',
        ),
        'output_filename': 'css/waffle.css',
    },
    'main': {
        'source_filenames': (
            'devcharm/index.styl',
        ),
        'output_filename': 'css/style.css',
    }
}

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

# Output customization
PROFILE_PAGE_NUM_SUGGESTED_WIP_ARTICLES = 10
PROFILE_PAGE_NUM_SCORE_TRANSACTIONS = 15

TOTAL_RANDOM_IMAGES = 12

ACTIVITY_POINTS = {
    'editing_article': 2,
    'adding_links': 10,
    'creating_article': 50,
    'receiving_kudos_as_author': 5,
    'receiving_kudos_as_editor': 1,
}

SOUTH_TESTS_MIGRATE = False

try:
    from local_settings import *
except ImportError:
    pass
