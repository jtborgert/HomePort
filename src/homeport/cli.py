"""Command-line interface for HomePort."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from typing import List, Optional

from .api import HomeyClient
from .models import AuthTokens, HomeyInfo
from .socket import HomeyRealtimeClient
from .storage import SettingsStorage, load_env


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_status(args: argparse.Namespace, storage: SettingsStorage) -> int:
    tokens = storage.get_auth_tokens()
    print("=== HomePort Status ===")
    print(f"Direct Base URL   : {storage.get('direct_base_url') or '(None)'}")
    print(f"Active Homey ID   : {storage.get('active_homey_id') or '(None)'}")
    print(f"Active Homey Name : {storage.get('active_homey_name') or '(None)'}")
    print(f"Connection Mode   : {storage.get('connection_mode')}")
    print(f"Session Token Set : {'Yes' if tokens.session_token else 'No'}")
    print(f"Access Token Set  : {'Yes' if tokens.access_token else 'No'}")

    cached_homeys = storage.get_cached_homeys()
    if cached_homeys:
        print(f"\nDiscovered Homeys ({len(cached_homeys)}):")
        for h in cached_homeys:
            print(f" - [{h.id}] {h.name} (Platform: {h.platform})")
            print(f"     Local Secure: {h.local_url_secure}")
            print(f"     Local       : {h.local_url}")
            print(f"     Remote      : {h.remote_url}")
    return 0


def cmd_login(args: argparse.Namespace, storage: SettingsStorage) -> int:
    client = HomeyClient(
        base_url=args.url,
        session_token=args.token,
        verify_ssl=not args.insecure,
    )
    try:
        sys_info = client.get_system_info()
        homey_name = sys_info.get("name") or "Homey Pro"
        storage.set("direct_base_url", args.url.rstrip("/"))
        storage.set("session_token", args.token)
        storage.set("active_homey_name", homey_name)
        storage.set("verify_ssl", not args.insecure)
        storage.save()
        print(f"Successfully logged in to {homey_name} ({args.url})!")
        return 0
    except Exception as e:
        print(f"Error logging in to Homey Pro: {e}", file=sys.stderr)
        return 1


def cmd_devices(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    if not base_url or not token:
        print("Error: No active Homey connection configured. Run 'homeport login' first.", file=sys.stderr)
        return 1

    client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
    try:
        devices = client.get_devices()
        print(f"=== Devices ({len(devices)}) ===")
        for d in devices.values():
            onoff_str = f" [ON]" if d.onoff is True else (f" [OFF]" if d.onoff is False else "")
            dim_str = f" (Dim: {int(d.dim * 100)}%)" if d.dim is not None else ""
            zone_str = f" in {d.zone_name}" if d.zone_name else ""
            fav_str = " ★" if storage.is_favorite(d.id) else ""
            print(f"• [{d.id}] {d.name} ({d.class_name}){zone_str}{onoff_str}{dim_str}{fav_str}")
            if args.verbose:
                print(f"    Capabilities: {', '.join(d.capabilities)}")
                print(f"    State: {json.dumps(d.state)}")
        return 0
    except Exception as e:
        print(f"Error fetching devices: {e}", file=sys.stderr)
        return 1


def cmd_toggle(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    if not base_url or not token:
        print("Error: No active Homey connection. Run 'homeport login' first.", file=sys.stderr)
        return 1

    client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
    try:
        dev = client.get_device(args.device_id)
        current = bool(dev.onoff)
        new_val = not current
        client.set_device_capability(args.device_id, "onoff", new_val)
        print(f"Toggled device '{dev.name}' ({dev.id}) to {'ON' if new_val else 'OFF'}.")
        return 0
    except Exception as e:
        print(f"Error toggling device: {e}", file=sys.stderr)
        return 1


def cmd_set_cap(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    if not base_url or not token:
        print("Error: No active Homey connection. Run 'homeport login' first.", file=sys.stderr)
        return 1

    # Parse value as json/bool/float/int if possible
    val_raw = args.value
    val: Any = val_raw
    if val_raw.lower() in ("true", "yes", "on"):
        val = True
    elif val_raw.lower() in ("false", "no", "off"):
        val = False
    else:
        try:
            val = float(val_raw) if "." in val_raw else int(val_raw)
        except ValueError:
            pass

    client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
    try:
        client.set_device_capability(args.device_id, args.capability_id, val)
        print(f"Set capability '{args.capability_id}' on device '{args.device_id}' to {val}.")
        return 0
    except Exception as e:
        print(f"Error setting capability: {e}", file=sys.stderr)
        return 1


def cmd_flows(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    if not base_url or not token:
        print("Error: No active Homey connection. Run 'homeport login' first.", file=sys.stderr)
        return 1

    client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
    try:
        flows = client.get_flows()
        print(f"=== Flows ({len(flows)}) ===")
        for f in flows.values():
            status = "Enabled" if f.enabled else "Disabled"
            trig = "Triggerable" if f.triggerable else "Not Triggerable"
            print(f"• [{f.id}] {f.name} ({status}, {trig})")
        return 0
    except Exception as e:
        print(f"Error fetching flows: {e}", file=sys.stderr)
        return 1


def cmd_trigger_flow(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    if not base_url or not token:
        print("Error: No active Homey connection. Run 'homeport login' first.", file=sys.stderr)
        return 1

    client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
    try:
        client.trigger_flow(args.flow_id)
        print(f"Successfully triggered flow '{args.flow_id}'.")
        return 0
    except Exception as e:
        print(f"Error triggering flow: {e}", file=sys.stderr)
        return 1


def cmd_listen(args: argparse.Namespace, storage: SettingsStorage) -> int:
    base_url = storage.get("direct_base_url")
    token = storage.get("session_token")
    homey_id = storage.get("active_homey_id", "")
    if not base_url or not token:
        print("Error: No active Homey connection. Run 'homeport login' first.", file=sys.stderr)
        return 1

    print(f"Connecting to Homey Socket.IO stream on {base_url}...")

    def on_event(uri: str, event_type: str, data: Any) -> None:
        print(f"\n[EVENT] URI: {uri} | Type: {event_type}")
        print(f"Payload: {json.dumps(data, indent=2)}")

    client = HomeyRealtimeClient(
        base_url=base_url,
        session_token=token,
        homey_id=homey_id,
        on_event=on_event,
        verify_ssl=storage.get("verify_ssl", True),
    )
    client.start()
    client.subscribe("homey:manager:flow")
    client.subscribe("homey:manager:devices")

    # Subscribe to devices
    try:
        http_client = HomeyClient(base_url=base_url, session_token=token, verify_ssl=storage.get("verify_ssl", True))
        devices = http_client.get_devices()
        for did in devices:
            client.subscribe(f"homey:device:{did}")
        print(f"Subscribed to {len(devices)} device streams and flow manager. Press Ctrl+C to exit.")
    except Exception as e:
        print(f"Warning: could not subscribe to all devices: {e}")

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping...")
        client.stop()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HomePort - Sailfish OS Homey Pro Client CLI")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    subparsers.add_parser("status", help="Show current connection status and discovered Homeys")

    # login
    login_parser = subparsers.add_parser("login", help="Configure direct Homey connection")
    login_parser.add_argument("--url", required=True, help="Homey URL (e.g. http://192.168.1.50 or https://...homeypro.net)")
    login_parser.add_argument("--token", required=True, help="Homey session token or API key")
    login_parser.add_argument("--insecure", action="store_true", help="Disable SSL certificate verification")

    # devices
    subparsers.add_parser("devices", help="List all Homey devices")

    # toggle
    toggle_parser = subparsers.add_parser("toggle", help="Toggle a device on/off")
    toggle_parser.add_argument("device_id", help="Homey Device ID")

    # set-capability
    set_cap_parser = subparsers.add_parser("set-capability", help="Set a device capability value")
    set_cap_parser.add_argument("device_id", help="Homey Device ID")
    set_cap_parser.add_argument("capability_id", help="Capability ID (e.g. onoff, dim, target_temperature)")
    set_cap_parser.add_argument("value", help="Value to set")

    # flows
    subparsers.add_parser("flows", help="List all Homey flows")

    # trigger-flow
    trigger_parser = subparsers.add_parser("trigger-flow", help="Trigger a flow")
    trigger_parser.add_argument("flow_id", help="Flow ID to trigger")

    # listen
    subparsers.add_parser("listen", help="Stream real-time events over Socket.IO")

    args = parser.parse_args(argv)
    load_env()
    setup_logging(args.verbose)
    storage = SettingsStorage()

    if args.command == "status":
        return cmd_status(args, storage)
    elif args.command == "login":
        return cmd_login(args, storage)
    elif args.command == "devices":
        return cmd_devices(args, storage)
    elif args.command == "toggle":
        return cmd_toggle(args, storage)
    elif args.command == "set-capability":
        return cmd_set_cap(args, storage)
    elif args.command == "flows":
        return cmd_flows(args, storage)
    elif args.command == "trigger-flow":
        return cmd_trigger_flow(args, storage)
    elif args.command == "listen":
        return cmd_listen(args, storage)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
