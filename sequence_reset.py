import os

os.environ['DJANGO_COLORS'] = 'nocolor'

from django.core.management import call_command
from django.conf import settings
from django.db import connection
from django.db.models.loading import get_app
from StringIO import StringIO

commands = StringIO()
cursor = connection.cursor()

for app in settings.INSTALLED_APPS:
    label = app.split('.')[-1]
    if get_app(label, emptyOK=True):
        call_command('sqlsequencereset', label, stdout=commands)

cursor.execute(commands.getvalue())