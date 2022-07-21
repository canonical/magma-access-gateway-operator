#!/usr/bin/env python3
# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

"""Machine Charm for Magma's Access Gateway."""

import logging
import subprocess

from ops.charm import CharmBase, InstallEvent
from ops.main import main
from ops.model import ActiveStatus

logger = logging.getLogger(__name__)


class MagmaAccessGatewayOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Observes juju events."""
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)

    def _on_install(self, event: InstallEvent) -> None:
        """Triggered on install event.

        Args:
            event: Juju event

        Returns:
            None
        """
        self.install_magma_access_gateway_snap()
        self.install_magma_access_gateway()
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

    @staticmethod
    def install_magma_access_gateway() -> None:
        """Installs Magma access gateway on the host.

        Returns:
            None
        """
        subprocess.run(["magma-access-gateway.install"], stdout=subprocess.PIPE)

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


if __name__ == "__main__":
    main(MagmaAccessGatewayOperatorCharm)
