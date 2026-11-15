"""HTTP client for Homey Pro and Athom Cloud Web API."""

from __future__ import annotations

import base64
import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import AuthTokens, HomeyDevice, HomeyFlow, HomeyInfo, HomeyZone

logger = logging.getLogger(__name__)


class HomeyApiError(Exception):
    """Base exception for Homey API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class HomeyAuthError(HomeyApiError):
    """Raised when authentication fails or token is expired."""
    pass


class HomeyConnectionError(HomeyApiError):
    """Raised when network connection fails."""
    pass


class HomeyClient:
    """
    Client for interacting with Homey Pro directly and via Athom Cloud API.
    Uses standard library urllib for zero external dependencies on Sailfish OS.
    """

    ATHOM_API_BASE = "https://api.athom.com"
    DEFAULT_TIMEOUT = 15.0

    def __init__(
        self,
        base_url: Optional[str] = None,
        session_token: Optional[str] = None,
        auth_tokens: Optional[AuthTokens] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        verify_ssl: bool = True,
    ):
        raw_url = (base_url or "").strip().rstrip("/")
        if raw_url and not (raw_url.startswith("http://") or raw_url.startswith("https://")):
            raw_url = "http://" + raw_url
        self.base_url = raw_url
        self.session_token = session_token
        self.auth_tokens = auth_tokens or AuthTokens()
        if session_token and not self.auth_tokens.session_token:
            self.auth_tokens.session_token = session_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        self._ssl_context: Optional[ssl.SSLContext] = None
        if not verify_ssl:
            self._ssl_context = ssl._create_unverified_context()

    def set_session(self, base_url: str, session_token: str, homey_id: Optional[str] = None) -> None:
        """Sets active Homey base URL and session token."""
        clean_url = (base_url or "").strip().rstrip("/")
        if clean_url and not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "http://" + clean_url
        self.base_url = clean_url
        self.session_token = session_token
        self.auth_tokens.session_token = session_token
        self.auth_tokens.direct_base_url = self.base_url
        if homey_id:
            self.auth_tokens.homey_id = homey_id

    # --------------------------------------------------------------------------
    # Athom Cloud OAuth2 and Delegation Token Methods
    # --------------------------------------------------------------------------

    def get_oauth_url(self, client_id: str, redirect_uri: str, state: str = "homeport") -> str:
        """Constructs the OAuth2 authorization URL for the user browser / webview."""
        params = {
            "authorization_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
        return f"{self.ATHOM_API_BASE}/oauth2/authorise?{urllib.parse.urlencode(params)}"

    def exchange_authorization_code(
        self,
        client_id: str,
        client_secret: str,
        code: str,
    ) -> AuthTokens:
        """
        Exchanges an OAuth2 authorization code for an Athom Cloud access & refresh token.
        Endpoint: POST https://api.athom.com/oauth2/token
        """
        auth_header = "Basic " + base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
        body_data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "authorization_code": code,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": auth_header,
        }

        url = f"{self.ATHOM_API_BASE}/oauth2/token"
        res = self._request("POST", url, headers=headers, data=body_data)
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_tokens.access_token = res.get("access_token")
        self.auth_tokens.refresh_token = res.get("refresh_token")
        self.auth_tokens.token_type = res.get("token_type", "bearer")
        self.auth_tokens.expires_in = int(res.get("expires_in", 3600))
        return self.auth_tokens

    def refresh_access_token(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None,
    ) -> AuthTokens:
        """
        Refreshes the Athom Cloud access token using the refresh token.
        Endpoint: POST https://api.athom.com/oauth2/token
        """
        cid = client_id or self.client_id
        csec = client_secret or self.client_secret
        rtoken = refresh_token or self.auth_tokens.refresh_token

        if not cid or not csec:
            raise HomeyAuthError("Missing client_id or client_secret for token refresh")
        if not rtoken:
            raise HomeyAuthError("Missing refresh_token for token refresh")

        auth_header = "Basic " + base64.b64encode(f"{cid}:{csec}".encode("utf-8")).decode("utf-8")
        body_data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": rtoken,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": auth_header,
        }

        url = f"{self.ATHOM_API_BASE}/oauth2/token"
        res = self._request("POST", url, headers=headers, data=body_data)

        self.auth_tokens.access_token = res.get("access_token")
        if res.get("refresh_token"):
            self.auth_tokens.refresh_token = res.get("refresh_token")
        self.auth_tokens.expires_in = int(res.get("expires_in", 3600))
        return self.auth_tokens

    def get_user_info(self, access_token: Optional[str] = None) -> Tuple[Dict[str, Any], List[HomeyInfo]]:
        """
        Retrieves user information and list of available Homeys from Athom Cloud.
        Endpoint: GET https://api.athom.com/user/me
        """
        token = access_token or self.auth_tokens.access_token
        if not token:
            raise HomeyAuthError("Missing access token for Athom Cloud")

        headers = {
            "Authorization": f"Bearer {token}",
        }

        url = f"{self.ATHOM_API_BASE}/user/me"
        res = self._request("GET", url, headers=headers)

        homeys: List[HomeyInfo] = []
        raw_homeys = res.get("homeys", [])
        if isinstance(raw_homeys, list):
            for h in raw_homeys:
                homeys.append(HomeyInfo.from_dict(h))

        return res, homeys

    def get_delegation_token(self, access_token: Optional[str] = None) -> str:
        """
        Obtains a JWT delegation token for Homey from Athom Cloud.
        Endpoint: POST https://api.athom.com/delegation/token?audience=homey
        """
        token = access_token or self.auth_tokens.access_token
        if not token:
            raise HomeyAuthError("Missing access token for delegation token request")

        headers = {
            "Authorization": f"Bearer {token}",
        }

        url = f"{self.ATHOM_API_BASE}/delegation/token?audience=homey"
        res = self._request("POST", url, headers=headers)

        # Body is a JSON string (e.g. "abc...") or dict {"token": "..."}
        if isinstance(res, str):
            delegation_token = res
        elif isinstance(res, dict) and "token" in res:
            delegation_token = str(res["token"])
        else:
            delegation_token = str(res)

        self.auth_tokens.delegation_token = delegation_token
        return delegation_token

    def create_homey_session(self, homey_url: str, delegation_token: Optional[str] = None) -> str:
        """
        Creates a session on the Homey Pro using the delegation token.
        Endpoint: POST <homey_url>/api/manager/users/login
        """
        del_token = delegation_token or self.auth_tokens.delegation_token
        if not del_token:
            del_token = self.get_delegation_token()

        target_url = homey_url.rstrip("/") + "/api/manager/users/login"
        payload = json.dumps({"token": del_token}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }

        res = self._request("POST", target_url, headers=headers, data=payload)

        # Body is a JSON string (e.g. "session_token_xyz") or dict
        if isinstance(res, str):
            session_tok = res
        elif isinstance(res, dict) and "token" in res:
            session_tok = str(res["token"])
        else:
            session_tok = str(res)

        self.base_url = homey_url.rstrip("/")
        self.session_token = session_tok
        self.auth_tokens.session_token = session_tok
        self.auth_tokens.direct_base_url = self.base_url
        return session_tok

    def authenticate_with_homey(
        self,
        homey_info: HomeyInfo,
        url_preference: str = "auto",
        access_token: Optional[str] = None,
    ) -> str:
        """
        Full flow: gets delegation token and creates session on the selected Homey.
        """
        best_url = homey_info.get_preferred_url(url_preference)
        if not best_url:
            raise HomeyConnectionError(f"No usable URL available for Homey {homey_info.name}")

        self.auth_tokens.homey_id = homey_info.id
        del_token = self.get_delegation_token(access_token)
        return self.create_homey_session(best_url, del_token)

    # --------------------------------------------------------------------------
    # Homey Local Manager & Device APIs
    # --------------------------------------------------------------------------

    def get_system_info(self) -> Dict[str, Any]:
        """
        Fetches Homey Pro system status and hardware/software info.
        Endpoint: GET /api/manager/system
        """
        return self._homey_request("GET", "/api/manager/system")

    def get_zones(self) -> Dict[str, HomeyZone]:
        """
        Fetches all Zones / Rooms.
        Endpoint: GET /api/manager/zones/zone
        """
        res = self._homey_request("GET", "/api/manager/zones/zone")
        zones: Dict[str, HomeyZone] = {}
        if isinstance(res, dict):
            for zid, zdata in res.items():
                if isinstance(zdata, dict):
                    zones[str(zid)] = HomeyZone.from_dict(zdata)
        elif isinstance(res, list):
            for zdata in res:
                if isinstance(zdata, dict):
                    z = HomeyZone.from_dict(zdata)
                    zones[z.id] = z
        return zones

    def get_devices(self, zones_map: Optional[Dict[str, str]] = None) -> Dict[str, HomeyDevice]:
        """
        Fetches all devices registered with Homey.
        Endpoint: GET /api/manager/devices/device
        """
        # If zones_map not provided, optionally resolve zone names
        if zones_map is None:
            try:
                zones = self.get_zones()
                zones_map = {zid: z.name for zid, z in zones.items()}
            except Exception as e:
                logger.warning("Could not fetch zones: %s", e)
                zones_map = {}

        res = self._homey_request("GET", "/api/manager/devices/device")
        devices: Dict[str, HomeyDevice] = {}

        if isinstance(res, dict):
            for did, ddata in res.items():
                if isinstance(ddata, dict):
                    devices[str(did)] = HomeyDevice.from_dict(ddata, zones_map=zones_map)
        elif isinstance(res, list):
            for ddata in res:
                if isinstance(ddata, dict):
                    dev = HomeyDevice.from_dict(ddata, zones_map=zones_map)
                    devices[dev.id] = dev

        return devices

    def get_device(self, device_id: str, zones_map: Optional[Dict[str, str]] = None) -> HomeyDevice:
        """
        Fetches details for a single device.
        Endpoint: GET /api/manager/devices/device/<device_id>
        """
        res = self._homey_request("GET", f"/api/manager/devices/device/{device_id}")
        return HomeyDevice.from_dict(res, zones_map=zones_map)

    def set_device_capability(
        self,
        device_id: str,
        capability_id: str,
        value: Any,
    ) -> Dict[str, Any]:
        """
        Updates a capability state for a device (e.g. onoff, dim, target_temperature).
        Endpoint: PUT /api/manager/devices/device/<device_id>/capability/<capability_id>
        """
        payload = json.dumps({"value": value}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        return self._homey_request(
            "PUT",
            f"/api/manager/devices/device/{device_id}/capability/{capability_id}",
            headers=headers,
            data=payload,
        )

    def toggle_device(self, device: HomeyDevice) -> Dict[str, Any]:
        """Convenience method to toggle the onoff capability of a device."""
        if "onoff" not in device.capabilities and "onoff" not in device.state:
            raise HomeyApiError(f"Device {device.name} does not support onoff capability")
        new_val = not bool(device.onoff)
        return self.set_device_capability(device.id, "onoff", new_val)

    def set_device_dim(self, device_id: str, dim_level: float) -> Dict[str, Any]:
        """Convenience method to set dim level (clamped 0.0 to 1.0)."""
        dim_level = max(0.0, min(1.0, float(dim_level)))
        return self.set_device_capability(device_id, "dim", dim_level)

    def get_flows(self) -> Dict[str, HomeyFlow]:
        """
        Fetches all Flows from Homey.
        Endpoint: GET /api/manager/flow/flow
        """
        res = self._homey_request("GET", "/api/manager/flow/flow")
        flows: Dict[str, HomeyFlow] = {}

        if isinstance(res, dict):
            for fid, fdata in res.items():
                if isinstance(fdata, dict):
                    flows[str(fid)] = HomeyFlow.from_dict(fdata)
        elif isinstance(res, list):
            for fdata in res:
                if isinstance(fdata, dict):
                    flow = HomeyFlow.from_dict(fdata)
                    flows[flow.id] = flow

        return flows

    def trigger_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Triggers / executes a Flow.
        Endpoint: POST /api/manager/flow/flow/<flow_id>/trigger
        """
        return self._homey_request("POST", f"/api/manager/flow/flow/{flow_id}/trigger")

    # --------------------------------------------------------------------------
    # Internal HTTP Request Dispatcher
    # --------------------------------------------------------------------------

    def _homey_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> Any:
        """Executes an authenticated request against the connected Homey Pro."""
        if not self.base_url:
            raise HomeyConnectionError("Homey base URL is not set")

        token = self.session_token or self.auth_tokens.session_token
        req_headers = dict(headers or {})
        if token:
            req_headers["Authorization"] = f"Bearer {token}"

        url = f"{self.base_url}{path}"
        try:
            return self._request(method, url, headers=req_headers, data=data)
        except HomeyAuthError:
            # If token expired and Athom Cloud tokens are available, try refresh session
            if self.auth_tokens.access_token:
                logger.info("Session token expired. Attempting token refresh...")
                try:
                    if self.client_id and self.auth_tokens.refresh_token:
                        self.refresh_access_token()
                    del_token = self.get_delegation_token()
                    new_session = self.create_homey_session(self.base_url, del_token)
                    req_headers["Authorization"] = f"Bearer {new_session}"
                    return self._request(method, url, headers=req_headers, data=data)
                except Exception as refresh_err:
                    logger.error("Failed to re-authenticate session: %s", refresh_err)
            raise

    def _request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
    ) -> Any:
        """Low-level HTTP request handler using standard urllib."""
        req_headers = {
            "User-Agent": "HomePort/1.0 (SailfishOS)",
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context) as response:
                content_type = response.headers.get("Content-Type", "")
                raw_body = response.read()
                if not raw_body:
                    return {}

                if isinstance(raw_body, bytes):
                    text = raw_body.decode("utf-8")
                else:
                    text = str(raw_body)
                if "application/json" in content_type or text.startswith(("{", "[", '"')):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
                return text

        except urllib.error.HTTPError as http_err:
            status = http_err.code
            err_body = ""
            parsed_err: Any = None
            try:
                err_body = http_err.read().decode("utf-8")
                parsed_err = json.loads(err_body)
            except Exception:
                parsed_err = err_body

            msg = f"HTTP {status} {http_err.reason} for {method} {url}"
            if isinstance(parsed_err, dict) and "error" in parsed_err:
                msg += f": {parsed_err.get('error')}"
                if "error_description" in parsed_err:
                    msg += f" - {parsed_err.get('error_description')}"
            elif isinstance(parsed_err, dict) and "message" in parsed_err:
                msg += f": {parsed_err.get('message')}"

            if status in (401, 403):
                raise HomeyAuthError(msg, status_code=status, response_data=parsed_err)
            raise HomeyApiError(msg, status_code=status, response_data=parsed_err)

        except urllib.error.URLError as url_err:
            raise HomeyConnectionError(f"Connection error to {url}: {url_err.reason}") from url_err
        except TimeoutError as timeout_err:
            raise HomeyConnectionError(f"Timeout connecting to {url}") from timeout_err
        except Exception as e:
            raise HomeyConnectionError(f"Network error communicating with {url}: {e}") from e
