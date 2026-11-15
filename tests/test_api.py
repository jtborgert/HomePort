"""Unit tests for Homey HTTP API client."""

import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from homeport.api import HomeyAuthError, HomeyClient, HomeyConnectionError
from homeport.models import HomeyInfo


class MockHttpResponse:
    def __init__(self, data, status=200, content_type="application/json"):
        self.data = data
        self.status = status
        self.headers = {"Content-Type": content_type}

    def read(self):
        if isinstance(self.data, (dict, list, bool)):
            return json.dumps(self.data).encode("utf-8")
        elif isinstance(self.data, str):
            return self.data.encode("utf-8")
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestHomeyClient(unittest.TestCase):

    def setUp(self):
        self.client = HomeyClient(base_url="http://192.168.1.100", session_token="test-session-tok")

    def test_oauth_url_generation(self):
        url = self.client.get_oauth_url(
            client_id="my-client-id",
            redirect_uri="https://example.com/callback",
            state="test-state",
        )
        self.assertIn("https://api.athom.com/oauth2/authorise", url)
        self.assertIn("client_id=my-client-id", url)
        self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fcallback", url)
        self.assertIn("state=test-state", url)

    @patch("urllib.request.urlopen")
    def test_exchange_authorization_code(self, mock_urlopen):
        mock_resp = {
            "token_type": "bearer",
            "access_token": "acc_xyz",
            "refresh_token": "ref_xyz",
            "expires_in": 3600,
        }
        mock_urlopen.return_value = MockHttpResponse(mock_resp)

        tokens = self.client.exchange_authorization_code(
            client_id="cid",
            client_secret="csec",
            code="auth_code_123",
        )
        self.assertEqual(tokens.access_token, "acc_xyz")
        self.assertEqual(tokens.refresh_token, "ref_xyz")
        self.assertEqual(self.client.auth_tokens.access_token, "acc_xyz")

    @patch("urllib.request.urlopen")
    def test_get_user_info_and_homeys(self, mock_urlopen):
        mock_resp = {
            "_id": "user123",
            "firstname": "John",
            "homeys": [
                {
                    "_id": "homey_pro_1",
                    "name": "Living Room Homey",
                    "platform": "local",
                    "localUrl": "http://192.168.1.50",
                    "localUrlSecure": "https://192-168-1-50.homey.homeylocal.com",
                    "remoteUrl": "https://homey-1.homeypro.net",
                }
            ],
        }
        mock_urlopen.return_value = MockHttpResponse(mock_resp)

        user_data, homeys = self.client.get_user_info(access_token="acc_test")
        self.assertEqual(len(homeys), 1)
        self.assertEqual(homeys[0].name, "Living Room Homey")
        self.assertEqual(homeys[0].id, "homey_pro_1")
        self.assertEqual(homeys[0].local_url_secure, "https://192-168-1-50.homey.homeylocal.com")

    @patch("urllib.request.urlopen")
    def test_get_delegation_token(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse('"delegation_jwt_token_123"')

        token = self.client.get_delegation_token(access_token="acc_test")
        self.assertEqual(token, "delegation_jwt_token_123")

    @patch("urllib.request.urlopen")
    def test_create_homey_session(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse('"homey_session_token_abc"')

        session_token = self.client.create_homey_session(
            homey_url="http://192.168.1.50",
            delegation_token="del_token_123",
        )
        self.assertEqual(session_token, "homey_session_token_abc")
        self.assertEqual(self.client.base_url, "http://192.168.1.50")
        self.assertEqual(self.client.session_token, "homey_session_token_abc")

    @patch("urllib.request.urlopen")
    def test_get_devices(self, mock_urlopen):
        mock_devices_data = {
            "dev_light_1": {
                "id": "dev_light_1",
                "name": "Ceiling Light",
                "class": "light",
                "zone": "zone_1",
                "capabilities": ["onoff", "dim"],
                "capabilitiesObj": {
                    "onoff": {"value": True, "type": "boolean"},
                    "dim": {"value": 0.8, "type": "number"},
                },
            }
        }
        mock_urlopen.return_value = MockHttpResponse(mock_devices_data)

        devices = self.client.get_devices(zones_map={"zone_1": "Bedroom"})
        self.assertIn("dev_light_1", devices)
        dev = devices["dev_light_1"]
        self.assertEqual(dev.name, "Ceiling Light")
        self.assertEqual(dev.zone_name, "Bedroom")
        self.assertTrue(dev.onoff)
        self.assertEqual(dev.dim, 0.8)

    @patch("urllib.request.urlopen")
    def test_set_capability(self, mock_urlopen):
        mock_urlopen.return_value = MockHttpResponse(True)

        res = self.client.set_device_capability("dev_light_1", "onoff", False)
        self.assertTrue(res)

        # Verify request parameters
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.method, "PUT")
        self.assertEqual(req.full_url, "http://192.168.1.100/api/manager/devices/device/dev_light_1/capability/onoff")
        self.assertEqual(req.data, b'{"value": false}')

    @patch("urllib.request.urlopen")
    def test_get_flows_and_trigger(self, mock_urlopen):
        mock_flows_data = {
            "flow_1": {
                "id": "flow_1",
                "name": "Turn off all lights",
                "enabled": True,
                "triggerable": True,
            }
        }
        mock_urlopen.return_value = MockHttpResponse(mock_flows_data)

        flows = self.client.get_flows()
        self.assertIn("flow_1", flows)
        self.assertEqual(flows["flow_1"].name, "Turn off all lights")

        # Trigger
        mock_urlopen.return_value = MockHttpResponse(True)
        trig_res = self.client.trigger_flow("flow_1")
        self.assertTrue(trig_res)


if __name__ == "__main__":
    unittest.main()
