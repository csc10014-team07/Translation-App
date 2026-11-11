"""Tests for Cloudflare tunnel orchestration and mobile client config generation.

Seam: Tunnel launcher and mobile configuration interface.
"""
import io
import re
import tarfile
from pathlib import Path

from scripts.start_tunnel_and_server import (
    ensure_cloudflared,
    extract_tunnel_url,
    get_cloudflared_download_info,
    get_local_ip,
    update_mobile_config,
)


def test_get_local_ip_returns_valid_ipv4():
    """Verify get_local_ip returns an IPv4 address formatted as X.X.X.X."""
    ip = get_local_ip()
    assert isinstance(ip, str)
    # Check valid IPv4 format
    pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    assert re.match(pattern, ip) is not None
    octets = [int(p) for p in ip.split(".")]
    assert all(0 <= octet <= 255 for octet in octets)


def test_extract_tunnel_url_success():
    """Verify regex correctly parses Cloudflare quick tunnel URLs from log output."""
    sample_logs = [
        "2026-10-27T12:00:00Z INF Starting tunnel",
        "2026-10-27T12:00:01Z INF Requesting quick tunnel",
        "2026-10-27T12:00:03Z INF +--------------------------------------------------------------------------------------------+",
        "2026-10-27T12:00:03Z INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |",
        "2026-10-27T12:00:03Z INF |  https://fuzzy-monkey-jumping.trycloudflare.com                                             |",
        "2026-10-27T12:00:03Z INF +--------------------------------------------------------------------------------------------+",
    ]
    url = extract_tunnel_url(sample_logs)
    assert url == "https://fuzzy-monkey-jumping.trycloudflare.com"


def test_extract_tunnel_url_none_found():
    """Verify extract_tunnel_url returns None when no trycloudflare URL appears."""
    sample_logs = [
        "2026-10-27T12:00:00Z INF Starting tunnel",
        "2026-10-27T12:00:01Z ERR Connection timed out",
    ]
    url = extract_tunnel_url(sample_logs)
    assert url is None


def test_update_mobile_config_cloudflare_https(tmp_path: Path):
    """Verify update_mobile_config generates valid TypeScript config with HTTPS and WSS."""
    target_config = tmp_path / "api.ts"
    tunnel_url = "https://silent-galaxy-explore.trycloudflare.com"
    
    update_mobile_config(tunnel_url, config_path=target_config)
    
    assert target_config.exists()
    content = target_config.read_text(encoding="utf-8")
    assert f"export const API_BASE_URL = '{tunnel_url}';" in content
    assert "export const WS_BASE_URL = 'wss://silent-galaxy-explore.trycloudflare.com/ws/stream';" in content


def test_update_mobile_config_local_http(tmp_path: Path):
    """Verify update_mobile_config generates valid TypeScript config for local LAN HTTP."""
    target_config = tmp_path / "api.ts"
    local_url = "http://192.168.1.150:8000"
    
    update_mobile_config(local_url, config_path=target_config)
    
    assert target_config.exists()
    content = target_config.read_text(encoding="utf-8")
    assert f"export const API_BASE_URL = '{local_url}';" in content
    assert "export const WS_BASE_URL = 'ws://192.168.1.150:8000/ws/stream';" in content


def test_get_cloudflared_download_info_macos_arm64(monkeypatch):
    """macOS arm64 downloads the matching .tgz archive."""
    import scripts.start_tunnel_and_server as launcher

    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher.platform, "machine", lambda: "arm64")

    url, bin_name = get_cloudflared_download_info()
    assert url.endswith("cloudflared-darwin-arm64.tgz")
    assert bin_name == "cloudflared"


def test_ensure_cloudflared_extracts_macos_tgz(tmp_path: Path, monkeypatch):
    """A macOS .tgz download must be unpacked to an executable, not chmod'd raw."""
    import shutil as shutil_mod

    import scripts.start_tunnel_and_server as launcher

    binary_payload = b"#!/bin/sh\necho cloudflared\n"

    monkeypatch.setattr(launcher, "TOOLS_DIR", tmp_path)
    monkeypatch.setattr(
        launcher,
        "get_cloudflared_download_info",
        lambda: (
            "https://example.com/cloudflared-darwin-arm64.tgz",
            "cloudflared",
        ),
    )
    monkeypatch.setattr(shutil_mod, "which", lambda _name: None)

    def _fake_urlretrieve(url: str, filename: str, reporthook=None):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            info = tarfile.TarInfo("cloudflared")
            info.size = len(binary_payload)
            archive.addfile(info, io.BytesIO(binary_payload))
        Path(filename).write_bytes(buffer.getvalue())
        return filename, None

    monkeypatch.setattr(launcher.urllib.request, "urlretrieve", _fake_urlretrieve)

    result = ensure_cloudflared()

    assert result == tmp_path / "cloudflared"
    assert result is not None
    assert result.read_bytes() == binary_payload
    assert result.stat().st_mode & 0o111, "Extracted cloudflared must be executable"
