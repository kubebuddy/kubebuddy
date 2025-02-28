from django.contrib import admin
from main.models import KubeConfig, AIConfig
# Register your models here.
admin.site.register(KubeConfig)
admin.site.register(AIConfig)