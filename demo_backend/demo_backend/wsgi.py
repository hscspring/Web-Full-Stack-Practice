"""
WSGI config for demo_backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

profile = os.environ.get('DEMO_PROFILE', 'develop')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo_backend.settings.%s' % profile)
# os.environ['DJANGO_SETTINGS_MODULE'] = 'demo_backend.settings.%s' % profile

application = get_wsgi_application()
