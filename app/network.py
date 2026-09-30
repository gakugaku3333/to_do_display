from __future__ import annotations

"""LAN 内でこのサーバーに到達するためのアドレス情報。

Mac mini の IP は DHCP で変わりうるため、端末には IP ではなく
Bonjour 名（例: mac-mini.local）で接続させるのが基本方針。
"""

import socket
import subprocess


def local_ip() -> str:
    """LAN 側の自分の IP を検出する（UDP connect はパケットを送信しない）。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def mdns_hostname() -> str:
    """Bonjour で公開されている `<名前>.local` を返す。

    macOS は「システム設定 > 一般 > 共有 > ローカルホスト名」を自動で
    mDNS 公開しているので、サーバー側で追加の設定は要らない。
    """
    try:
        name = subprocess.run(
            ["scutil", "--get", "LocalHostName"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        name = socket.gethostname().removesuffix(".local")
    return f"{name}.local"


def access_urls(port: int) -> list[str]:
    """端末に案内する URL（推奨の .local 名を先頭に）。"""
    urls = [f"http://{mdns_hostname()}:{port}"]
    try:
        urls.append(f"http://{local_ip()}:{port}")
    except OSError:
        pass
    return urls
