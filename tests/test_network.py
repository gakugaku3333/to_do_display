from __future__ import annotations

import subprocess
from unittest.mock import patch

from app import network


def test_mdns_hostname_uses_local_hostname():
    done = subprocess.CompletedProcess([], 0, stdout="mac-mini\n")
    with patch("subprocess.run", return_value=done):
        assert network.mdns_hostname() == "mac-mini.local"


def test_mdns_hostname_falls_back_to_gethostname():
    with patch("subprocess.run", side_effect=FileNotFoundError), \
         patch("socket.gethostname", return_value="mac-mini.local"):
        assert network.mdns_hostname() == "mac-mini.local"


def test_access_urls_puts_mdns_first():
    with patch.object(network, "mdns_hostname", return_value="mac-mini.local"), \
         patch.object(network, "local_ip", return_value="192.168.1.20"):
        assert network.access_urls(8080) == [
            "http://mac-mini.local:8080",
            "http://192.168.1.20:8080",
        ]
