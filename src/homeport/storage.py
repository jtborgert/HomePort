"""Configuration and token persistence storage for HomePort on Sailfish OS.

Follows official Sailfish OS guidelines for secure application data storage:
- Stores non-secret and secret configuration in $XDG_CONFIG_HOME/harbour-homeport
- Enforces strict user-only filesystem permissions (0700 for directories, 0600 for files)
- Implements atomic file writes to prevent data corruption
- Supports secret lifecycle management (secure token wipe on logout)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import AuthTokens, HomeyInfo

logger = logging.getLogger(__name__)


def load_env(
    dotenv_path: Optional[str | Path] = None,
    override: bool = False,
) -> Dict[str, str]:
    """
    Loads environment variables from a .env file into os.environ.

    Searches for .env in the current working directory, git repository root,
    or custom path if provided.

    Returns a dictionary of loaded environment variables.
    """
    if dotenv_path:
        env_file = Path(dotenv_path)
    else:
        # Search current working directory, then package/project root
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parents[2] / ".env",
            Path.home() / ".config" / SettingsStorage.ORG_NAME / SettingsStorage.APP_DIR_NAME / ".env",
            Path.home() / ".config" / SettingsStorage.LEGACY_ORG_NAME / SettingsStorage.APP_DIR_NAME / ".env",
            Path.home() / ".config" / SettingsStorage.APP_DIR_NAME / ".env",
        ]
        env_file = next((p for p in candidates if p.is_file()), Path.cwd() / ".env")

    loaded: Dict[str, str] = {}
    if not env_file.is_file():
        return loaded

    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                # Remove quotes if present
                if len(val) >= 2 and (
                    (val.startswith('"') and val.endswith('"'))
                    or (val.startswith("'") and val.endswith("'"))
                ):
                    val = val[1:-1]
                loaded[key] = val
                if override or key not in os.environ:
                    os.environ[key] = val
    except Exception as e:
        logger.warning("Failed to load .env file from %s: %s", env_file, e)

    return loaded


class SettingsStorage:
    """
    Manages persistent settings, credentials, and tokens in the standard Sailfish OS
    XDG / Sailjail config directories (~/.config/de.tobias-borgert/harbour-homeport/settings.json).

    Enforces POSIX file permission 0600 (read/write only by owner) to safeguard
    sensitive information (session tokens, client secrets, access tokens).
    Implements schema versioning, seamless automatic configuration migrations, and
    cross-directory discovery compatible with Sailjail application profile sandboxing.
    """

    SCHEMA_VERSION = 1
    ORG_NAME = "de.tobias-borgert"
    LEGACY_ORG_NAME = "de.posteo.tobias.borgert"
    APP_DIR_NAME = "harbour-homeport"

    def __init__(self, config_dir: Optional[str] = None, load_env_vars: bool = True):
        if config_dir:
            self.base_dir = Path(config_dir)
            self.file_path = self.base_dir / "settings.json"
            self._ensure_secure_dir()
        else:
            self.base_dir, self.file_path = self._resolve_storage_path()

        self._data: Dict[str, Any] = self._load()
        if load_env_vars:
            self.load_from_env(override=False)

    @classmethod
    def get_candidate_dirs(cls) -> List[Path]:
        """Returns list of candidate configuration and data directories in priority order."""
        candidates: List[Path] = []

        # 1. Explicit env vars
        custom_dir = os.environ.get("HOMEPORT_CONFIG_DIR") or os.environ.get("HOMEY_CONFIG_DIR")
        if custom_dir:
            candidates.append(Path(custom_dir))

        home = Path.home()
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        config_root = Path(xdg_config) if xdg_config else home / ".config"

        xdg_data = os.environ.get("XDG_DATA_HOME")
        data_root = Path(xdg_data) if xdg_data else home / ".local" / "share"

        # 2. Sailjail application profile sandboxed directories (Org/App)
        candidates.append(config_root / cls.ORG_NAME / cls.APP_DIR_NAME)
        candidates.append(data_root / cls.ORG_NAME / cls.APP_DIR_NAME)

        # 3. Legacy Sailjail sandboxed directories for backward compatibility and migration
        candidates.append(config_root / cls.LEGACY_ORG_NAME / cls.APP_DIR_NAME)
        candidates.append(data_root / cls.LEGACY_ORG_NAME / cls.APP_DIR_NAME)

        # 4. Standard un-sandboxed XDG directories (App)
        candidates.append(config_root / cls.APP_DIR_NAME)
        candidates.append(data_root / cls.APP_DIR_NAME)

        # 5. Fallback temp directory
        tmp_dir = Path(tempfile.gettempdir()) / cls.APP_DIR_NAME
        candidates.append(tmp_dir)

        # Deduplicate while preserving order
        unique_candidates: List[Path] = []
        for c in candidates:
            if c not in unique_candidates:
                unique_candidates.append(c)
        return unique_candidates

    @classmethod
    def _resolve_storage_path(cls) -> tuple[Path, Path]:
        """
        Determines the active writable base directory and settings file path.
        Prioritizes Sailjail application sandboxed directories (~/.config/<Org>/<App>).
        """
        candidates = cls.get_candidate_dirs()

        # Check if an existing settings.json exists in any candidate directory
        existing_file_dir: Optional[Path] = None
        for candidate in candidates:
            try:
                candidate_file = candidate / "settings.json"
                if candidate_file.is_file():
                    existing_file_dir = candidate
                    break
            except Exception:
                pass

        # Find the first writable candidate directory
        writable_dir: Optional[Path] = None
        for candidate in candidates:
            try:
                candidate.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    os.chmod(candidate, 0o700)
                except Exception:
                    pass
                # Test write capability
                probe = candidate / ".homeport_probe"
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("probe")
                if probe.exists():
                    probe.unlink(missing_ok=True)
                writable_dir = candidate
                break
            except Exception as e:
                logger.debug("Candidate directory %s not writable: %s", candidate, e)
                continue

        if not writable_dir:
            home = Path.home()
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            config_root = Path(xdg_config) if xdg_config else home / ".config"
            writable_dir = config_root / cls.ORG_NAME / cls.APP_DIR_NAME

        target_file = writable_dir / "settings.json"

        # If existing file was in a different directory and target_file doesn't exist yet, migrate it
        if existing_file_dir and existing_file_dir != writable_dir and not target_file.is_file():
            try:
                src_file = existing_file_dir / "settings.json"
                if src_file.is_file():
                    with open(src_file, "r", encoding="utf-8") as f_in, open(target_file, "w", encoding="utf-8") as f_out:
                        f_out.write(f_in.read())
                    try:
                        os.chmod(target_file, 0o600)
                    except Exception:
                        pass
                    logger.info("Migrated existing settings from %s to %s", src_file, target_file)
            except Exception as e:
                logger.warning("Failed to migrate existing settings from %s: %s", existing_file_dir, e)

        return writable_dir, target_file

    @property
    def schema_version(self) -> int:
        """Returns the schema version of the loaded configuration."""
        return int(self._data.get("schema_version", self.SCHEMA_VERSION))

    def _ensure_secure_dir(self) -> None:
        """Ensures the configuration directory exists with restricted 0700 permissions."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                os.chmod(self.base_dir, 0o700)
            except Exception:
                pass
        except Exception as e:
            logger.warning("Could not set 0700 permissions on %s: %s", self.base_dir, e)

    def _load(self) -> Dict[str, Any]:
        """Loads settings from disk if available, automatically migrating older schema versions."""
        target_path = self.file_path
        if not target_path.exists():
            # Check all candidate directories if file exists elsewhere
            for candidate in self.get_candidate_dirs():
                alt_path = candidate / "settings.json"
                if alt_path.is_file():
                    target_path = alt_path
                    break

        if not target_path.exists():
            return self._defaults()
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if not isinstance(content, dict):
                    return self._defaults()

                # Detect existing schema version
                file_version = self._detect_version(content)
                needs_save = False

                if file_version < self.SCHEMA_VERSION:
                    content = self._migrate(content, from_version=file_version, to_version=self.SCHEMA_VERSION)
                    needs_save = True

                defaults = self._defaults()
                defaults.update(content)
                defaults["schema_version"] = self.SCHEMA_VERSION

                if needs_save or target_path != self.file_path:
                    self._data = defaults
                    self.save()

                return defaults
        except Exception as e:
            logger.warning("Failed to load settings file %s: %s", target_path, e)
            return self._defaults()

    def _detect_version(self, data: Dict[str, Any]) -> int:
        """Determines the schema version of loaded configuration data."""
        if "schema_version" in data:
            try:
                return int(data["schema_version"])
            except (ValueError, TypeError):
                return 0
        if "version" in data:
            try:
                return int(data["version"])
            except (ValueError, TypeError):
                return 0
        if "config_version" in data:
            try:
                return int(data["config_version"])
            except (ValueError, TypeError):
                return 0
        return 0

    def _migrate(self, data: Dict[str, Any], from_version: int, to_version: int) -> Dict[str, Any]:
        """Progressively migrates configuration data across schema versions."""
        cur = from_version
        while cur < to_version:
            migrate_method = getattr(self, f"_migrate_{cur}_to_{cur + 1}", None)
            if callable(migrate_method):
                data = migrate_method(data)
            else:
                logger.info("No explicit migration step from v%d to v%d; applying default schema upgrade", cur, cur + 1)
                data["schema_version"] = cur + 1
            cur += 1
        return data

    def _migrate_0_to_1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrates unversioned legacy config format (v0) to schema version 1:
        - Normalizes legacy key aliases (base_url -> direct_base_url, user -> username, etc.)
        - Flattens legacy nested token structures
        - Enforces correct field types and sets schema_version = 1
        """
        migrated = dict(data)

        # Legacy URL mappings
        if "base_url" in migrated and not migrated.get("direct_base_url"):
            migrated["direct_base_url"] = migrated.pop("base_url")

        # Legacy user mappings
        if "user" in migrated and not migrated.get("username"):
            migrated["username"] = migrated.pop("user")

        # Legacy favorites mappings
        if "favorites" in migrated and not migrated.get("favorite_devices"):
            migrated["favorite_devices"] = migrated.pop("favorites")

        # Legacy nested tokens dictionary
        if "tokens" in migrated and isinstance(migrated["tokens"], dict):
            tokens = migrated.pop("tokens")
            if "access_token" in tokens and not migrated.get("access_token"):
                migrated["access_token"] = tokens.get("access_token", "")
            if "refresh_token" in tokens and not migrated.get("refresh_token"):
                migrated["refresh_token"] = tokens.get("refresh_token", "")
            if "session_token" in tokens and not migrated.get("session_token"):
                migrated["session_token"] = tokens.get("session_token", "")
            if "delegation_token" in tokens and not migrated.get("delegation_token"):
                migrated["delegation_token"] = tokens.get("delegation_token", "")

        # Legacy api_key alias
        if "api_key" in migrated and not migrated.get("session_token"):
            migrated["session_token"] = migrated.pop("api_key")

        # Ensure correct list type for favorites
        if "favorite_devices" in migrated:
            if not isinstance(migrated["favorite_devices"], list):
                migrated["favorite_devices"] = list(migrated["favorite_devices"])
            migrated["favorite_devices"] = [str(f) for f in migrated["favorite_devices"]]

        migrated["schema_version"] = 1
        return migrated

    def _defaults(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "username": "",
            "email": "",
            "client_id": "",
            "client_secret": "",
            "access_token": "",
            "refresh_token": "",
            "delegation_token": "",
            "session_token": "",
            "active_homey_id": "",
            "active_homey_name": "",
            "direct_base_url": "",
            "connection_mode": "auto",  # 'auto', 'local_secure', 'local', 'remote'
            "verify_ssl": True,
            "favorite_devices": [],
            "cached_homeys": [],
        }

    def load_from_env(self, override: bool = False, persist: bool = False) -> None:
        """
        Populates settings from environment variables if present.
        Supports standard HomePort environment variable names.
        """
        mapping = {
            "HOMEY_BASE_URL": "direct_base_url",
            "HOMEY_SESSION_TOKEN": "session_token",
            "HOMEY_API_KEY": "session_token",
            "HOMEY_CLIENT_ID": "client_id",
            "HOMEY_CLIENT_SECRET": "client_secret",
            "HOMEY_ACCESS_TOKEN": "access_token",
            "HOMEY_REFRESH_TOKEN": "refresh_token",
            "HOMEY_DELEGATION_TOKEN": "delegation_token",
            "HOMEY_USERNAME": "username",
            "HOMEY_EMAIL": "email",
            "HOMEY_CONNECTION_MODE": "connection_mode",
        }
        modified = False
        for env_key, setting_key in mapping.items():
            val = os.environ.get(env_key)
            if val is not None and val != "":
                if override or not self._data.get(setting_key):
                    self._data[setting_key] = val
                    modified = True

        if "HOMEY_VERIFY_SSL" in os.environ:
            val_ssl = os.environ["HOMEY_VERIFY_SSL"].strip().lower()
            bool_ssl = val_ssl not in ("0", "false", "no", "off")
            self._data["verify_ssl"] = bool_ssl
            modified = True

        if modified and persist:
            self.save()

    def save(self) -> None:
        """
        Saves current settings and tokens to disk atomically with strict 0600 permissions.
        """
        try:
            self._ensure_secure_dir()
            self._data["schema_version"] = self.SCHEMA_VERSION
            data_str = json.dumps(self._data, indent=2)

            # Atomic write via temporary file in the same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(self.base_dir),
                prefix="settings_",
                suffix=".tmp",
            )
            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                    f.write(data_str)
                    f.flush()
                    os.fsync(f.fileno())
                try:
                    os.chmod(temp_path, 0o600)
                except Exception:
                    pass
                os.replace(temp_path, str(self.file_path))
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                raise

            # Ensure final permissions are 0600 (owner read/write only)
            if self.file_path.exists():
                try:
                    os.chmod(self.file_path, 0o600)
                except Exception:
                    pass
        except Exception as e:
            logger.error("Failed to save settings to %s: %s; attempting direct fallback write", self.file_path, e)
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(self._data, indent=2))
                try:
                    os.chmod(self.file_path, 0o600)
                except Exception:
                    pass
            except Exception as fallback_e:
                logger.error("Fallback write also failed for %s: %s", self.file_path, fallback_e)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, mapping: Dict[str, Any]) -> None:
        self._data.update(mapping)
        self.save()

    def get_all_settings(self) -> Dict[str, Any]:
        """Returns all configuration and credential entries."""
        return dict(self._data)

    def clear_tokens(self) -> None:
        """Clears all session and authentication tokens securely."""
        self._data["access_token"] = ""
        self._data["refresh_token"] = ""
        self._data["delegation_token"] = ""
        self._data["session_token"] = ""
        self.save()

    def get_auth_tokens(self) -> AuthTokens:
        return AuthTokens(
            access_token=self._data.get("access_token") or None,
            refresh_token=self._data.get("refresh_token") or None,
            delegation_token=self._data.get("delegation_token") or None,
            session_token=self._data.get("session_token") or None,
            homey_id=self._data.get("active_homey_id") or None,
            direct_base_url=self._data.get("direct_base_url") or None,
        )

    def save_auth_tokens(self, tokens: AuthTokens) -> None:
        if tokens.access_token is not None:
            self._data["access_token"] = tokens.access_token
        if tokens.refresh_token is not None:
            self._data["refresh_token"] = tokens.refresh_token
        if tokens.delegation_token is not None:
            self._data["delegation_token"] = tokens.delegation_token
        if tokens.session_token is not None:
            self._data["session_token"] = tokens.session_token
        if tokens.homey_id is not None:
            self._data["active_homey_id"] = tokens.homey_id
        if tokens.direct_base_url is not None:
            self._data["direct_base_url"] = tokens.direct_base_url
        self.save()

    def get_cached_homeys(self) -> List[HomeyInfo]:
        raw = self._data.get("cached_homeys", [])
        return [HomeyInfo.from_dict(h) for h in raw if isinstance(h, dict)]

    def set_cached_homeys(self, homeys: List[HomeyInfo]) -> None:
        self._data["cached_homeys"] = [h.to_dict() for h in homeys]
        self.save()

    def get_favorite_devices(self) -> List[str]:
        """Returns the list of favorite device IDs."""
        return list(self._data.get("favorite_devices", []))

    def is_favorite(self, device_id: str) -> bool:
        """Checks if a device ID is marked as favorite."""
        favs = self._data.get("favorite_devices", [])
        return str(device_id) in favs

    def set_favorite(self, device_id: str, is_fav: bool) -> bool:
        """Sets favorite status for a device ID and saves to disk."""
        favs = list(self._data.get("favorite_devices", []))
        did = str(device_id)
        if is_fav and did not in favs:
            favs.append(did)
        elif not is_fav and did in favs:
            favs = [f for f in favs if f != did]
        self._data["favorite_devices"] = favs
        self.save()
        return is_fav

    def toggle_favorite(self, device_id: str) -> bool:
        """Toggles favorite status for a device ID and saves to disk."""
        favs = list(self._data.get("favorite_devices", []))
        did = str(device_id)
        if did in favs:
            favs = [f for f in favs if f != did]
            is_fav = False
        else:
            favs.append(did)
            is_fav = True
        self._data["favorite_devices"] = favs
        self.save()
        return is_fav

    def save_favorites(self, favorites: List[str]) -> None:
        """Saves an entire list of favorite device IDs to disk."""
        self._data["favorite_devices"] = [str(f) for f in favorites]
        self.save()
