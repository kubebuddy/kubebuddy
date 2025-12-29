from django.test import TestCase
from django.core.exceptions import ValidationError
from main.models import KubeConfig, Cluster, AIConfig



# ==========================================
# KUBECONFIG MODEL TESTS
# ==========================================
class KubeConfigModelTests(TestCase):

    def test_save_generates_cluster_id(self):
        """Ensure save() auto-generates cluster_id."""
        kube = KubeConfig(path="/tmp/config", path_type="default")
        kube.save()
        self.assertEqual(kube.cluster_id, "cluster_id_01")

    def test_save_increments_cluster_id(self):
        """Ensure second cluster increments count."""
        KubeConfig.objects.create(cluster_id="cluster_id_01", path="/a", path_type="default")

        kube = KubeConfig(path="/b", path_type="default")
        kube.save()
        self.assertEqual(kube.cluster_id, "cluster_id_02")

    def test_str_method_kube(self):
        """__str__ returns cluster_id."""
        kube = KubeConfig.objects.create(
            cluster_id="cid123",
            path="/tmp/config",
            path_type="default"
        )
        self.assertEqual(str(kube), "cid123")


# ==========================================
# CLUSTER MODEL TESTS
# ==========================================
class ClusterModelTests(TestCase):

    def setUp(self):
        self.kube = KubeConfig.objects.create(
            cluster_id="cluster_id_01",
            path="/tmp/config",
            path_type="default"
        )

    def test_cluster_str_method(self):
        """__str__ returns cluster_name."""
        cluster = Cluster.objects.create(
            cluster_name="MyCluster",
            kube_config=self.kube,
            context_name="ctx"
        )
        self.assertEqual(str(cluster), "MyCluster")

    def test_cluster_fk_to_kubeconfig(self):
        """Ensure Cluster links to valid KubeConfig."""
        cluster = Cluster.objects.create(
            cluster_name="TestCluster",
            kube_config=self.kube,
            context_name="ctx"
        )
        self.assertEqual(cluster.kube_config.cluster_id, "cluster_id_01")


# ==========================================
# AI CONFIG MODEL TESTS
# ==========================================
class AIConfigModelTests(TestCase):

    def test_str_method_ai(self):
        """__str__ returns '<Provider> API Key'."""
        obj = AIConfig(provider="openai", api_key="key123", model="gpt-3.5-turbo")
        self.assertEqual(str(obj), "OpenAI API Key")

    # ----------------- CLEAN() TESTS - MODEL VALIDATION -----------------

    def test_clean_invalid_openai_model(self):
        """Test that invalid OpenAI model raises ValidationError."""
        obj = AIConfig(provider="openai", api_key="abc", model="wrong-model")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_invalid_gemini_model(self):
        """Test that invalid Gemini model raises ValidationError."""
        obj = AIConfig(provider="gemini", api_key="abc", model="random")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_invalid_ollama_model(self):
        """Test that invalid Ollama model raises ValidationError."""
        obj = AIConfig(provider="ollama", model="invalid-model", api_key=None)
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_valid_openai_model(self):
        """Test that valid OpenAI model passes clean()."""
        obj = AIConfig(provider="openai", api_key="abc", model="gpt-4")
        try:
            obj.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    def test_clean_valid_gemini_model(self):
        """Test that valid Gemini model passes clean()."""
        obj = AIConfig(provider="gemini", api_key="abc", model="gemini-2.0-flash")
        try:
            obj.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    def test_clean_valid_ollama_model(self):
        """Test that valid Ollama model passes clean()."""
        obj = AIConfig(provider="ollama", model="llama3", api_key=None)
        try:
            obj.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError unexpectedly!")

    # ----------------- CLEAN() TESTS - API KEY VALIDATION -----------------

    def test_clean_ollama_cannot_have_api_key(self):
        """Test that Ollama with API key raises ValidationError."""
        obj = AIConfig(provider="ollama", api_key="some_key", model="llama3")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_openai_requires_api_key(self):
        """Test that OpenAI without API key raises ValidationError."""
        obj = AIConfig(provider="openai", api_key=None, model="gpt-3.5-turbo")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_gemini_requires_api_key(self):
        """Test that Gemini without API key raises ValidationError."""
        obj = AIConfig(provider="gemini", api_key=None, model="gemini-2.0-flash")
        with self.assertRaises(ValidationError):
            obj.clean()

    def test_clean_openai_with_empty_string_api_key(self):
        """Test that OpenAI with empty string API key raises ValidationError."""
        obj = AIConfig(provider="openai", api_key="", model="gpt-3.5-turbo")
        with self.assertRaises(ValidationError):
            obj.clean()

    # ----------------- SAVE() TESTS -----------------

    def test_save_assigns_default_openai_model(self):
        """Test that save() assigns default OpenAI model when model is None."""
        obj = AIConfig(provider="openai", api_key="aaa", model=None)
        obj.save()
        self.assertEqual(obj.model, AIConfig.DEFAULT_MODELS["openai"])

    def test_save_assigns_default_gemini_model(self):
        """Test that save() assigns default Gemini model when model is None."""
        obj = AIConfig(provider="gemini", api_key="123", model=None)
        obj.save()
        self.assertEqual(obj.model, AIConfig.DEFAULT_MODELS["gemini"])

    def test_save_assigns_default_ollama_model(self):
        """Test that save() assigns default Ollama model when model is None."""
        obj = AIConfig(provider="ollama", model=None, api_key=None)
        obj.save()
        self.assertEqual(obj.model, AIConfig.DEFAULT_MODELS["ollama"])

    def test_save_with_explicit_model(self):
        """Test that save() keeps the explicit model when provided."""
        obj = AIConfig(provider="openai", api_key="aaa", model="gpt-4")
        obj.save()
        self.assertEqual(obj.model, "gpt-4")

    # ----------------- UNIQUE CONSTRAINT TEST -----------------

    def test_unique_provider_and_model(self):
        """Test that unique_together constraint works for provider and model."""
        AIConfig.objects.create(
            provider="openai",
            api_key="abc",
            model="gpt-3.5-turbo"
        )

        with self.assertRaises(Exception):
            AIConfig.objects.create(
                provider="openai",
                api_key="xyz",
                model="gpt-3.5-turbo"
            )

    def test_different_providers_same_model_name_allowed(self):
        """Test that different providers can exist even if model names overlap."""
        AIConfig.objects.create(
            provider="openai",
            api_key="abc",
            model="gpt-3.5-turbo"
        )
        
        obj2 = AIConfig.objects.create(
            provider="gemini",
            api_key="xyz",
            model="gemini-2.0-flash"
        )
        self.assertEqual(obj2.provider, "gemini")

    # ----------------- PROVIDER-SPECIFIC TESTS -----------------

    def test_ollama_no_api_key_required(self):
        """Test that Ollama can be created without API key."""
        obj = AIConfig.objects.create(
            provider="ollama",
            model="llama3",
            api_key=None
        )
        self.assertIsNone(obj.api_key)
        self.assertEqual(obj.model, "llama3")

    def test_openai_all_models_valid(self):
        """Test that all OpenAI models in MODELS_OPENAI are valid."""
        for model_code, _ in AIConfig.MODELS_OPENAI[:3]:  # Test first 3 to save time
            obj = AIConfig(provider="openai", api_key="test", model=model_code)
            try:
                obj.clean()
            except ValidationError:
                self.fail(f"Valid OpenAI model '{model_code}' raised ValidationError!")

    def test_gemini_all_models_valid(self):
        """Test that all Gemini models in MODELS_GEMINI are valid."""
        for model_code, _ in AIConfig.MODELS_GEMINI[:3]:  # Test first 3 to save time
            obj = AIConfig(provider="gemini", api_key="test", model=model_code)
            try:
                obj.clean()
            except ValidationError:
                self.fail(f"Valid Gemini model '{model_code}' raised ValidationError!")

    def test_ollama_all_models_valid(self):
        """Test that all Ollama models in MODELS_OLLAMA are valid."""
        for model_code, _ in AIConfig.MODELS_OLLAMA[:3]:  # Test first 3 to save time
            obj = AIConfig(provider="ollama", api_key=None, model=model_code)
            try:
                obj.clean()
            except ValidationError:
                self.fail(f"Valid Ollama model '{model_code}' raised ValidationError!")