#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Machine Charm for Magma's Access Gateway."""

import ipaddress
import json
import logging
import subprocess
from typing import List

import netifaces  # type: ignore[import]
from ops.charm import CharmBase, InstallEvent, StartEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

logger = logging.getLogger(__name__)


class MagmaAccessGatewayOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Observes juju events."""
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.start, self._on_start)

    def _on_install(self, event: InstallEvent) -> None:
        """Triggered on install event.

        Args:
            event: Juju event

        Returns:
            None
        """
        self.unit.status = MaintenanceStatus("Installing AGW Snap")
        self.install_magma_access_gateway_snap()
        if not self._is_configuration_valid():
            self.unit.status = BlockedStatus("Configuration is invalid. Check logs for details")
            event.defer()
            return
        self.unit.status = MaintenanceStatus("Installing AGW")
        self.install_magma_access_gateway()

    def _on_start(self, event: StartEvent):
        """Truggered on start event.

        Args:
            event: Juju event

        Returns:
            None
        """
        magma_service = subprocess.run(
            ["systemctl", "is-active", "magma@magmad"],
            stdout=subprocess.PIPE,
        )
        if magma_service.returncode != 0:
            event.defer()
            return
        self.unit.status = ActiveStatus()

    @staticmethod
    def install_magma_access_gateway_snap() -> None:
        """Installs Magma Access Gateway snap.

        Returns:
            None
        """
        subprocess.run(
            ["snap", "install", "magma-access-gateway", "--classic", "--edge"],
            stdout=subprocess.PIPE,
        )

    def install_magma_access_gateway(self) -> None:
        """Installs Magma access gateway on the host.

        Returns:
            None
        """
        command = ["magma-access-gateway.install"]
        command.extend(self._install_arguments)
        subprocess.run(
            command,
            stdout=subprocess.PIPE,
        )

    @staticmethod
    def configure_magma_access_gateway(orc8r_domain: str, root_ca_path: str) -> None:
        """Configures Magma Access Gateway to connect to an Orchestrator.

        Args:
            orc8r_domain (str): Orchestrator domain.
            root_ca_path (str): Path to Orchestrator root CA certificate.

        Returns:
            None
        """
        subprocess.run(
            [
                "magma-access-gateway.configure",
                "--domain",
                orc8r_domain,
                "--root-ca-pem-path",
                root_ca_path,
            ],
            stdout=subprocess.PIPE,
        )

    def _is_configuration_valid(self) -> bool:
        """Validates configuration."""
        if self.model.config["skip-networking"]:
            return True
        valid = self._is_valid_interface("sgi", "eth0")
        if not self._is_valid_interface("s1", "eth1"):
            valid = False
        if not self._is_valid_interface_addressing_configuration("sgi"):
            valid = False
        if not self._are_valid_dns(self.model.config["dns"]):
            logger.warning("Invalid DNS configuration")
            valid = False
        return valid

    def _is_valid_interface(self, interface_name: str, new_interface_name: str) -> bool:
        """Validates a network interface name."""
        interface = self.model.config.get(interface_name)
        if not interface:
            logger.warning("%s interface name is required", (interface_name))
            return False
        if (
            interface not in netifaces.interfaces()
            and new_interface_name not in netifaces.interfaces()  # noqa: W503
        ):
            logger.warning("%s interface not found", (interface))
            return False
        return True

    def _is_valid_interface_addressing_configuration(self, interface: str) -> bool:
        """Validates sgi interface configuration."""
        ipv4_address = self.model.config.get(f"{interface}-ipv4-address")
        ipv4_gateway = self.model.config.get(f"{interface}-ipv4-gateway")
        ipv6_address = self.model.config.get(f"{interface}-ipv6-address")
        ipv6_gateway = self.model.config.get(f"{interface}-ipv6-gateway")
        if not ipv4_address and not ipv4_gateway and not ipv6_address and not ipv6_gateway:
            return True
        if any([ipv4_address, ipv4_gateway]) and not all([ipv4_address, ipv4_gateway]):
            logger.warning("Both IPv4 address and gateway required for interface %s", (interface))
            return False
        if any([ipv6_address, ipv6_gateway]) and not all([ipv6_address, ipv6_gateway]):
            logger.warning("Both IPv6 address and gateway required for interface %s", (interface))
            return False
        if ipv6_address and not ipv4_address:
            logger.warning(
                "Pure IPv6 configuration is not supported for interface %s", (interface)
            )
            return False
        if ipv4_address and not self._is_valid_ipv4_address(ipv4_address):
            logger.warning("Invalid IPv4 address and netmask for interface %s", (interface))
            return False
        if ipv4_gateway and not self._is_valid_ipv4_gateway(ipv4_gateway):
            logger.warning("Invalid IPv4 gateway for interface %s", (interface))
            return False
        if ipv6_address and not self._is_valid_ipv6_address(ipv6_address):
            logger.warning("Invalid IPv6 address and netmask for interface %s", (interface))
            return False
        if ipv6_gateway and not self._is_valid_ipv6_gateway(ipv6_gateway):
            logger.warning("Invalid IPv6 gateway for interface %s", (interface))
            return False
        return True

    def _is_valid_ipv4_address(self, ipv4_address: str) -> bool:
        """Validate an IPv4 address and netmask.

        A valid string will have the form:
        a.b.c.d/x
        """
        try:
            ip = ipaddress.ip_network(ipv4_address, strict=False)
            return isinstance(ip, ipaddress.IPv4Network)
        except ValueError:
            return False

    def _is_valid_ipv4_gateway(self, ipv4_gateway: str) -> bool:
        """Validate an IPv4 gateway.

        A valid string will have the form:
        a.b.c.d
        """
        try:
            ip = ipaddress.ip_address(ipv4_gateway)
            return isinstance(ip, ipaddress.IPv4Address)
        except ValueError:
            return False

    def _is_valid_ipv6_address(self, ipv6_address: str) -> bool:
        """Validate an IPv6 address and netmask."""
        try:
            ip = ipaddress.ip_network(ipv6_address, strict=False)
            return isinstance(ip, ipaddress.IPv6Network)
        except ValueError:
            return False

    def _is_valid_ipv6_gateway(self, ipv6_gateway: str) -> bool:
        """Validate an IPv6 gateway."""
        try:
            ip = ipaddress.ip_address(ipv6_gateway)
            return isinstance(ip, ipaddress.IPv6Address)
        except ValueError:
            return False

    def _are_valid_dns(self, dns: str) -> bool:
        """Validate that provided string is a list of IP addresses."""
        try:
            list_of_dns = json.loads(dns)
            if not isinstance(list_of_dns, list):
                return False
            try:
                [ipaddress.ip_address(dns) for dns in list_of_dns]
            except ValueError:
                return False
        except json.JSONDecodeError:
            return False
        return True

    @property
    def _install_arguments(self) -> List[str]:
        """Prepares argument list for install command from configuration.

        Returns:
            List of arguments for install command
        """
        if self.model.config["skip-networking"]:
            return ["--skip-networking"]
        arguments = ["--dns"]
        arguments.extend(json.loads(self.model.config["dns"]))
        arguments.extend(["--sgi", self.model.config["sgi"], "--s1", self.model.config["s1"]])
        if self.model.config.get("sgi-ipv4-address"):
            arguments.extend(
                [
                    "--sgi-ipv4-address",
                    self.model.config["sgi-ipv4-address"],
                    "--sgi-ipv4-gateway",
                    self.model.config["sgi-ipv4-gateway"],
                ]
            )
        if self.model.config.get("sgi-ipv6-address"):
            arguments.extend(
                [
                    "--sgi-ipv6-address",
                    self.model.config["sgi-ipv6-address"],
                    "--sgi-ipv6-gateway",
                    self.model.config["sgi-ipv6-gateway"],
                ]
            )
        if self.model.config.get("s1-ipv4-address"):
            arguments.extend(
                [
                    "--s1-ipv4-address",
                    self.model.config["s1-ipv4-address"],
                    "--s1-ipv4-gateway",
                    self.model.config["s1-ipv4-gateway"],
                ]
            )
        if self.model.config.get("s1-ipv6-address"):
            arguments.extend(
                [
                    "--s1-ipv6-address",
                    self.model.config["s1-ipv6-address"],
                    "--s1-ipv6-gateway",
                    self.model.config["s1-ipv6-gateway"],
                ]
            )
        return arguments


if __name__ == "__main__":
    main(MagmaAccessGatewayOperatorCharm)
