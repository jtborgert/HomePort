"""PyOtherSide Bridge layer connecting Sailfish OS QML UI with Homey Pro client."""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from .api import HomeyAuthError, HomeyClient, HomeyConnectionError
from .models import AuthTokens, HomeyDevice, HomeyFlow, HomeyInfo, HomeyZone
from .socket import HomeyRealtimeClient
from .storage import SettingsStorage

logger = logging.getLogger(__name__)

# Safe fallback for pyotherside when running outside QML runtime (e.g. CLI, tests)
try:
    import pyotherside
except ImportError:
    class _DummyPyOtherSide:
        @staticmethod
        def send(event_name: str, *args: Any) -> None:
            logger.debug("[PyOtherSide Event] %s: %s", event_name, args)

    pyotherside = _DummyPyOtherSide()


class HomePortBridge:
    """Singleton bridge controller between QML Silica UI and Homey backend."""

    def __init__(self, storage: Optional[SettingsStorage] = None):
        self.storage = storage or SettingsStorage()
        self.client = HomeyClient(
            verify_ssl=bool(self.storage.get("verify_ssl", True)),
        )
        self.realtime: Optional[HomeyRealtimeClient] = None
        self._devices_cache: Dict[str, HomeyDevice] = {}
        self._zones_cache: Dict[str, HomeyZone] = {}
        self._flows_cache: Dict[str, HomeyFlow] = {}
        self._lock = threading.Lock()

    def init_bridge(self) -> Dict[str, Any]:
        """Initializes client with stored credentials and checks login status."""
        tokens = self.storage.get_auth_tokens()
        self.client.auth_tokens = tokens
        self.client.client_id = self.storage.get("client_id")
        self.client.client_secret = self.storage.get("client_secret")

        direct_url = self.storage.get("direct_base_url")
        session_token = tokens.session_token

        is_configured = bool((direct_url and session_token) or (tokens.access_token or tokens.session_token))
        state = {
            "isConfigured": is_configured,
            "hasDirectUrl": bool(direct_url),
            "hasAccessToken": bool(tokens.access_token),
            "hasSessionToken": bool(session_token),
            "activeHomeyId": self.storage.get("active_homey_id", ""),
            "activeHomeyName": self.storage.get("active_homey_name", ""),
            "connectionMode": self.storage.get("connection_mode", "auto"),
            "directBaseUrl": direct_url or "",
            "sessionToken": session_token or "",
            "clientId": self.storage.get("client_id", ""),
            "clientSecret": self.storage.get("client_secret", ""),
            "username": self.storage.get("username", ""),
            "email": self.storage.get("email", ""),
        }

        if direct_url and session_token:
            self.client.set_session(direct_url, session_token, tokens.homey_id)
            self._start_realtime_client()

        return state

    def get_settings(self) -> Dict[str, Any]:
        """Returns all persisted settings, credentials, and tokens."""
        return self.storage.get_all_settings()

    def save_settings(self, settings_data: Dict[str, Any]) -> bool:
        """Saves settings, user credentials, and tokens."""
        try:
            if isinstance(settings_data, dict):
                data_to_save = dict(settings_data)
                # Normalize direct URL
                if "direct_base_url" in data_to_save and data_to_save["direct_base_url"]:
                    url = str(data_to_save["direct_base_url"]).strip().rstrip("/")
                    if url and not (url.startswith("http://") or url.startswith("https://")):
                        url = "http://" + url
                    data_to_save["direct_base_url"] = url
                    self.client.base_url = url
                if "client_id" in data_to_save:
                    self.client.client_id = data_to_save["client_id"]
                if "client_secret" in data_to_save:
                    self.client.client_secret = data_to_save["client_secret"]
                if "session_token" in data_to_save:
                    self.client.session_token = data_to_save["session_token"]
                self.storage.update(data_to_save)
                return True
        except Exception as e:
            logger.exception("Failed to save settings: %s", e)
        return False

    # --------------------------------------------------------------------------
    # Authentication & Connection APIs
    # --------------------------------------------------------------------------

    def get_oauth_url(self, client_id: str, redirect_uri: str) -> str:
        """Returns OAuth authorization URL for web browser."""
        return self.client.get_oauth_url(client_id, redirect_uri)

    def login_oauth(
        self,
        client_id: str,
        client_secret: str,
        auth_code: str,
        url_preference: str = "auto",
        email: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        """Asynchronously completes OAuth exchange and retrieves Homeys."""
        def worker() -> None:
            try:
                tokens = self.client.exchange_authorization_code(client_id, client_secret, auth_code)
                self.storage.set("client_id", client_id)
                self.storage.set("client_secret", client_secret)
                if email is not None:
                    self.storage.set("email", email)
                if username is not None:
                    self.storage.set("username", username)
                self.storage.save_auth_tokens(tokens)

                # Fetch Homeys
                _, homeys = self.client.get_user_info(tokens.access_token)
                self.storage.set_cached_homeys(homeys)

                homey_list = [h.to_dict() for h in homeys]
                pyotherside.send("oauth_success", homey_list)

                # If only one Homey exists, automatically connect to it
                if len(homeys) == 1:
                    self.select_homey(homeys[0].id, url_preference)
            except Exception as e:
                logger.exception("OAuth login failed")
                pyotherside.send("oauth_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def login_direct(
        self,
        base_url: str,
        session_token: str,
        homey_name: str = "Homey Pro Local",
        email: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        """Connects directly to a local Homey Pro using IP/URL and Session Token."""
        def worker() -> None:
            try:
                clean_url = base_url.strip().rstrip("/")
                if clean_url and not (clean_url.startswith("http://") or clean_url.startswith("https://")):
                    clean_url = "http://" + clean_url
                clean_token = session_token.strip()

                test_client = HomeyClient(
                    base_url=clean_url,
                    session_token=clean_token,
                    verify_ssl=bool(self.storage.get("verify_ssl", True)),
                )
                sys_info = test_client.get_system_info()
                clean_url = test_client.base_url

                self.client.set_session(clean_url, clean_token)
                self.storage.set("direct_base_url", clean_url)
                self.storage.set("session_token", clean_token)
                if email is not None:
                    self.storage.set("email", email)
                if username is not None:
                    self.storage.set("username", username)
                self.storage.set("active_homey_name", homey_name or sys_info.get("name", "Homey Pro"))
                self.storage.save()

                self._start_realtime_client()

                pyotherside.send("login_success", {
                    "baseUrl": clean_url,
                    "name": self.storage.get("active_homey_name"),
                    "systemInfo": sys_info,
                })

                self.fetch_devices()
            except Exception as e:
                logger.exception("Direct login failed")
                pyotherside.send("login_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_homeys(self) -> None:
        """Refreshes the user's Homeys list from Athom Cloud."""
        def worker() -> None:
            try:
                _, homeys = self.client.get_user_info()
                self.storage.set_cached_homeys(homeys)
                pyotherside.send("homeys_refreshed", [h.to_dict() for h in homeys])
            except Exception as e:
                logger.exception("Failed to refresh Homeys")
                pyotherside.send("homeys_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def select_homey(self, homey_id: str, url_preference: str = "auto") -> None:
        """Authenticates with a specific Homey and prepares session."""
        def worker() -> None:
            try:
                homeys = self.storage.get_cached_homeys()
                target_homey = next((h for h in homeys if h.id == homey_id), None)
                if not target_homey:
                    _, fresh_homeys = self.client.get_user_info()
                    self.storage.set_cached_homeys(fresh_homeys)
                    target_homey = next((h for h in fresh_homeys if h.id == homey_id), None)

                if not target_homey:
                    raise HomeyConnectionError(f"Homey {homey_id} not found in account")

                session_token = self.client.authenticate_with_homey(target_homey, url_preference)
                best_url = target_homey.get_preferred_url(url_preference) or ""

                self.storage.set("active_homey_id", target_homey.id)
                self.storage.set("active_homey_name", target_homey.name)
                self.storage.set("direct_base_url", best_url)
                self.storage.set("session_token", session_token)
                self.storage.set("connection_mode", url_preference)
                self.storage.save()

                self._start_realtime_client()

                pyotherside.send("homey_selected", {
                    "id": target_homey.id,
                    "name": target_homey.name,
                    "url": best_url,
                })

                self.fetch_devices()
            except Exception as e:
                logger.exception("Failed to select Homey")
                pyotherside.send("homey_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def logout(self) -> None:
        """Logs out and clears saved sessions."""
        if self.realtime:
            self.realtime.stop()
            self.realtime = None
        self.storage.clear_tokens()
        self.client.session_token = None
        self.client.base_url = ""
        self._devices_cache.clear()
        self._zones_cache.clear()
        self._flows_cache.clear()
        pyotherside.send("logged_out", {})

    # --------------------------------------------------------------------------
    # Devices, Zones & Capabilities Management
    # --------------------------------------------------------------------------

    def fetch_devices(self) -> None:
        """Fetches all devices and zones from Homey."""
        def worker() -> None:
            try:
                zones = self.client.get_zones()
                self._zones_cache = zones
                zones_map = {zid: z.name for zid, z in zones.items()}

                devices = self.client.get_devices(zones_map=zones_map)
                self._devices_cache = devices

                # Attach favorite metadata
                dev_list: List[Dict[str, Any]] = []
                for dev in devices.values():
                    is_fav = self.storage.is_favorite(dev.id) or dev.is_favorite
                    dev.is_favorite = is_fav
                    if is_fav and not self.storage.is_favorite(dev.id):
                        self.storage.set_favorite(dev.id, True)
                    d_dict = dev.to_dict()
                    d_dict["isFavorite"] = is_fav
                    dev_list.append(d_dict)

                # Subscribe to device real-time updates
                if self.realtime and self.realtime.is_connected:
                    for did in devices.keys():
                        self.realtime.subscribe(f"homey:device:{did}")

                pyotherside.send("devices_loaded", dev_list)
                pyotherside.send("zones_loaded", [z.to_dict() for z in zones.values()])
            except Exception as e:
                logger.exception("Failed to fetch devices")
                pyotherside.send("devices_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def set_device_capability(self, device_id: str, capability_id: str, value: Any) -> None:
        """Sets a capability value for a device."""
        def worker() -> None:
            try:
                self.client.set_device_capability(device_id, capability_id, value)
                # Optimistically update cache
                if device_id in self._devices_cache:
                    dev = self._devices_cache[device_id]
                    dev.state[capability_id] = value
                    if capability_id in dev.capabilities_obj:
                        dev.capabilities_obj[capability_id].value = value

                pyotherside.send("device_capability_updated", {
                    "deviceId": device_id,
                    "capabilityId": capability_id,
                    "value": value,
                })
            except Exception as e:
                logger.exception("Failed to update capability %s on device %s", capability_id, device_id)
                pyotherside.send("device_error", {
                    "deviceId": device_id,
                    "error": str(e),
                })

        threading.Thread(target=worker, daemon=True).start()

    def toggle_device(self, device_id: str) -> None:
        """Toggles a device's onoff state."""
        def worker() -> None:
            try:
                dev = self._devices_cache.get(device_id)
                if not dev:
                    dev = self.client.get_device(device_id)
                    self._devices_cache[device_id] = dev

                current_val = bool(dev.onoff)
                new_val = not current_val
                self.client.set_device_capability(device_id, "onoff", new_val)

                dev.state["onoff"] = new_val
                if "onoff" in dev.capabilities_obj:
                    dev.capabilities_obj["onoff"].value = new_val

                pyotherside.send("device_capability_updated", {
                    "deviceId": device_id,
                    "capabilityId": "onoff",
                    "value": new_val,
                })
            except Exception as e:
                logger.exception("Failed to toggle device %s", device_id)
                pyotherside.send("device_error", {
                    "deviceId": device_id,
                    "error": str(e),
                })

        threading.Thread(target=worker, daemon=True).start()

    def toggle_favorite(self, device_id: str) -> bool:
        """Toggles favorite status of device."""
        is_fav = self.storage.toggle_favorite(device_id)
        if device_id in self._devices_cache:
            self._devices_cache[device_id].is_favorite = is_fav
        pyotherside.send("favorite_toggled", {
            "deviceId": device_id,
            "isFavorite": is_fav,
        })
        return is_fav

    def set_favorite(self, device_id: str, is_fav: bool) -> bool:
        """Sets favorite status of device."""
        res = self.storage.set_favorite(device_id, is_fav)
        if device_id in self._devices_cache:
            self._devices_cache[device_id].is_favorite = res
        pyotherside.send("favorite_toggled", {
            "deviceId": device_id,
            "isFavorite": res,
        })
        return res

    def get_favorites(self) -> List[str]:
        """Returns list of favorite device IDs."""
        return self.storage.get_favorite_devices()

    def get_devices(self) -> List[Dict[str, Any]]:
        """Returns all cached devices as dicts with favorite info."""
        res: List[Dict[str, Any]] = []
        for dev in self._devices_cache.values():
            d_dict = dev.to_dict()
            d_dict["isFavorite"] = self.storage.is_favorite(dev.id) or dev.is_favorite
            res.append(d_dict)
        return res

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Returns a single device by ID with capabilities and state."""
        dev = self._devices_cache.get(device_id)
        if not dev:
            try:
                dev = self.client.get_device(device_id)
                self._devices_cache[device_id] = dev
            except Exception:
                return None
        if dev:
            d_dict = dev.to_dict()
            d_dict["isFavorite"] = self.storage.is_favorite(dev.id) or dev.is_favorite
            return d_dict
        return None

    # --------------------------------------------------------------------------
    # Flows Management
    # --------------------------------------------------------------------------

    def fetch_flows(self) -> None:
        """Fetches all Flows."""
        def worker() -> None:
            try:
                flows = self.client.get_flows()
                self._flows_cache = flows
                pyotherside.send("flows_loaded", [f.to_dict() for f in flows.values()])
            except Exception as e:
                logger.exception("Failed to fetch flows")
                pyotherside.send("flows_error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def trigger_flow(self, flow_id: str) -> None:
        """Triggers a Flow."""
        def worker() -> None:
            try:
                self.client.trigger_flow(flow_id)
                pyotherside.send("flow_triggered", {"flowId": flow_id, "success": True})
            except Exception as e:
                logger.exception("Failed to trigger flow %s", flow_id)
                pyotherside.send("flow_error", {"flowId": flow_id, "error": str(e)})

        threading.Thread(target=worker, daemon=True).start()

    # --------------------------------------------------------------------------
    # Real-Time WebSocket / Socket.IO Management
    # --------------------------------------------------------------------------

    def _start_realtime_client(self) -> None:
        """Starts real-time Socket.io listener."""
        if self.realtime:
            self.realtime.stop()

        base_url = self.client.base_url or self.storage.get("direct_base_url")
        token = self.client.session_token or self.storage.get("session_token")
        homey_id = self.storage.get("active_homey_id", "")

        if not base_url or not token:
            return

        self.realtime = HomeyRealtimeClient(
            base_url=base_url,
            session_token=token,
            homey_id=homey_id,
            on_event=self._on_realtime_event,
            verify_ssl=bool(self.storage.get("verify_ssl", True)),
        )
        self.realtime.start()
        self.realtime.subscribe("homey:manager:flow")
        self.realtime.subscribe("homey:manager:devices")

    def _on_realtime_event(self, uri: str, event_type: str, data: Any) -> None:
        """Dispatches incoming Socket.IO events to QML."""
        logger.debug("Socket.IO event: uri=%s event_type=%s", uri, event_type)

        if uri.startswith("homey:device:"):
            device_id = uri.split(":")[-1]
            if isinstance(data, dict):
                capability_id = data.get("capabilityId") or data.get("capability")
                value = data.get("value")
                if capability_id:
                    # Update cache
                    if device_id in self._devices_cache:
                        self._devices_cache[device_id].state[capability_id] = value
                        if capability_id in self._devices_cache[device_id].capabilities_obj:
                            self._devices_cache[device_id].capabilities_obj[capability_id].value = value

                    pyotherside.send("device_capability_updated", {
                        "deviceId": device_id,
                        "capabilityId": capability_id,
                        "value": value,
                    })

        elif uri == "homey:manager:flow":
            pyotherside.send("flow_event", {
                "eventType": event_type,
                "data": data,
            })


# Global singleton instance for PyOtherSide
bridge = HomePortBridge()

# Exposed module-level functions for PyOtherSide `call()`
def init() -> Dict[str, Any]:
    return bridge.init_bridge()

def get_settings() -> Dict[str, Any]:
    return bridge.get_settings()

def save_settings(settings_data: Dict[str, Any]) -> bool:
    return bridge.save_settings(settings_data)

def get_oauth_url(client_id: str, redirect_uri: str) -> str:
    return bridge.get_oauth_url(client_id, redirect_uri)

def login_oauth(client_id: str, client_secret: str, auth_code: str, url_preference: str = "auto", email: str = "", username: str = "") -> None:
    bridge.login_oauth(client_id, client_secret, auth_code, url_preference, email=email or None, username=username or None)

def login_direct(base_url: str, session_token: str, homey_name: str = "", email: str = "", username: str = "") -> None:
    bridge.login_direct(base_url, session_token, homey_name, email=email or None, username=username or None)

def refresh_homeys() -> None:
    bridge.refresh_homeys()

def select_homey(homey_id: str, url_preference: str = "auto") -> None:
    bridge.select_homey(homey_id, url_preference)

def logout() -> None:
    bridge.logout()

def fetch_devices() -> None:
    bridge.fetch_devices()

def set_device_capability(device_id: str, capability_id: str, value: Any) -> None:
    bridge.set_device_capability(device_id, capability_id, value)

def toggle_device(device_id: str) -> None:
    bridge.toggle_device(device_id)

def toggle_favorite(device_id: str) -> bool:
    return bridge.toggle_favorite(device_id)

def set_favorite(device_id: str, is_fav: bool) -> bool:
    return bridge.set_favorite(device_id, is_fav)

def get_favorites() -> List[str]:
    return bridge.get_favorites()

def get_devices() -> List[Dict[str, Any]]:
    return bridge.get_devices()

def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    return bridge.get_device(device_id)

def fetch_flows() -> None:
    bridge.fetch_flows()

def trigger_flow(flow_id: str) -> None:
    bridge.trigger_flow(flow_id)
