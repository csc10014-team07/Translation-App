"""Startup script orchestrating FastAPI backend, Cloudflare Tunnel, and Mobile config.

Features:
- Probes local environment and hardware capabilities.
- Automatically acquires `cloudflared` binary if not installed.
- Launches FastAPI Uvicorn server on port 8000.
- Launches Cloudflare Quick Tunnel to expose port 8000 over public HTTPS/WSS.
- Automatically updates `Translation-App/mobile/src/config/api.ts`.
- Displays connection URLs, QR instructions, and handles clean Ctrl+C shutdown.
"""
import argparse
import platform
import re
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.request
from collections.abc import Iterable
from pathlib import Path

# Fix Windows console UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_ROOT = BACKEND_DIR.parent
DEFAULT_MOBILE_CONFIG = APP_ROOT / "mobile" / "src" / "config" / "api.ts"
TOOLS_DIR = (APP_ROOT.parent / "tools") if (APP_ROOT.parent / "tools").exists() else (APP_ROOT / "tools")

TUNNEL_REGEX = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


def get_cloudflared_download_info() -> tuple[str, str]:
    """Return (download_url, binary_filename) according to current OS platform."""
    if sys.platform.startswith("win"):
        return (
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
            "cloudflared.exe",
        )
    elif sys.platform.startswith("darwin"):
        machine = platform.machine().lower()
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        return (
            f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-{arch}.tgz",
            "cloudflared",
        )
    else:  # Linux / Google Colab
        return (
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
            "cloudflared",
        )


def get_local_ip() -> str:
    """Detect machine's local IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def extract_tunnel_url(log_lines: Iterable[str]) -> str | None:
    """Extract public trycloudflare.com URL from output lines."""
    for line in log_lines:
        match = TUNNEL_REGEX.search(line)
        if match:
            return match.group(0)
    return None


def ensure_cloudflared() -> Path | None:
    """Ensure cloudflared executable is available across platforms."""
    # 1. Check in PATH
    import shutil
    path_in_env = shutil.which("cloudflared")
    if path_in_env:
        return Path(path_in_env)

    # 2. Check in tools/ directory
    download_url, bin_name = get_cloudflared_download_info()
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    local_binary = TOOLS_DIR / bin_name
    if local_binary.exists() and local_binary.stat().st_size > 1_000_000:
        # A previous broken macOS run may have left the raw .tgz in place.
        try:
            with local_binary.open("rb") as fh:
                is_compressed_archive = fh.read(2) == b"\x1f\x8b"
        except OSError:
            return local_binary
        if not is_compressed_archive:
            return local_binary

    # 3. Download official binary
    print(f"📥 Downloading cloudflared for {sys.platform} from GitHub releases...")
    print(f"   Destination: {local_binary}")

    def _progress(count: int, block_size: int, total_size: int) -> None:
        percent = int(count * block_size * 100 / total_size) if total_size > 0 else 0
        sys.stdout.write(f"\r   Progress: {percent}% ({count * block_size // 1048576}MB / {total_size // 1048576}MB)")
        sys.stdout.flush()

    try:
        if download_url.endswith(".tgz"):
            with tempfile.TemporaryDirectory() as tmp_dir:
                archive_path = Path(tmp_dir) / "cloudflared.tgz"
                urllib.request.urlretrieve(
                    download_url, str(archive_path), reporthook=_progress
                )
                with tarfile.open(archive_path, "r:gz") as archive:
                    member = next(
                        (
                            item
                            for item in archive.getmembers()
                            if Path(item.name).name == bin_name and item.isfile()
                        ),
                        None,
                    )
                    if member is None:
                        raise RuntimeError(f"{bin_name} not found in downloaded archive")
                    source = archive.extractfile(member)
                    if source is None:
                        raise RuntimeError(f"Could not read {bin_name} from archive")
                    with local_binary.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
        else:
            urllib.request.urlretrieve(download_url, str(local_binary), reporthook=_progress)
        if not sys.platform.startswith("win"):
            import stat
            local_binary.chmod(local_binary.stat().st_mode | stat.S_IEXEC)
        print("\n✅ Download completed.")
        return local_binary
    except Exception as exc:
        print(f"\n⚠️  Could not download cloudflared: {exc}")
        print("   Falling back to Local LAN mode.")
        return None


def update_mobile_config(base_url: str, config_path: Path | None = None) -> Path:
    """Update mobile/src/config/api.ts with active base URL and derived WebSocket URL."""
    target = config_path or DEFAULT_MOBILE_CONFIG
    target.parent.mkdir(parents=True, exist_ok=True)
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    content = f"""// Auto-generated by start_tunnel_and_server.py
// Connected to AI Inference Host
export const API_BASE_URL = '{base_url}';
export const WS_BASE_URL = '{ws_url}/ws/stream';
"""
    target.write_text(content, encoding="utf-8")
    print(f"📱 Updated mobile config ({target.name}): {base_url}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Start Translation App Server & Remote Tunnel")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind FastAPI server")
    parser.add_argument("--local-only", action="store_true", help="Run local LAN only without Cloudflare Tunnel")
    parser.add_argument("--tunnel-url", type=str, default=None, help="Use existing custom tunnel URL")
    args = parser.parse_args()

    local_ip = get_local_ip()
    port = args.port

    print("=" * 80)
    print("🚀 STARTING TRANSLATION APP INFERENCE BACKEND")
    print("=" * 80)
    print(f"🖥️  Host Machine : {socket.gethostname()} ({local_ip})")
    print(f"⚙️  Port         : {port}")

    # 1. Start Uvicorn process
    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]

    print(f"\n⏳ Starting FastAPI server on port {port}...")
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # Continuously drain server stdout to prevent pipe buffer deadlocks on Windows (4KB default)
    server_logs: list[str] = []

    def _drain_stream(stream, log_list: list[str]) -> None:
        try:
            if stream is not None:
                for line in iter(stream.readline, ""):
                    log_list.append(line)
        except Exception:
            pass

    threading.Thread(
        target=_drain_stream,
        args=(server_proc.stdout, server_logs),
        daemon=True,
    ).start()

    # Wait for server to become responsive
    healthy = False
    for _ in range(30):
        time.sleep(1.0)
        if server_proc.poll() is not None:
            print(f"❌ FastAPI server process exited unexpectedly with code {server_proc.returncode}.")
            if server_logs:
                print("\n--- Recent Server Logs ---")
                print("".join(server_logs[-30:]))
            sys.exit(1)

        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    healthy = True
                    break
        except Exception:
            pass

    if not healthy:
        print("❌ FastAPI server failed to start within 30 seconds.")
        if server_logs:
            print("\n--- Recent Server Logs ---")
            print("".join(server_logs[-30:]))
        server_proc.kill()
        sys.exit(1)

    print("✅ FastAPI backend is healthy and responding.")

    tunnel_url = args.tunnel_url
    tunnel_proc = None

    if not args.local_only and not tunnel_url:
        cf_bin = ensure_cloudflared()
        if cf_bin and cf_bin.exists():
            print(f"\n🌐 Establishing Cloudflare Quick Tunnel to http://localhost:{port}...")
            tunnel_cmd = [str(cf_bin), "tunnel", "--url", f"http://localhost:{port}"]
            try:
                tunnel_proc = subprocess.Popen(
                    tunnel_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError as exc:
                print(f"⚠️  Could not start cloudflared: {exc}")
                print("   Falling back to Local LAN mode.")
                tunnel_proc = None

            if tunnel_proc is not None and tunnel_proc.stdout is not None:
                # Monitor tunnel output for generated URL
                start_t = time.time()
                collected_lines: list[str] = []
                while time.time() - start_t < 25:
                    if tunnel_proc.poll() is not None:
                        print("⚠️  Cloudflare tunnel process terminated prematurely.")
                        break
                    line = tunnel_proc.stdout.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    collected_lines.append(line)
                    found = extract_tunnel_url([line])
                    if found:
                        tunnel_url = found
                        break

                # Continue draining tunnel output in background so pipe buffer never fills
                threading.Thread(
                    target=_drain_stream,
                    args=(tunnel_proc.stdout, collected_lines),
                    daemon=True,
                ).start()

                if not tunnel_url:
                    print("⚠️  Cloudflare tunnel URL not detected within timeout. Falling back to local LAN.")

    active_url = tunnel_url or f"http://{local_ip}:{port}"
    update_mobile_config(active_url)

    print("\n" + "=" * 80)
    print("🎉 TRANSLATION APP INFERENCE HOST IS LIVE!")
    print("=" * 80)
    print(f"📍 Localhost Endpoint  : http://localhost:{port}")
    print(f"🏠 Local LAN Endpoint  : http://{local_ip}:{port}")
    if tunnel_url:
        print(f"🌐 Cloudflare Tunnel   : {tunnel_url}")
        print(f"⚡ Streaming WebSocket : {tunnel_url.replace('https://', 'wss://')}/ws/stream")
        print(f"📖 Interactive Swagger : {tunnel_url}/docs")
    else:
        print(f"⚡ Streaming WebSocket : ws://{local_ip}:{port}/ws/stream")
        print(f"📖 Interactive Swagger : http://{local_ip}:{port}/docs")

    print("\n📲 TO CONNECT MOBILE APP (Expo):")
    print("   1. In a separate terminal run:")
    print("      cd Translation-App/mobile")
    print("      npm install   # (first time only)")
    print("      npx expo start")
    print("   2. Scan the generated QR code with your smartphone (Expo Go).")
    print("=" * 80)
    print("Press Ctrl+C to stop both Server and Tunnel.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server and tunnel...")
        if tunnel_proc:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=3)
        if server_proc:
            server_proc.terminate()
            server_proc.wait(timeout=3)
        print("✅ Shutdown complete.")


if __name__ == "__main__":
    main()
