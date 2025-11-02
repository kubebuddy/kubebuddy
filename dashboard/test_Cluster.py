from django.http import Http404, HttpResponseNotModified
from django.test import TestCase, RequestFactory
from django.views import static as static_views
from unittest import mock
from pathlib import Path

import os

class StaticViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        from tempfile import TemporaryDirectory
        self.temp_dir = TemporaryDirectory()
        self.temp_dir_path = self.temp_dir.name
        with open(os.path.join(self.temp_dir_path, "test.txt"), "w") as f:
            f.write("hello world")
        os.mkdir(os.path.join(self.temp_dir_path, "subdir"))
        with open(os.path.join(self.temp_dir_path, "subdir", "file2.txt"), "w") as f:
            f.write("subdir file")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_serve_file_success(self):
        request = self.factory.get("/static/test.txt")
        response = static_views.serve(request, "test.txt", document_root=self.temp_dir_path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"hello world")
        self.assertIn("Last-Modified", response.headers)
        # Explicitly close the file wrapper if present to release the file lock on Windows
        file_to_close = getattr(response, 'file_to_stream', None)
        if file_to_close and hasattr(file_to_close, 'close'):
            file_to_close.close()

    def test_serve_file_not_found(self):
        request = self.factory.get("/static/missing.txt")
        with self.assertRaises(Http404):
            static_views.serve(request, "missing.txt", document_root=self.temp_dir_path)

    def test_serve_directory_index_enabled(self):
        request = self.factory.get("/static/")
        response = static_views.serve(request, "", document_root=self.temp_dir_path, show_indexes=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("test.txt", content)
        self.assertIn("subdir/", content)

    def test_serve_directory_index_disabled(self):
        request = self.factory.get("/static/")
        with self.assertRaises(Http404):
            static_views.serve(request, "", document_root=self.temp_dir_path, show_indexes=False)

    def test_serve_file_if_modified_since(self):
        file_path = os.path.join(self.temp_dir_path, "test.txt")
        mtime = int(os.stat(file_path).st_mtime)
        request = self.factory.get("/static/test.txt", HTTP_IF_MODIFIED_SINCE=static_views.http_date(mtime))
        response = static_views.serve(request, "test.txt", document_root=self.temp_dir_path)
        self.assertIsInstance(response, HttpResponseNotModified)

    def test_builtin_template_path_exists(self):
        path = static_views.builtin_template_path("directory_index.html")
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "directory_index.html")

    def test_directory_index_template_fallback(self):
        with mock.patch("django.template.loader.select_template", side_effect=static_views.TemplateDoesNotExist("x")):
            files = ["a.txt", "b.txt"]
            for fname in files:
                with open(os.path.join(self.temp_dir_path, fname), "w") as f:
                    f.write("data")
            response = static_views.directory_index("test", Path(self.temp_dir_path))
            content = response.content.decode()
            self.assertIn("a.txt", content)
            self.assertIn("b.txt", content)
            self.assertTrue(static_views.builtin_template_path("directory_index.html").exists())

    def test_was_modified_since_true_for_none(self):
        self.assertTrue(static_views.was_modified_since(None, 123456))

    def test_was_modified_since_false_for_unmodified(self):
        header = static_views.http_date(200000)
        self.assertFalse(static_views.was_modified_since(header, 100000))

    def test_was_modified_since_true_for_modified(self):
        header = static_views.http_date(100000)
        self.assertTrue(static_views.was_modified_since(header, 200000))
