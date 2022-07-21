# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, call, patch

from ops import testing

from charm import MagmaAccessGatewayOperatorCharm

testing.SIMULATE_CAN_CONNECT = True


class TestMagmaAccessGatewayOperatorCharm(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(MagmaAccessGatewayOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @patch("subprocess.run")
    def test_given_subprocess_doesnt_crash_when_install_then_snap_is_installed(
        self, patch_subprocess_run
    ):
        event = Mock()
        self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(["magma-access-gateway.install"], stdout=-1),
            ]
        )
