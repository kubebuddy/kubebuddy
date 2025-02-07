from django.db import models
from django.utils.timezone import now
# Create your models here.

class KubeConfig(models.Model):
    cluster_id = models.CharField(primary_key=True, max_length=20, unique=True, editable=False)
    path = models.CharField(max_length=255, help_text="Path to the kube config file")
    path_type = models.CharField(
        max_length=50,
        choices=[('default', 'Default'), ('manual', 'Manual')],
        help_text="Type of path (default or manual)"
    )
    created_at = models.DateTimeField(default=now, editable=False)

    def save(self, *args, **kwargs):
        if not self.cluster_id:
            cluster_count = KubeConfig.objects.count()
            self.cluster_id = f"cluster_id_{cluster_count + 1:02d}"
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.cluster_id}"
    
class Cluster(models.Model):
    cluster_name = models.CharField(max_length=255)
    kube_config = models.ForeignKey(KubeConfig, on_delete=models.CASCADE)

    def __str__(self):
        return self.cluster_name