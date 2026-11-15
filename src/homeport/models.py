"""Data models for Homey Pro devices, capabilities, zones, flows, and connection settings."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union


@dataclass
class HomeyCapability:
    """Represents a device capability (e.g. onoff, dim, measure_temperature)."""
    id: str
    value: Any = None
    type: str = "boolean"  # boolean, number, string, enum
    title: str = ""
    desc: str = ""
    units: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    getable: bool = True
    setable: bool = True
    values: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, cap_id: str, data: Union[Dict[str, Any], Any]) -> HomeyCapability:
        if isinstance(data, dict):
            return cls(
                id=cap_id,
                value=data.get("value"),
                type=data.get("type", "boolean"),
                title=data.get("title", cap_id),
                desc=data.get("desc", ""),
                units=data.get("units"),
                min=data.get("min"),
                max=data.get("max"),
                step=data.get("step"),
                getable=data.get("getable", True),
                setable=data.get("setable", True),
                values=data.get("values", []),
            )
        return cls(id=cap_id, value=data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HomeyDevice:
    """Represents a Homey device."""
    id: str
    name: str
    class_name: str = "other"  # light, socket, sensor, thermostat, etc.
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None
    icon_url: Optional[str] = None
    driver_id: Optional[str] = None
    ready: bool = True
    available: bool = True
    capabilities: List[str] = field(default_factory=list)
    capabilities_obj: Dict[str, HomeyCapability] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    is_favorite: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any], zones_map: Optional[Dict[str, str]] = None) -> HomeyDevice:
        dev_id = str(data.get("id") or data.get("_id", ""))
        name = data.get("name", "Unknown Device")
        class_name = data.get("class", "other")
        zone_id = data.get("zone")
        zone_name = zones_map.get(zone_id) if zones_map and zone_id else None
        icon_url = data.get("iconObj", {}).get("url") if isinstance(data.get("iconObj"), dict) else data.get("icon")
        driver_id = data.get("driverId")
        ready = bool(data.get("ready", True))
        available = bool(data.get("available", True))
        capabilities = list(data.get("capabilities", []))
        is_favorite = bool(
            data.get("isFavorite") or
            data.get("favorite") or
            (data.get("ui", {}).get("favorite") if isinstance(data.get("ui"), dict) else False)
        )

        cap_objs: Dict[str, HomeyCapability] = {}
        raw_cap_obj = data.get("capabilitiesObj") or {}
        if isinstance(raw_cap_obj, dict):
            for cid, cdata in raw_cap_obj.items():
                cap_objs[cid] = HomeyCapability.from_dict(cid, cdata)
        else:
            for cid in capabilities:
                cap_objs[cid] = HomeyCapability(id=cid)

        state: Dict[str, Any] = {}
        for cid, cap in cap_objs.items():
            state[cid] = cap.value

        return cls(
            id=dev_id,
            name=name,
            class_name=class_name,
            zone_id=zone_id,
            zone_name=zone_name,
            icon_url=icon_url,
            driver_id=driver_id,
            ready=ready,
            available=available,
            capabilities=capabilities,
            capabilities_obj=cap_objs,
            state=state,
            is_favorite=is_favorite,
        )

    @property
    def onoff(self) -> Optional[bool]:
        """Convenience property for on/off state."""
        if "onoff" in self.state and self.state["onoff"] is not None:
            return bool(self.state["onoff"])
        return None

    @property
    def dim(self) -> Optional[float]:
        """Convenience property for dimming level (0.0 - 1.0)."""
        if "dim" in self.state and self.state["dim"] is not None:
            try:
                return float(self.state["dim"])
            except (ValueError, TypeError):
                return None
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "class": self.class_name,
            "zoneId": self.zone_id,
            "zoneName": self.zone_name,
            "iconUrl": self.icon_url,
            "driverId": self.driver_id,
            "ready": self.ready,
            "available": self.available,
            "capabilities": list(self.capabilities),
            "capabilitiesObj": {cid: c.to_dict() for cid, c in self.capabilities_obj.items()},
            "state": dict(self.state),
            "onoff": self.onoff,
            "dim": self.dim,
            "isFavorite": self.is_favorite,
        }


@dataclass
class HomeyZone:
    """Represents a Zone / Room in Homey."""
    id: str
    name: str
    parent_id: Optional[str] = None
    icon: Optional[str] = None
    order: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HomeyZone:
        return cls(
            id=str(data.get("id") or data.get("_id", "")),
            name=data.get("name", "Unknown Zone"),
            parent_id=data.get("parent"),
            icon=data.get("icon"),
            order=int(data.get("order", 0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "parentId": self.parent_id,
            "icon": self.icon,
            "order": self.order,
        }


@dataclass
class HomeyFlow:
    """Represents a Homey Flow."""
    id: str
    name: str
    folder_id: Optional[str] = None
    enabled: bool = True
    triggerable: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HomeyFlow:
        return cls(
            id=str(data.get("id") or data.get("_id", "")),
            name=data.get("name", "Unnamed Flow"),
            folder_id=data.get("folder"),
            enabled=bool(data.get("enabled", True)),
            triggerable=bool(data.get("triggerable", True)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "folderId": self.folder_id,
            "enabled": self.enabled,
            "triggerable": self.triggerable,
        }


@dataclass
class HomeyInfo:
    """Represents a Homey Pro system instance."""
    id: str
    name: str
    platform: str = "local"  # local or cloud
    local_url: Optional[str] = None
    local_url_secure: Optional[str] = None
    remote_url: Optional[str] = None
    software_version: Optional[str] = None
    language: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HomeyInfo:
        return cls(
            id=str(data.get("_id") or data.get("id", "")),
            name=data.get("name", "Homey Pro"),
            platform=data.get("platform", "local"),
            local_url=data.get("localUrl"),
            local_url_secure=data.get("localUrlSecure"),
            remote_url=data.get("remoteUrl"),
            software_version=data.get("softwareVersion"),
            language=data.get("language"),
        )

    def get_preferred_url(self, preference: str = "auto") -> Optional[str]:
        """
        Returns the preferred URL based on availability and preference.
        preference: 'local_secure', 'local', 'remote', or 'auto' (local_secure -> local -> remote)
        """
        if preference == "local_secure" and self.local_url_secure:
            return self.local_url_secure
        if preference == "local" and self.local_url:
            return self.local_url
        if preference == "remote" and self.remote_url:
            return self.remote_url

        # Auto fallback: localUrlSecure -> localUrl -> remoteUrl
        return self.local_url_secure or self.local_url or self.remote_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "localUrl": self.local_url,
            "localUrlSecure": self.local_url_secure,
            "remoteUrl": self.remote_url,
            "softwareVersion": self.software_version,
            "language": self.language,
        }


@dataclass
class AuthTokens:
    """Stores OAuth and Homey session tokens."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600
    delegation_token: Optional[str] = None
    session_token: Optional[str] = None
    homey_id: Optional[str] = None
    direct_base_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuthTokens:
        return cls(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "bearer"),
            expires_in=int(data.get("expires_in", 3600)),
            delegation_token=data.get("delegation_token"),
            session_token=data.get("session_token"),
            homey_id=data.get("homey_id"),
            direct_base_url=data.get("direct_base_url"),
        )
