#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Machine Charm for Magma's Access Gateway."""

import copy
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
        """Triggered on start event.

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
        if not self._is_valid_interface_addressing_configuration("s1"):
            valid = False
        if not self._are_valid_dns(self.model.config["dns"]):
            logger.warning("Invalid DNS configuration")
            valid = False
        return valid

    def _is_valid_interface(self, interface_name: str, new_interface_name: str) -> bool:
        """Validates a network interface name.

        An interface name is required and must represent an interface present on the
        machine. Because Magma requires interfaces to be named a certain way, the
        installation will rename the interfaces. For that reason, we also check for
        the renamed interface to be present.

        Args:
            interface_name: Original name of the interface
            new_interface_name: Name of the interface that will be set by Magma

        Returns:
            True if the interface name is valid and found
        """
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

    @staticmethod
    def _is_valid_ipv4_address(ipv4_address: str) -> bool:
        """Validate an IPv4 address and netmask.

        A valid string will have the form:
        a.b.c.d/x
        """
        try:
            ip = ipaddress.ip_network(ipv4_address, strict=False)
            return isinstance(ip, ipaddress.IPv4Network) and ip.prefixlen != 32
        except ValueError:
            return False

    @staticmethod
    def _is_valid_ipv4_gateway(ipv4_gateway: str) -> bool:
        """Validate an IPv4 gateway.

        A valid string will have the form:
        a.b.c.d
        """
        try:
            ip = ipaddress.ip_address(ipv4_gateway)
            return isinstance(ip, ipaddress.IPv4Address)
        except ValueError:
            return False

    @staticmethod
    def _is_valid_ipv6_address(ipv6_address: str) -> bool:
        """Validate an IPv6 address and netmask.

        A valid string will contain an IPv6 address followed by a
        netmask, like this:
        2001:0db8:85a3:0000:0000:8a2e:0370:7334/64
        """
        try:
            ip = ipaddress.ip_network(ipv6_address, strict=False)
            return isinstance(ip, ipaddress.IPv6Network) and ip.prefixlen != 128
        except ValueError:
            return False

    @staticmethod
    def _is_valid_ipv6_gateway(ipv6_gateway: str) -> bool:
        """Validate an IPv6 gateway.

        A valid string will contain an IPv6 address, like this:
        2001:0db8:85a3:0000:0000:8a2e:0370:7334
        """
        try:
            ip = ipaddress.ip_address(ipv6_gateway)
            return isinstance(ip, ipaddress.IPv6Address)
        except ValueError:
            return False

    @staticmethod
    def _are_valid_dns(dns: str) -> bool:
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
        config = dict(copy.deepcopy(self.model.config))
        if config.pop("skip-networking"):
            return ["--skip-networking"]
        arguments = ["--dns"]
        arguments.extend(json.loads(config.pop("dns")))
        for key, value in config.items():
            arguments.extend([f"--{key}", value])
        return arguments


if __name__ == "__main__":
    main(MagmaAccessGatewayOperatorCharm)
