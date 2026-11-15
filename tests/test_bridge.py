"""Unit tests for PyOtherSide bridge interface."""

import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from homeport.bridge import HomePortBridge
from homeport.models import AuthTokens, HomeyDevice, HomeyInfo
from homeport.storage import SettingsStorage


class TestBridge(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = SettingsStorage(config_dir=self.temp_dir, load_env_vars=False)
        self.bridge = HomePortBridge(storage=self.storage)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_bridge_empty(self):
        state = self.bridge.init_bridge()
        self.assertFalse(state["isConfigured"])
        self.assertFalse(state["hasDirectUrl"])

    def test_init_bridge_configured(self):
        self.storage.set("direct_base_url", "http://192.168.1.50")
        self.storage.set("session_token", "test_token")
        self.storage.set("active_homey_name", "Homey Pro Test")
        self.storage.set("email", "test@sailfish.org")
        self.storage.set("username", "testuser")
        self.storage.set("client_id", "my_client_id")
        self.storage.set("client_secret", "my_secret")

        state = self.bridge.init_bridge()
        self.assertTrue(state["isConfigured"])
        self.assertTrue(state["hasDirectUrl"])
        self.assertEqual(state["activeHomeyName"], "Homey Pro Test")
        self.assertEqual(state["email"], "test@sailfish.org")
        self.assertEqual(state["username"], "testuser")
        self.assertEqual(state["clientId"], "my_client_id")
        self.assertEqual(state["clientSecret"], "my_secret")
        self.assertEqual(state["sessionToken"], "test_token")

    def test_save_and_get_settings(self):
        self.bridge.save_settings({
            "email": "saved@sailfish.org",
            "username": "jolla_user",
            "client_id": "c123",
            "session_token": "s123",
            "direct_base_url": "192.168.1.100",
        })
        settings = self.bridge.get_settings()
        self.assertEqual(settings["email"], "saved@sailfish.org")
        self.assertEqual(settings["username"], "jolla_user")
        self.assertEqual(settings["client_id"], "c123")
        self.assertEqual(settings["session_token"], "s123")
        self.assertEqual(settings["direct_base_url"], "http://192.168.1.100")

    def test_init_bridge_with_saved_direct_url_and_token(self):
        self.bridge.save_settings({
            "direct_base_url": "192.168.1.50:80",
            "session_token": "my_api_token",
        })
        state = self.bridge.init_bridge()
        self.assertTrue(state["isConfigured"])
        self.assertTrue(state["hasDirectUrl"])
        self.assertEqual(state["directBaseUrl"], "http://192.168.1.50:80")
        self.assertEqual(state["sessionToken"], "my_api_token")

    def test_toggle_favorite(self):
        self.assertTrue(self.bridge.toggle_favorite("dev123"))
        self.assertTrue(self.storage.is_favorite("dev123"))
        self.assertFalse(self.bridge.toggle_favorite("dev123"))
        self.assertFalse(self.storage.is_favorite("dev123"))

    def test_set_and_get_favorites(self):
        self.assertTrue(self.bridge.set_favorite("dev-A", True))
        self.assertTrue(self.bridge.set_favorite("dev-B", True))
        self.assertEqual(self.bridge.get_favorites(), ["dev-A", "dev-B"])

        self.assertFalse(self.bridge.set_favorite("dev-A", False))
        self.assertEqual(self.bridge.get_favorites(), ["dev-B"])

    def test_devices_cache_and_get_device(self):
        mock_dev = HomeyDevice(
            id="dev-speaker-1",
            name="Living Room Sonos",
            class_name="speaker",
            capabilities=["volume_set", "volume_mute", "speaker_playing"],
        )
        self.bridge._devices_cache["dev-speaker-1"] = mock_dev
        self.bridge.set_favorite("dev-speaker-1", True)

        dev_dict = self.bridge.get_device("dev-speaker-1")
        self.assertIsNotNone(dev_dict)
        self.assertEqual(dev_dict["name"], "Living Room Sonos")
        self.assertEqual(dev_dict["class"], "speaker")
        self.assertEqual(dev_dict["capabilities"], ["volume_set", "volume_mute", "speaker_playing"])
        self.assertTrue(dev_dict["isFavorite"])

    def test_logout(self):
        self.storage.set("session_token", "test_tok")
        self.bridge.logout()
        self.assertIsNone(self.storage.get_auth_tokens().session_token)


if __name__ == "__main__":
    unittest.main()
