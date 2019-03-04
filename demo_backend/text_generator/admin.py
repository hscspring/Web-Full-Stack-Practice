from django.contrib import admin

# Register your models here.

from .models import TextGenerator

admin.site.register(TextGenerator)