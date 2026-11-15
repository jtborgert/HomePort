"""Integration tests for connecting against a real live Homey backend using .env credentials."""

import os
import unittest

from homeport.api import HomeyClient
from homeport.storage import load_env

# Automatically load .env if present in workspace root
load_env()

LIVE_BASE_URL = os.environ.get("HOMEY_BASE_URL")
LIVE_SESSION_TOKEN = os.environ.get("HOMEY_SESSION_TOKEN") or os.environ.get("HOMEY_API_KEY")
LIVE_VERIFY_SSL = os.environ.get("HOMEY_VERIFY_SSL", "true").lower() not in ("0", "false", "no")


class TestLiveBackend(unittest.TestCase):

    def setUp(self):
        if not LIVE_BASE_URL or not LIVE_SESSION_TOKEN:
            self.skipTest("Live backend credentials not configured in .env (HOMEY_BASE_URL & HOMEY_SESSION_TOKEN required)")
        self.client = HomeyClient(
            base_url=LIVE_BASE_URL,
            session_token=LIVE_SESSION_TOKEN,
            verify_ssl=LIVE_VERIFY_SSL,
        )

    def test_live_system_info(self):
        """Verifies connection and system info retrieval from real Homey backend."""
        info = self.client.get_system_info()
        self.assertIsInstance(info, dict)
        self.assertTrue("name" in info or "version" in info or "language" in info or "platform" in info)

    def test_live_get_devices(self):
        """Fetches devices from real Homey backend."""
        devices = self.client.get_devices()
        self.assertIsInstance(devices, dict)
        # Verify structure of loaded devices if any exist
        for dev_id, dev in devices.items():
            self.assertEqual(dev_id, dev.id)
            self.assertIsNotNone(dev.name)
            self.assertIsInstance(dev.capabilities, list)

    def test_live_get_zones(self):
        """Fetches zones from real Homey backend."""
        zones = self.client.get_zones()
        self.assertIsInstance(zones, dict)
        for zone_id, zone in zones.items():
            self.assertEqual(zone_id, zone.id)
            self.assertIsNotNone(zone.name)

    def test_live_get_flows(self):
        """Fetches flows from real Homey backend."""
        flows = self.client.get_flows()
        self.assertIsInstance(flows, dict)
        for flow_id, flow in flows.items():
            self.assertEqual(flow_id, flow.id)
            self.assertIsNotNone(flow.name)


if __name__ == "__main__":
    unittest.main()
