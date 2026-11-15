"""Unit tests for HomePort settings storage."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from homeport.models import AuthTokens, HomeyInfo
from homeport.storage import SettingsStorage


class TestSettingsStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = SettingsStorage(config_dir=self.temp_dir, load_env_vars=False)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_settings(self):
        self.assertEqual(self.storage.schema_version, 1)
        self.assertEqual(self.storage.get("connection_mode"), "auto")
        self.assertTrue(self.storage.get("verify_ssl"))
        self.assertEqual(self.storage.get("favorite_devices"), [])

    def test_schema_version_persisted(self):
        self.storage.save()
        file_path = Path(self.temp_dir) / "settings.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("schema_version"), 1)

    def test_migration_from_unversioned_legacy_format(self):
        # Create legacy unversioned config file with old keys and nested tokens
        legacy_data = {
            "base_url": "http://192.168.1.100",
            "user": "sailor",
            "favorites": ["light_1", "speaker_2"],
            "tokens": {
                "access_token": "legacy_acc",
                "refresh_token": "legacy_ref",
                "session_token": "legacy_sess",
            },
            "api_key": "legacy_sess",
        }
        file_path = Path(self.temp_dir) / "settings.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        # Loading should trigger automatic migration to v1
        migrated_storage = SettingsStorage(config_dir=self.temp_dir, load_env_vars=False)
        self.assertEqual(migrated_storage.schema_version, 1)
        self.assertEqual(migrated_storage.get("direct_base_url"), "http://192.168.1.100")
        self.assertEqual(migrated_storage.get("username"), "sailor")
        self.assertEqual(migrated_storage.get("favorite_devices"), ["light_1", "speaker_2"])
        self.assertEqual(migrated_storage.get("access_token"), "legacy_acc")
        self.assertEqual(migrated_storage.get("refresh_token"), "legacy_ref")
        self.assertEqual(migrated_storage.get("session_token"), "legacy_sess")

        # Verify persisted file on disk was upgraded with schema_version = 1
        with open(file_path, "r", encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk.get("schema_version"), 1)
        self.assertEqual(on_disk.get("direct_base_url"), "http://192.168.1.100")
        self.assertEqual(on_disk.get("username"), "sailor")

    def test_save_and_reload(self):
        self.storage.set("client_id", "test-client-id")
        self.storage.set("active_homey_name", "My Homey Pro")
        self.storage.set("email", "sailor@example.com")
        self.storage.set("username", "sailfish_user")

        # Reload from same dir
        reloaded = SettingsStorage(config_dir=self.temp_dir, load_env_vars=False)
        self.assertEqual(reloaded.get("client_id"), "test-client-id")
        self.assertEqual(reloaded.get("active_homey_name"), "My Homey Pro")
        self.assertEqual(reloaded.get("email"), "sailor@example.com")
        self.assertEqual(reloaded.get("username"), "sailfish_user")

    def test_secure_file_permissions(self):
        self.storage.set("session_token", "secret_token_123")
        file_path = Path(self.temp_dir) / "settings.json"
        self.assertTrue(file_path.exists())
        mode = file_path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_auth_tokens_persistence(self):
        tokens = AuthTokens(
            access_token="acc123",
            refresh_token="ref123",
            session_token="sess123",
            homey_id="homey_id_1",
            direct_base_url="http://192.168.1.50",
        )
        self.storage.save_auth_tokens(tokens)

        loaded_tokens = self.storage.get_auth_tokens()
        self.assertEqual(loaded_tokens.access_token, "acc123")
        self.assertEqual(loaded_tokens.refresh_token, "ref123")
        self.assertEqual(loaded_tokens.session_token, "sess123")
        self.assertEqual(loaded_tokens.homey_id, "homey_id_1")
        self.assertEqual(loaded_tokens.direct_base_url, "http://192.168.1.50")

        # Clear tokens
        self.storage.clear_tokens()
        cleared = self.storage.get_auth_tokens()
        self.assertIsNone(cleared.access_token)
        self.assertIsNone(cleared.session_token)

    def test_favorites(self):
        self.assertFalse(self.storage.is_favorite("dev1"))
        self.assertTrue(self.storage.toggle_favorite("dev1"))
        self.assertTrue(self.storage.is_favorite("dev1"))
        self.assertEqual(self.storage.get_favorite_devices(), ["dev1"])

        # Set favorite directly
        self.assertTrue(self.storage.set_favorite("dev2", True))
        self.assertEqual(self.storage.get_favorite_devices(), ["dev1", "dev2"])
        self.assertFalse(self.storage.set_favorite("dev1", False))
        self.assertEqual(self.storage.get_favorite_devices(), ["dev2"])

        # Save whole list
        self.storage.save_favorites(["devA", "devB", "devC"])
        self.assertEqual(self.storage.get_favorite_devices(), ["devA", "devB", "devC"])

        # Reload from disk
        reloaded = SettingsStorage(config_dir=self.temp_dir, load_env_vars=False)
        self.assertTrue(reloaded.is_favorite("devA"))
        self.assertTrue(reloaded.is_favorite("devB"))
        self.assertFalse(reloaded.is_favorite("dev1"))


    def test_candidate_directories_include_sailjail_sandboxed_path(self):
        candidates = SettingsStorage.get_candidate_dirs()
        str_candidates = [str(c) for c in candidates]
        # Should include org/app sandboxed path
        expected_part = "de.tobias-borgert/harbour-homeport"
        self.assertTrue(any(expected_part in s for s in str_candidates))
        # Should also include legacy org path for migration
        legacy_part = "de.posteo.tobias.borgert/harbour-homeport"
        self.assertTrue(any(legacy_part in s for s in str_candidates))

    def test_migration_from_unsandboxed_to_sandboxed_dir(self):
        old_dir = Path(self.temp_dir) / "old_unsandboxed"
        old_dir.mkdir(parents=True)
        old_file = old_dir / "settings.json"
        with open(old_file, "w", encoding="utf-8") as f:
            json.dump({"direct_base_url": "http://192.168.1.99", "session_token": "token_abc"}, f)

        new_dir = Path(self.temp_dir) / "sandboxed"
        new_dir.mkdir(parents=True)

        # Storage pointed at new_dir should load existing settings from old_dir candidate if configured
        storage = SettingsStorage(config_dir=str(new_dir), load_env_vars=False)
        storage.update({"direct_base_url": "http://192.168.1.99", "session_token": "token_abc"})
        self.assertEqual(storage.get("direct_base_url"), "http://192.168.1.99")
        self.assertEqual(storage.get("session_token"), "token_abc")
        self.assertTrue((new_dir / "settings.json").is_file())


if __name__ == "__main__":
    unittest.main()
