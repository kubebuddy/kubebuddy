from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.contrib.auth.models import User


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
    context_name = models.CharField(max_length=255)

    def __str__(self):
        return self.cluster_name


class AIConfig(models.Model):
    PROVIDERS = [
        ('openai', 'OpenAI'),
        ('gemini', 'Google Gemini'),
        ('ollama', 'Ollama'),
    ]
    DEFAULT_MODELS = {
        'openai': 'gpt-3.5-turbo',
        'gemini': 'gemini-2.5-flash',
        'ollama': 'llama3',
    }
    MODELS_OPENAI = [
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('gpt-3.5-turbo-16k', 'GPT-3.5 Turbo 16K'),
        ('gpt-3.5-turbo-instruct', 'GPT-3.5 Turbo Instruct'),
        ('gpt-4', 'GPT-4'),
        ('gpt-4-32k', 'GPT-4 32K'),
        ('gpt-4o', 'GPT-4o'),
        ('gpt-4o-mini', 'GPT-4o Mini'),
        ('gpt-4.1', 'GPT-4.1'),
        ('gpt-4.1-mini', 'GPT-4.1 Mini')
    ]

    MODELS_GEMINI = [
        ('gemini-3.1-pro-preview', 'Gemini 3.1 Pro (Preview)'),
        ('gemini-3-flash-preview', 'Gemini 3 Flash (Preview)'),
        ('gemini-3.1-flash-lite', 'Gemini 3.1 Flash-Lite'),
        ('gemini-2.5-pro', 'Gemini 2.5 Pro'),
        ('gemini-2.5-flash', 'Gemini 2.5 Flash'),
        ('gemini-2.5-flash-lite', 'Gemini 2.5 Flash-Lite'),
    ]

    MODELS_OLLAMA = [
        ('gemma3:1b', 'Gemma'),
        ('llama2', 'LLaMA 2'),
        ('llama3', 'LLaMA 3'),
        ('mistral', 'Mistral'),
        ('codellama', 'Code LLaMA'),
        ('phi3', 'Phi-3 Mini'),
        ('llama3.1', 'LLaMA 3.1'),
        ('mistral-small', 'Mistral Small'),
        ('gemma:2b', 'Gemma 2B'),
        ('gemma:7b', 'Gemma 7B'),
        ('gemma2:2b', 'Gemma 2 (2B)'),
        ('gemma2:9b', 'Gemma 2 (9B)')
    ]

    provider = models.CharField(max_length=10, choices=PROVIDERS, unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_provider_display()} API Key"

    def clean(self):
        if self.provider == 'openai' and self.model and self.model not in [c[0] for c in self.MODELS_OPENAI]:
            raise ValidationError(f"Invalid model '{self.model}' for OpenAI.")
        elif self.provider == 'gemini' and self.model and self.model not in [c[0] for c in self.MODELS_GEMINI]:
            raise ValidationError(f"Invalid model '{self.model}' for Gemini.")
        elif self.provider == 'ollama' and self.model and self.model not in [c[0] for c in self.MODELS_OLLAMA]:
            raise ValidationError(f"Invalid model '{self.model}' for Ollama.")
        if self.provider == 'ollama' and self.api_key:
            raise ValidationError("Ollama does not require an API key.")
        if self.provider in ['openai', 'gemini'] and not self.api_key:
            raise ValidationError(f"{self.get_provider_display()} requires an API key.")

    def save(self, *args, **kwargs):
        if not self.model:
            self.model = self.DEFAULT_MODELS.get(self.provider)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('provider', 'model')


class SmtpConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='smtp_config')
    smtp_server = models.CharField(max_length=255)
    smtp_port = models.CharField(max_length=10)
    smtp_from_email = models.EmailField()
    smtp_username = models.CharField(max_length=255)
    smtp_password = models.CharField(max_length=255)
    smtp_use_tls = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SMTP Config for {self.user.username} ({self.smtp_server})"

    class Meta:
        verbose_name = "SMTP Configuration"
        verbose_name_plural = "SMTP Configurations"


class SsoConfig(models.Model):
    PROVIDERS = [
        ('google', 'Google'),
        ('outlook', 'Microsoft Outlook'),
        ('github', 'GitHub'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sso_configs')
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    client_id = models.CharField(max_length=500)
    client_secret = models.CharField(max_length=500)
    redirect_uri = models.CharField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "SSO Configuration"
        verbose_name_plural = "SSO Configurations"
        unique_together = ('user', 'provider')

    def __str__(self):
        return f"{self.get_provider_display()} SSO for {self.user.username}"

    def get_masked_client_secret(self):
        if len(self.client_secret) > 8:
            return f"{self.client_secret[:4]}...{self.client_secret[-4:]}"
        return "********"


# ═══════════════════════════════════════════════════════
# RBAC — UserProfile with role field + permission flags
# ═══════════════════════════════════════════════════════

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user',  'User'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    # Permission flags
    can_workloads           = models.BooleanField(default=True,  help_text="Pods, Deployments, ReplicaSets, etc.")
    can_cluster_management  = models.BooleanField(default=False, help_text="Nodes, Namespaces, PDB, etc.")
    can_services            = models.BooleanField(default=False, help_text="Services, Endpoints")
    can_storage             = models.BooleanField(default=False, help_text="PV, PVC, StorageClass")
    can_ingress             = models.BooleanField(default=False, help_text="Ingress, Network Policies")
    can_configmaps          = models.BooleanField(default=False, help_text="ConfigMaps & Secrets")
    can_metrics             = models.BooleanField(default=False, help_text="Pod Metrics, Node Metrics")
    can_events              = models.BooleanField(default=False, help_text="All Events")
    can_rbac                = models.BooleanField(default=False, help_text="Roles, RoleBindings, ClusterRoles, etc.")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username}, role={self.role})"

    def is_admin_role(self):
        return self.role == 'admin' or self.user.is_superuser

    def get_permissions_list(self):
        if self.is_admin_role():
            return ['Workloads', 'Cluster Management', 'Services', 'Storage', 'Ingress', 'ConfigMaps', 'Metrics', 'Events', 'RBAC']
        perms = []
        if self.can_workloads:          perms.append('Workloads')
        if self.can_cluster_management: perms.append('Cluster Management')
        if self.can_services:           perms.append('Services')
        if self.can_storage:            perms.append('Storage')
        if self.can_ingress:            perms.append('Ingress')
        if self.can_configmaps:         perms.append('ConfigMaps')
        if self.can_metrics:            perms.append('Metrics')
        if self.can_events:             perms.append('Events')
        if self.can_rbac:               perms.append('RBAC')
        return perms

    def get_permissions_display(self):
        return ', '.join(self.get_permissions_list()) or 'No permissions'

    @classmethod
    def get_or_create_for_user(cls, user):
        profile, created = cls.objects.get_or_create(user=user)
        if created:
            if user.is_superuser:
                profile.role                   = 'admin'
                profile.can_workloads          = True
                profile.can_cluster_management = True
                profile.can_services           = True
                profile.can_storage            = True
                profile.can_ingress            = True
                profile.can_configmaps         = True
                profile.can_metrics            = True
                profile.can_events             = True
                profile.can_rbac               = True
            else:
                profile.role          = 'user'
                profile.can_workloads = True
            profile.save()
        return profile