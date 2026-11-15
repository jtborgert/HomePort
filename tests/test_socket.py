"""Unit tests for Homey Socket.IO client packet framing and event handling."""

import json
import unittest
from unittest.mock import MagicMock, patch

from homeport.socket import HomeyRealtimeClient


class TestHomeySocketClient(unittest.TestCase):

    def setUp(self):
        self.received_events = []

        def on_event(uri, event_type, data):
            self.received_events.append((uri, event_type, data))

        self.client = HomeyRealtimeClient(
            base_url="http://192.168.1.50",
            session_token="test_sess_token",
            homey_id="homey_123",
            on_event=on_event,
        )

    def test_handle_socketio_device_event(self):
        # Socket.IO event format: 42["homey:device:dev_1", "capability", {"capabilityId": "onoff", "value": true}]
        raw_msg = '["homey:device:dev_1", "capability", {"capabilityId": "onoff", "value": true}]'
        self.client._handle_socketio_message("2" + raw_msg)

        self.assertEqual(len(self.received_events), 1)
        uri, ev_type, data = self.received_events[0]
        self.assertEqual(uri, "homey:device:dev_1")
        self.assertEqual(ev_type, "capability")
        self.assertEqual(data["capabilityId"], "onoff")
        self.assertEqual(data["value"], True)

    def test_handle_socketio_flow_event(self):
        # Socket.IO event format: 42["homey:manager:flow", "create", {"id": "flow_123"}]
        raw_msg = '["homey:manager:flow", "create", {"id": "flow_123"}]'
        self.client._handle_socketio_message("2" + raw_msg)

        self.assertEqual(len(self.received_events), 1)
        uri, ev_type, data = self.received_events[0]
        self.assertEqual(uri, "homey:manager:flow")
        self.assertEqual(ev_type, "create")
        self.assertEqual(data["id"], "flow_123")

    def test_handshake_client_ack_callback(self):
        # Simulate handshake ack response: 431[null, {"namespace": "/api"}]
        self.client._send_raw_socketio = MagicMock()
        self.client._send_handshake_client()

        self.assertTrue(len(self.client._ack_callbacks) > 0)
        ack_id = list(self.client._ack_callbacks.keys())[0]

        # Simulate ACK received
        ack_payload = f"3{ack_id}[null, {{\"namespace\": \"/api\"}}]"
        self.client._handle_socketio_message(ack_payload)

        self.assertTrue(self.client._authenticated)
        self.assertEqual(self.client._namespace, "/api")


if __name__ == "__main__":
    unittest.main()
