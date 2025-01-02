from django.db import models

# Create your models here.

class KubeConfig(models.Model):
    cluster_id = models.AutoField(primary_key=True)
    path = models.CharField(max_length=255, help_text="Path to the kube config file")
    path_type = models.CharField(
        max_length=50,
        choices=[('default', 'Default'), ('manual', 'Manual')],
        help_text="Type of path (default or manual)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.path} ({self.path_type})"