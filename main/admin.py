from django.contrib import admin
from main.models import KubeConfig, AIConfig, Cluster
# Register your models here.
admin.site.register(KubeConfig)
admin.site.register(Cluster)
admin.site.register(AIConfig)