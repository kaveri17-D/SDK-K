import ipaddress
import logging
from datetime import datetime, timezone
from fastapi import Request
from backend.app.core.config import settings

logger = logging.getLogger("clipper-x.service.ip")


class IPService:
    @staticmethod
    def is_ip_in_network(ip_str: str, network_or_ip: str) -> bool:
        """Checks if an IP matches a single IP or CIDR network block."""
        try:
            target_ip = ipaddress.ip_address(ip_str)
            network = ipaddress.ip_network(network_or_ip, strict=False)
            return target_ip in network
        except ValueError:
            return False

    @classmethod
    def is_trusted_proxy(cls, client_ip: str) -> bool:
        """
        Determines if the direct incoming connection IP is in the configured trusted proxies list.
        """
        if not client_ip:
            return False

        for trusted in settings.trusted_proxies_list:
            if cls.is_ip_in_network(client_ip, trusted):
                return True
        return False

    @classmethod
    def get_observed_public_ip(cls, request: Request) -> str:
        """
        Securely extracts the observed egress IP from the incoming request.
        Does NOT blindly trust arbitrary X-Forwarded-For headers unless the direct peer
        is an authorized trusted reverse-proxy.
        """
        direct_ip = request.client.host if request.client else "127.0.0.1"

        # If direct client is NOT a trusted proxy, return direct IP directly.
        if not cls.is_trusted_proxy(direct_ip):
            return direct_ip

        # Direct peer is a trusted proxy. Inspect X-Forwarded-For safely.
        xff_header = request.headers.get("X-Forwarded-For")
        if not xff_header:
            return direct_ip

        # Parse comma-separated IPs from right to left
        forwarded_ips = [ip.strip() for ip in xff_header.split(",") if ip.strip()]
        if not forwarded_ips:
            return direct_ip

        # Walk backward from the last hop, looking for the first untrusted IP
        for ip in reversed(forwarded_ips):
            if not cls.is_trusted_proxy(ip):
                return ip

        # If all hops in XFF are in trusted proxy range, return the leftmost client IP
        return forwarded_ips[0]

    @classmethod
    def get_ip_response(cls, request: Request) -> dict:
        ip = cls.get_observed_public_ip(request)
        return {
            "ip": ip,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
