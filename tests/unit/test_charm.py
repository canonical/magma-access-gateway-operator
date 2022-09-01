# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, call, patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus

from charm import MagmaAccessGatewayOperatorCharm

testing.SIMULATE_CAN_CONNECT = True


class TestMagmaAccessGatewayOperatorCharm(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(MagmaAccessGatewayOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @patch("subprocess.run")
    def test_given_no_config_provided_when_install_then_snap_is_installed(
        self, patch_subprocess_run
    ):
        event = Mock()
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual("sgi interface name is required", captured.records[0].getMessage())
        self.assertEqual("s1 interface name is required", captured.records[1].getMessage())

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_interfaces_config_when_install_then_status_is_blocked(
        self, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "nosuchinterface", "s1": "bananaphone"})
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual("nosuchinterface interface not found", captured.records[0].getMessage())
        self.assertEqual("bananaphone interface not found", captured.records[1].getMessage())

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_sgi_ipv4_address_and_no_gateway_in_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2/24",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv4 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_sgi_ipv4_gateway_and_no_address_in_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-gateway": "10.0.0.1",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv4 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_sgi_ipv6_address_and_no_gateway_in_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv6 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_sgi_ipv6_gateway_and_no_address_in_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv6-gateway": "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv6 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_only_ipv6_sgi_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                "sgi-ipv6-gateway": "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Pure IPv6 configuration is not supported for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_sgi_ipv4_address_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "invalidip",
                "sgi-ipv4-gateway": "10.0.0.1",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_sgi_ipv4_gateway_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2/24",
                "sgi-ipv4-gateway": "not a gateway",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 gateway for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_sgi_ipv6_address_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2/24",
                "sgi-ipv4-gateway": "10.0.0.1",
            }
        )
        self.harness.update_config(
            {
                "sgi-ipv6-address": "not ipv6",
                "sgi-ipv6-gateway": "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_sgi_ipv6_gateway_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2/24",
                "sgi-ipv4-gateway": "10.0.0.1",
            }
        )
        self.harness.update_config(
            {
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                "sgi-ipv6-gateway": "not a gateway",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 gateway for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_valid_dhcp_config_when_install_then_status_is_active(
        self, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    ["magma-access-gateway.install", "--sgi", "enp0s1", "--s1", "enp0s2"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_valid_static_config_when_install_then_status_is_active(
        self, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2/24",
                "sgi-ipv4-gateway": "10.0.0.1",
            }
        )
        self.harness.update_config(
            {
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                "sgi-ipv6-gateway": "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
            }
        )
        self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    ["magma-access-gateway.install", "--sgi", "enp0s1", "--s1", "enp0s2"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus(),
        )
