"""Unit tests for environment variable and .env file loading."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from homeport.storage import SettingsStorage, load_env


class TestEnvLoading(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.saved_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.saved_env)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_env_file_parsing(self):
        env_content = """
# This is a comment
HOMEY_BASE_URL=http://192.168.1.88
HOMEY_SESSION_TOKEN="my-secret-session-token"
HOMEY_CLIENT_ID='test-client-id-single-quotes'
export HOMEY_USERNAME=homey_admin
HOMEY_VERIFY_SSL=false
"""
        env_path = Path(self.temp_dir) / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)

        # Clear target env vars from os.environ
        for k in ["HOMEY_BASE_URL", "HOMEY_SESSION_TOKEN", "HOMEY_CLIENT_ID", "HOMEY_USERNAME", "HOMEY_VERIFY_SSL"]:
            os.environ.pop(k, None)

        loaded = load_env(dotenv_path=env_path)
        self.assertEqual(loaded["HOMEY_BASE_URL"], "http://192.168.1.88")
        self.assertEqual(loaded["HOMEY_SESSION_TOKEN"], "my-secret-session-token")
        self.assertEqual(loaded["HOMEY_CLIENT_ID"], "test-client-id-single-quotes")
        self.assertEqual(loaded["HOMEY_USERNAME"], "homey_admin")
        self.assertEqual(loaded["HOMEY_VERIFY_SSL"], "false")

        # Verify os.environ was populated
        self.assertEqual(os.environ["HOMEY_BASE_URL"], "http://192.168.1.88")
        self.assertEqual(os.environ["HOMEY_SESSION_TOKEN"], "my-secret-session-token")
        self.assertEqual(os.environ["HOMEY_USERNAME"], "homey_admin")

    def test_load_env_non_overriding_default(self):
        os.environ["HOMEY_BASE_URL"] = "http://existing-url.com"
        env_path = Path(self.temp_dir) / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("HOMEY_BASE_URL=http://new-url.com\n")

        load_env(dotenv_path=env_path, override=False)
        self.assertEqual(os.environ["HOMEY_BASE_URL"], "http://existing-url.com")

        # With override=True
        load_env(dotenv_path=env_path, override=True)
        self.assertEqual(os.environ["HOMEY_BASE_URL"], "http://new-url.com")

    def test_settings_storage_loads_from_env(self):
        os.environ["HOMEY_BASE_URL"] = "http://10.0.0.5:80"
        os.environ["HOMEY_SESSION_TOKEN"] = "env_session_token_xyz"
        os.environ["HOMEY_CLIENT_ID"] = "env_client_id_123"
        os.environ["HOMEY_EMAIL"] = "env_user@example.com"
        os.environ["HOMEY_VERIFY_SSL"] = "false"

        storage = SettingsStorage(config_dir=self.temp_dir, load_env_vars=True)
        self.assertEqual(storage.get("direct_base_url"), "http://10.0.0.5:80")
        self.assertEqual(storage.get("session_token"), "env_session_token_xyz")
        self.assertEqual(storage.get("client_id"), "env_client_id_123")
        self.assertEqual(storage.get("email"), "env_user@example.com")
        self.assertFalse(storage.get("verify_ssl"))


if __name__ == "__main__":
    unittest.main()
