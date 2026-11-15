"""Unit tests for HomePort data models."""

import unittest
from homeport.models import AuthTokens, HomeyCapability, HomeyDevice, HomeyFlow, HomeyInfo, HomeyZone


class TestHomeyModels(unittest.TestCase):

    def test_capability_parsing(self):
        cap_dict = {
            "value": True,
            "type": "boolean",
            "title": "Turn on/off",
            "getable": True,
            "setable": True,
        }
        cap = HomeyCapability.from_dict("onoff", cap_dict)
        self.assertEqual(cap.id, "onoff")
        self.assertEqual(cap.value, True)
        self.assertTrue(cap.setable)

        # To dict
        d = cap.to_dict()
        self.assertEqual(d["id"], "onoff")
        self.assertEqual(d["value"], True)

    def test_device_parsing(self):
        dev_data = {
            "id": "dev-123",
            "name": "Living Room Light",
            "class": "light",
            "zone": "zone-living",
            "capabilities": ["onoff", "dim"],
            "capabilitiesObj": {
                "onoff": {"value": True, "type": "boolean", "title": "On / Off"},
                "dim": {"value": 0.75, "type": "number", "min": 0, "max": 1, "step": 0.01},
            },
        }
        zones_map = {"zone-living": "Living Room"}
        dev = HomeyDevice.from_dict(dev_data, zones_map=zones_map)

        self.assertEqual(dev.id, "dev-123")
        self.assertEqual(dev.name, "Living Room Light")
        self.assertEqual(dev.class_name, "light")
        self.assertEqual(dev.zone_name, "Living Room")
        self.assertTrue(dev.onoff)
        self.assertEqual(dev.dim, 0.75)

        # Verify to_dict
        d = dev.to_dict()
        self.assertEqual(d["id"], "dev-123")
        self.assertEqual(d["onoff"], True)
        self.assertEqual(d["dim"], 0.75)
        self.assertFalse(d["isFavorite"])
        self.assertIn("capabilitiesObj", d)

        # Device with favorite flag
        dev_fav = HomeyDevice.from_dict({
            "id": "dev-456",
            "name": "Favorite Plug",
            "favorite": True,
        })
        self.assertTrue(dev_fav.is_favorite)
        self.assertTrue(dev_fav.to_dict()["isFavorite"])

    def test_zone_parsing(self):
        zone_data = {
            "id": "zone-1",
            "name": "Kitchen",
            "parent": "zone-ground-floor",
            "order": 2,
        }
        zone = HomeyZone.from_dict(zone_data)
        self.assertEqual(zone.id, "zone-1")
        self.assertEqual(zone.name, "Kitchen")
        self.assertEqual(zone.parent_id, "zone-ground-floor")
        self.assertEqual(zone.order, 2)

    def test_flow_parsing(self):
        flow_data = {
            "id": "flow-abc",
            "name": "Good Night",
            "folder": "folder-1",
            "enabled": True,
            "triggerable": True,
        }
        flow = HomeyFlow.from_dict(flow_data)
        self.assertEqual(flow.id, "flow-abc")
        self.assertEqual(flow.name, "Good Night")
        self.assertTrue(flow.enabled)
        self.assertTrue(flow.triggerable)

    def test_homey_info_url_preference(self):
        info = HomeyInfo(
            id="homey-xyz",
            name="My Homey Pro",
            local_url="http://192.168.1.50",
            local_url_secure="https://192-168-1-50.homey.homeylocal.com",
            remote_url="https://homey-xyz.homey.eu-west-1.homeypro.net",
        )
        self.assertEqual(info.get_preferred_url("auto"), "https://192-168-1-50.homey.homeylocal.com")
        self.assertEqual(info.get_preferred_url("local"), "http://192.168.1.50")
        self.assertEqual(info.get_preferred_url("remote"), "https://homey-xyz.homey.eu-west-1.homeypro.net")

        # Fallback when local_url_secure is missing
        info2 = HomeyInfo(id="h2", name="H2", local_url="http://192.168.1.60")
        self.assertEqual(info2.get_preferred_url("auto"), "http://192.168.1.60")

    def test_auth_tokens(self):
        tokens = AuthTokens(
            access_token="acc123",
            refresh_token="ref123",
            session_token="sess123",
            homey_id="homey1",
        )
        d = tokens.to_dict()
        self.assertEqual(d["access_token"], "acc123")
        self.assertEqual(d["session_token"], "sess123")

        reconstructed = AuthTokens.from_dict(d)
        self.assertEqual(reconstructed.access_token, "acc123")
        self.assertEqual(reconstructed.refresh_token, "ref123")


if __name__ == "__main__":
    unittest.main()
