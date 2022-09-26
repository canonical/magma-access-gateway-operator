# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, call, patch

from ops import testing
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus

from charm import MagmaAccessGatewayOperatorCharm

testing.SIMULATE_CAN_CONNECT = True


class TestMagmaAccessGatewayOperatorCharm(unittest.TestCase):
    def setUp(self):
        self.harness = testing.Harness(MagmaAccessGatewayOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @patch("subprocess.run")
    def test_given_no_config_provided_when_install_then_snap_is_installed_and_status_is_blocked(
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
    def test_given_skip_networking_config_provided_when_install_then_snap_is_installed_and_status_is_maintenance(  # noqa: E501
        self, patch_subprocess_run
    ):
        event = Mock()
        self.harness.update_config({"skip-networking": "True"})
        self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    ["magma-access-gateway.install", "--skip-networking"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            MaintenanceStatus("Installing AGW"),
        )

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
    def test_given_sgi_ipv4_address_missing_netmask_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "sgi-ipv4-address": "10.0.0.2",
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
    def test_given_sgi_ipv6_address_missing_netmask_config_when_install_then_status_is_blocked(
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
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7332",
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
    def test_given_only_ipv6_s1_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "s1-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Pure IPv6 configuration is not supported for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_s1_ipv4_address_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "s1-ipv4-address": "invalidip",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 address and netmask for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_s1_ipv6_address_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "s1-ipv4-address": "10.0.0.2/24",
            }
        )
        self.harness.update_config(
            {
                "s1-ipv6-address": "not ipv6",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 address and netmask for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_invalid_dns_config_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "dns": "notjson",
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_dns_config_not_list_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "dns": '{"dns": "8.8.8.8"}',
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_dns_config_contains_non_ip_when_install_then_status_is_blocked(
        self,
        patch_interfaces,
        patch_subprocess_run,
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "enp0s1", "s1": "enp0s2"})
        self.harness.update_config(
            {
                "dns": '["8.8.8.8", "dns1.example.com"]',
            }
        )
        with self.assertLogs() as captured:
            self.harness.charm._on_install(event=event)

        self.assertEqual(
            self.harness.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
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
                    [
                        "magma-access-gateway.install",
                        "--dns",
                        "8.8.8.8",
                        "208.67.222.222",
                        "--sgi",
                        "enp0s1",
                        "--s1",
                        "enp0s2",
                    ],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            MaintenanceStatus("Installing AGW"),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_valid_static_config_when_install_then_status_is_maintenance(
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
        self.harness.update_config(
            {
                "s1-ipv4-address": "10.1.0.2/24",
            }
        )
        self.harness.update_config(
            {
                "s1-ipv6-address": "2002:0db8:85a3:0000:0000:8a2e:0370:7334/64",
            }
        )
        self.harness.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    [
                        "magma-access-gateway.install",
                        "--dns",
                        "8.8.8.8",
                        "208.67.222.222",
                        "--sgi",
                        "enp0s1",
                        "--s1",
                        "enp0s2",
                        "--sgi-ipv4-address",
                        "10.0.0.2/24",
                        "--sgi-ipv4-gateway",
                        "10.0.0.1",
                        "--sgi-ipv6-address",
                        "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                        "--sgi-ipv6-gateway",
                        "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
                        "--s1-ipv4-address",
                        "10.1.0.2/24",
                        "--s1-ipv6-address",
                        "2002:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                    ],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            MaintenanceStatus("Installing AGW"),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_magma_service_not_running_when_start_then_status_is_unchanged(
        self, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        expected_status = self.harness.charm.unit.status
        completed_process = Mock(returncode=1)
        patch_subprocess_run.return_value = completed_process

        self.harness.charm._on_start(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["systemctl", "is-active", "magma@magmad"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            expected_status,
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_magma_service_running_when_start_then_status_is_active(
        self, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        completed_process = Mock(returncode=0)
        patch_subprocess_run.return_value = completed_process

        self.harness.charm._on_start(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["systemctl", "is-active", "magma@magmad"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.harness.charm.unit.status,
            ActiveStatus(),
        )

    @patch("subprocess.run")
    @patch("subprocess.check_output")
    def test_given_magma_is_running_when_post_install_checks_action_then_checks_start(
        self,
        patch_subprocess_check_output,
        patch_subprocess_run,
    ):
        action_event = Mock()
        patch_subprocess_run.return_value = Mock(returncode=0)
        
        self.harness.charm._on_post_install_checks_action(event=action_event)

        patch_subprocess_check_output.assert_has_calls(
            [
                call(
                    ["magma-access-gateway.post-install"]
                ),
            ]
        )

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_given_magma_is_not_running_when_post_install_checks_action_then_checks_not_start(
        self, 
        patch_subprocess_run,
        patch_check_output
    ):
        patch_subprocess_run.return_value = Mock(returncode=1)
        action_event = Mock()

        self.harness.charm._on_post_install_checks_action(event=action_event)

        patch_check_output.assert_not_called()
