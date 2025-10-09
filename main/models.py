from django.db import models
from django.core.exceptions import ValidationError
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
        'gemini': 'gemini-2.0-flash',
        'ollama': 'llama3',  
    }

    MODELS_OPENAI = [
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
        ('gpt-3.5-turbo-16k', 'GPT-3.5 Turbo 16K'),
        ('gpt-3.5-turbo-instruct', 'GPT-3.5 Turbo Instruct'),
        ('gpt-4', 'GPT-4'),
        ('gpt-4-32k', 'GPT-4 32K'),
    ]

    MODELS_GEMINI = [
        ('gemini-2.0-flash', 'Gemini 2.0 Flash'),
        ('gemini-2.0-flash-lite', 'Gemini 2.0 Flash-Lite'),
        ('gemini-1.5-flash', 'Gemini 1.5 Flash'),
        ('gemini-1.5-flash-8b', 'Gemini 1.5 Flash-8B'),
        ('gemini-1.5-pro', 'Gemini 1.5 Pro'),
    ]

    MODELS_OLLAMA = [
        ('gemma3:1b','Gemma'),
        ('llama2', 'LLaMA 2'),
        ('llama3', 'LLaMA 3'),
        ('mistral', 'Mistral'),
        ('codellama', 'Code LLaMA'),
        ('phi3', 'Phi-3 Mini')
    ]

    provider = models.CharField(max_length=10, choices=PROVIDERS, unique=True)
    api_key = models.CharField(max_length=255, blank=True, null=True,
        help_text="Required only for OpenAI and Gemini. Leave empty for Ollama."
    )
    model = models.CharField(max_length=50, blank=True, null=True,
        help_text="Specific model to use for the provider (optional, defaults will be used if not specified)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_provider_display()} Config"

    def clean(self):
        if self.provider == 'openai' and self.model and self.model not in [choice[0] for choice in self.MODELS_OPENAI]:
            raise ValidationError(f"Invalid model '{self.model}' for OpenAI. Choose from: {', '.join([choice[0] for choice in self.MODELS_OPENAI])}.")
        elif self.provider == 'gemini' and self.model and self.model not in [choice[0] for choice in self.MODELS_GEMINI]:
            raise ValidationError(f"Invalid model '{self.model}' for Gemini. Choose from: {', '.join([choice[0] for choice in self.MODELS_GEMINI])}.")
        elif self.provider == 'ollama' and self.model and self.model not in [choice[0] for choice in self.MODELS_OLLAMA]:
            raise ValidationError(f"Invalid model '{self.model}' for Ollama. Choose from: {', '.join([choice[0] for choice in self.MODELS_OLLAMA])}.")

        # Ollama doesn’t need API key
        if self.provider == 'ollama' and self.api_key:
            raise ValidationError("Ollama does not require an API key. Leave it blank.")

        # OpenAI/Gemini must have API key
        if self.provider in ['openai', 'gemini'] and not self.api_key:
            raise ValidationError(f"{self.get_provider_display()} requires an API key.")

    def save(self, *args, **kwargs):
        if not self.model:
            self.model = self.DEFAULT_MODELS.get(self.provider)
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('provider', 'model')


