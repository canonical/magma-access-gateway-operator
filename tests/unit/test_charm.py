# Copyright 2021 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import pathlib
import tempfile
import unittest
from unittest.mock import Mock, PropertyMock, call, mock_open, patch

import ruamel.yaml
from ops import testing
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus

from charm import MagmaAccessGatewayOperatorCharm, install_file

testing.SIMULATE_CAN_CONNECT = True  # type: ignore[attr-defined]


class TestMagmaAccessGatewayOperatorCharm(unittest.TestCase):
    TEST_PIPELINED_CONFIG = """# Pipeline application level configs
access_control:
  # Blocks access to all AGW local IPs from UEs.
  block_agw_local_ips: true"""

    def setUp(self):
        self.yaml = ruamel.yaml.YAML()
        self.harness = testing.Harness(MagmaAccessGatewayOperatorCharm)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()
        self.charm = self.harness.charm

    @patch("subprocess.run")
    def test_given_no_config_provided_when_install_then_snap_is_installed_and_status_is_blocked(
        self, patch_subprocess_run
    ):
        event = Mock()
        patch_subprocess_run.side_effect = [Mock(returncode=1), Mock(returncode=0)]
        with self.assertLogs() as captured:
            self.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(["systemctl", "is-enabled", "magma@magmad"], stdout=-1),
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
            ]
        )
        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual("sgi interface name is required", captured.records[0].getMessage())
        self.assertEqual("s1 interface name is required", captured.records[1].getMessage())

    @patch("subprocess.run")
    @patch("charm.open", new_callable=mock_open, read_data=TEST_PIPELINED_CONFIG)
    def test_given_skip_networking_config_provided_when_install_then_snap_is_installed_and_status_is_maintenance(  # noqa: E501
        self, _, patch_subprocess_run
    ):
        event = Mock()
        patch_subprocess_run.side_effect = [
            Mock(returncode=1),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
        ]
        self.harness.update_config({"skip-networking": True})
        self.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(["systemctl", "is-enabled", "magma@magmad"], stdout=-1),
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    ["magma-access-gateway.install", "--no-reboot", "--skip-networking"],
                    stdout=-1,
                ),
                call(["shutdown", "--reboot", "+1"], stdout=-1),
            ]
        )

        self.assertEqual(
            self.charm.unit.status,
            MaintenanceStatus("Rebooting to apply changes"),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_interfaces_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        self.harness.update_config({"sgi": "nosuchinterface", "s1": "bananaphone"})
        with self.assertLogs() as captured:
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual("nosuchinterface interface not found", captured.records[0].getMessage())
        self.assertEqual("bananaphone interface not found", captured.records[1].getMessage())

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv4_address_and_no_gateway_in_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv4 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv4_gateway_and_no_address_in_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv4 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv6_address_and_no_gateway_in_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv6 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv6_gateway_and_no_address_in_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Both IPv6 address and gateway required for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_only_ipv6_sgi_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Pure IPv6 configuration is not supported for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_sgi_ipv4_address_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv4_address_missing_netmask_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_sgi_ipv4_gateway_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 gateway for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_sgi_ipv6_address_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_sgi_ipv6_address_missing_netmask_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 address and netmask for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_sgi_ipv6_gateway_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 gateway for interface sgi",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_only_ipv6_s1_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Pure IPv6 configuration is not supported for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_s1_ipv4_address_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv4 address and netmask for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_s1_ipv6_address_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid IPv6 address and netmask for interface s1",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_invalid_dns_config_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_dns_config_not_list_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
            captured.records[0].getMessage(),
        )

    @patch("netifaces.interfaces")
    @patch("subprocess.run")
    def test_given_dns_config_contains_non_ip_when_install_then_status_is_blocked(
        self, _, patch_interfaces
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
            self.charm._on_install(event=event)

        self.assertEqual(
            self.charm.unit.status,
            BlockedStatus("Configuration is invalid. Check logs for details"),
        )
        self.assertEqual(
            "Invalid DNS configuration",
            captured.records[0].getMessage(),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    @patch("charm.open", new_callable=mock_open, read_data=TEST_PIPELINED_CONFIG)
    def test_given_valid_static_config_when_install_then_status_is_maintenance(
        self, _, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        patch_subprocess_run.side_effect = [
            Mock(returncode=1),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
        ]
        self.harness.update_config(
            {
                "sgi": "enp0s1",
                "s1": "enp0s2",
                "sgi-ipv4-address": "10.0.0.2/24",
                "sgi-ipv4-gateway": "10.0.0.1",
                "sgi-ipv6-address": "2001:0db8:85a3:0000:0000:8a2e:0370:7334/64",
                "sgi-ipv6-gateway": "2001:0db8:85a3:0000:0000:8a2e:0370:7331",
                "s1-ipv4-address": "10.1.0.2/24",
                "s1-ipv6-address": "2002:0db8:85a3:0000:0000:8a2e:0370:7334/64",
            }
        )
        self.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(["systemctl", "is-enabled", "magma@magmad"], stdout=-1),
                call(
                    ["snap", "install", "magma-access-gateway", "--classic", "--edge"], stdout=-1
                ),
                call(
                    [
                        "magma-access-gateway.install",
                        "--no-reboot",
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
                call(["shutdown", "--reboot", "+1"], stdout=-1),
            ]
        )
        self.assertEqual(
            self.charm.unit.status,
            MaintenanceStatus("Rebooting to apply changes"),
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    @patch("charm.open", new_callable=mock_open, read_data=TEST_PIPELINED_CONFIG)
    def test_given_block_agw_local_ips_config_is_false_when_install_then_unblock_local_ips_flag_is_added_to_the_snap_installation_command(  # noqa: E501
        self, _, patch_interfaces, patch_subprocess_run
    ):
        event = Mock()
        patch_interfaces.return_value = ["enp0s1", "enp0s2"]
        patch_subprocess_run.side_effect = [
            Mock(returncode=1),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
            Mock(returncode=0),
        ]
        self.harness.update_config(
            {
                "sgi": "enp0s1",
                "s1": "enp0s2",
                "block-agw-local-ips": False,
            }
        )
        patch_subprocess_run.assert_has_calls(
            [
                call(["systemctl", "is-enabled", "magma@magmad"], stdout=-1),
                call(
                    [
                        "snap",
                        "install",
                        "magma-access-gateway",
                        "--classic",
                        "--channel",
                        "1.8/stable",
                    ],
                    stdout=-1,
                ),
                call(
                    [
                        "magma-access-gateway.install",
                        "--no-reboot",
                        "--dns",
                        "8.8.8.8",
                        "208.67.222.222",
                        "--unblock-local-ips",
                        "--sgi",
                        "enp0s1",
                        "--s1",
                        "enp0s2",
                    ],
                    stdout=-1,
                ),
                call(["shutdown", "--reboot", "+1"], stdout=-1),
            ]
        )
        self.charm._on_install(event=event)

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_magma_service_not_running_when_start_then_status_is_unchanged(
        self, _, patch_subprocess_run
    ):
        event = Mock()
        expected_status = self.charm.unit.status
        completed_process = Mock(returncode=1)
        patch_subprocess_run.return_value = completed_process

        self.charm._on_start(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["systemctl", "is-active", "magma@magmad"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.charm.unit.status,
            expected_status,
        )

    @patch("subprocess.run")
    @patch("netifaces.interfaces")
    def test_given_magma_service_running_when_start_then_status_is_active(
        self, _, patch_subprocess_run
    ):
        event = Mock()
        completed_process = Mock(returncode=0)
        patch_subprocess_run.return_value = completed_process

        self.charm._on_start(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["systemctl", "is-active", "magma@magmad"],
                    stdout=-1,
                ),
            ]
        )
        self.assertEqual(
            self.charm.unit.status,
            ActiveStatus(),
        )

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_given_magma_service_running_when_get_access_gateway_secrets_action_then_hardware_id_and_challenge_key_are_returned(  # noqa: E501
        self, patch_subprocess_run, patched_check_output
    ):
        completed_process = Mock(returncode=0)
        patch_subprocess_run.return_value = completed_process
        test_hw_id = "1234-abc-5678"
        test_challenge_key = "whatever"
        action_event = Mock()
        patched_check_output.return_value = f"""Hardware ID
------------
{test_hw_id}

Challenge key
-----------
{test_challenge_key}
""".encode(
            "utf-8"
        )

        self.charm._on_get_access_gateway_secrets(action_event)

        self.assertEqual(
            action_event.set_results.call_args,
            call({"hardware-id": test_hw_id, "challenge-key": test_challenge_key}),
        )

    @patch("subprocess.run")
    def test_given_magma_service_not_running_when_get_access_gateway_secrets_action_then_action_fails(  # noqa: E501
        self, patch_subprocess_run
    ):
        completed_process = Mock(returncode=1)
        patch_subprocess_run.return_value = completed_process
        action_event = Mock()

        self.charm._on_get_access_gateway_secrets(action_event)

        self.assertEqual(
            action_event.fail.call_args,
            call("Magma is not running! Please start Magma and try again."),
        )

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_given_magma_service_running_but_gateway_info_doesnt_return_anything_when_get_access_gateway_secrets_action_then_action_fails(  # noqa: E501
        self, patch_subprocess_run, patched_check_output
    ):
        completed_process = Mock(returncode=0)
        patch_subprocess_run.return_value = completed_process
        action_event = Mock()
        patched_check_output.return_value = "".encode("utf-8")

        self.charm._on_get_access_gateway_secrets(action_event)

        self.assertEqual(
            action_event.fail.call_args,
            call("Failed to get Magma Access Gateway secrets!"),
        )

    @patch("subprocess.check_output")
    @patch("subprocess.run")
    def test_given_magma_service_running_but_gateway_info_doesnt_return_values_for_secrets_when_get_access_gateway_secrets_action_then_action_fails(  # noqa: E501
        self, patch_subprocess_run, patched_check_output
    ):
        completed_process = Mock(returncode=0)
        patch_subprocess_run.return_value = completed_process
        action_event = Mock()
        patched_check_output.return_value = """Hardware ID
------------

Challenge key
-----------
""".encode(
            "utf-8"
        )

        self.charm._on_get_access_gateway_secrets(action_event)

        self.assertEqual(
            action_event.fail.call_args,
            call("Failed to get Magma Access Gateway secrets!"),
        )

    @patch("subprocess.run")
    def test_given_not_successful_post_install_checks_when_post_install_checks_action_then_error_message_is_set_in_action_results(  # noqa: E501
        self, patch_subprocess_run
    ):
        patch_subprocess_run.return_value = Mock(returncode=1)
        failed_msg = "Post-installation checks failed. For more information, please check journalctl logs."  # noqa: E501
        action_event = Mock()

        self.charm._on_post_install_checks_action(event=action_event)

        self.assertEqual(
            action_event.set_results.call_args,
            call({"post-install-checks-output": failed_msg}),
        )

    @patch("subprocess.run")
    def test_given_successful_post_install_checks_when_post_install_checks_action_then_success_message_is_set_in_action_results(  # noqa: E501
        self, patch_subprocess_run
    ):
        patch_subprocess_run.return_value = Mock(returncode=0)
        successful_msg = "Magma AGW post-installation checks finished successfully."
        action_event = Mock()

        self.charm._on_post_install_checks_action(event=action_event)

        self.assertEqual(
            action_event.set_results.call_args,
            call({"post-install-checks-output": successful_msg}),
        )

    @patch("subprocess.run")
    @patch("charm.open", new_callable=mock_open, read_data=TEST_PIPELINED_CONFIG)
    def test_given_magma_service_enabled_when_install_then_nothing_done(
        self, _, patch_subprocess_run
    ):
        event = Mock()
        patch_subprocess_run.side_effect = [Mock(returncode=0)]

        self.charm._on_install(event=event)

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["systemctl", "is-enabled", "magma@magmad"],
                    stdout=-1,
                ),
            ]
        )

    @patch("subprocess.run")
    @patch("charm.Path")
    def test_given_certifier_pem_not_stored_when_certifier_pem_changed_then_remove_agw_certs_not_called(  # noqa: E501
        self, patch_path, _
    ):
        patch_path.return_value.exists.return_value = False
        relation_id = self.harness.add_relation("magma-orchestrator", "orc8r-nginx-operator")
        self.harness.add_relation_unit(relation_id, "orc8r-nginx-operator/0")
        self.harness.update_relation_data(
            relation_id,
            "orc8r-nginx-operator",
            {
                "root_ca_certificate": "root_ca_certificate_content",
                "certifier_pem_certificate": "certifier_pem_certificate_content",
                "orchestrator_address": "orchestrator.com",
                "orchestrator_port": "42",
                "bootstrapper_address": "bootstrapper.com",
                "bootstrapper_port": "42",
                "fluentd_address": "fluentd.com",
                "fluentd_port": "42",
            },
        )
        self.assertNotIn(call().unlink(), patch_path.mock_calls)

    @patch("subprocess.run")
    @patch("charm.Path")
    def test_given_certifier_pem_stored_when_certifier_pem_changed_then_remove_agw_certs_called(
        self, patch_path, _
    ):
        relation_id = self.harness.add_relation("magma-orchestrator", "orc8r-nginx-operator")
        self.harness.add_relation_unit(relation_id, "orc8r-nginx-operator/0")
        self.harness.update_relation_data(
            relation_id,
            "orc8r-nginx-operator",
            {
                "root_ca_certificate": "root_ca_certificate_content",
                "certifier_pem_certificate": "certifier_pem_certificate_content",
                "orchestrator_address": "orchestrator.com",
                "orchestrator_port": "42",
                "bootstrapper_address": "bootstrapper.com",
                "bootstrapper_port": "42",
                "fluentd_address": "fluentd.com",
                "fluentd_port": "42",
            },
        )
        self.assertIn(call().unlink(), patch_path.mock_calls)

    @patch("charm.Path")
    @patch("subprocess.run")
    def test_when_orchestrator_available_event_then_configuration_is_installed(
        self, patch_subprocess_run, patch_path
    ):
        relation_id = self.harness.add_relation("magma-orchestrator", "orc8r-nginx-operator")
        self.harness.add_relation_unit(relation_id, "orc8r-nginx-operator/0")
        self.harness.update_relation_data(
            relation_id,
            "orc8r-nginx-operator",
            {
                "root_ca_certificate": "root_ca_certificate_content",
                "certifier_pem_certificate": "certifier_pem_certificate_content",
                "orchestrator_address": "orchestrator.com",
                "orchestrator_port": "42",
                "bootstrapper_address": "bootstrapper.com",
                "bootstrapper_port": "42",
                "fluentd_address": "fluentd.com",
                "fluentd_port": "42",
            },
        )

        mock_calls = patch_path.mock_calls
        expected_calls = [
            call("/var/opt/magma/tmp/certs/rootCA.pem"),
            call().write_text("root_ca_certificate_content"),
            call("/var/opt/magma/tmp/certs/certifier.pem"),
            call().write_text("root_ca_certificate_content"),
            call("/var/opt/magma/configs/control_proxy.yml"),
            call().write_text(
                "cloud_address: orchestrator.com\n"
                "cloud_port: 42\n"
                "bootstrap_address: bootstrapper.com\n"
                "bootstrap_port: 42\n"
                "fluentd_address: fluentd.com\n"
                "fluentd_port: 42\n"
                "\n"
                "rootca_cert: /var/opt/magma/tmp/certs/rootCA.pem\n"
            ),
        ]
        self.assertTrue(all(mock_call in mock_calls for mock_call in expected_calls))

        patch_subprocess_run.assert_has_calls(
            [
                call(
                    ["service", "magma@*", "stop"],
                    stdout=-1,
                ),
                call(
                    ["service", "magma@magmad", "start"],
                    stdout=-1,
                ),
            ]
        )

    @patch("netifaces.ifaddresses")
    def test_given_eth1_interface_is_available_and_unit_is_leader_when_lte_core_relation_joined_then_then_core_information_is_set(  # noqa: E501
        self,
        patch_ip_address,
    ):
        self.harness.set_leader(True)
        patch_ip_address.return_value = {2: [{"addr": "0.0.0.0"}]}
        relation_id = self.harness.add_relation("lte-core", "srs-enb-ue-operator")
        self.harness.add_relation_unit(relation_id, "srs-enb-ue-operator/0")
        self.assertEqual(
            self.harness.get_relation_data(relation_id, self.charm.app),
            {"mme_ipv4_address": "0.0.0.0"},
        )

    @patch("netifaces.ifaddresses")
    def test_given_eth1_interface_is_available_and_unit_is_leader_when_lte_core_relation_joined_then_charm_is_active(  # noqa: E501
        self,
        patch_ip_address,
    ):
        self.harness.set_leader(True)
        patch_ip_address.return_value = {2: [{"addr": "0.0.0.0"}]}
        relation_id = self.harness.add_relation("lte-core", "srs-enb-ue-operator")
        self.harness.add_relation_unit(relation_id, "srs-enb-ue-operator/0")
        self.assertEqual(
            self.charm.unit.status,
            ActiveStatus(),
        )

    def test_given_eth1_interface_is_available_and_unit_is_not_leader_when_lte_core_relation_joined_then_core_information_is_not_set(  # noqa: E501
        self,
    ):
        self.harness.set_leader(False)
        relation_id = self.harness.add_relation("lte-core", "srs-enb-ue-operator")
        self.harness.add_relation_unit(relation_id, "srs-enb-ue-operator/0")
        self.assertEqual(
            self.harness.get_relation_data(relation_id, self.charm.app),
            {},
        )

    def test_given_eth1_interface_is_not_available_when_lte_core_relation_joined_then_core_information_is_not_set(  # noqa: E501
        self,
    ):
        self.harness.set_leader(True)
        relation_id = self.harness.add_relation("lte-core", "srs-enb-ue-operator")
        self.harness.add_relation_unit(relation_id, "srs-enb-ue-operator/0")
        self.assertEqual(
            self.harness.get_relation_data(relation_id, self.charm.app),
            {},
        )

    def test_given_eth1_interface_is_not_available_when_lte_core_relation_joined_then_charm_is_in_waiting_status(  # noqa: E501
        self,
    ):
        self.harness.set_leader(True)
        relation_id = self.harness.add_relation("lte-core", "srs-enb-ue-operator")
        self.harness.add_relation_unit(relation_id, "srs-enb-ue-operator/0")
        self.assertEqual(
            self.charm.unit.status,
            WaitingStatus("Waiting for the MME interface to be ready"),
        )

    def test_given_directory_does_not_exist_when_install_file_then_directory_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            file = pathlib.Path(directory) / "does_not_exist" / "file.txt"

            install_file(file, "content")

            self.assertTrue(file.parent.exists())

    def test_given_file_exists_and_already_has_content_when_install_file_then_return_false(self):
        with tempfile.TemporaryDirectory() as directory:
            file = pathlib.Path(directory) / "exists" / "file.txt"
            file.parent.mkdir()
            file.write_text("content")

            self.assertFalse(install_file(file, "content"))

    def test_given_file_exists_without_content_when_install_file_then_return_true_and_content_is_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            file = pathlib.Path(directory) / "exists" / "file.txt"
            file.parent.mkdir()
            file.write_text("")

            self.assertTrue(install_file(file, "content"))
            self.assertEqual(file.read_text(), "content")

    def test_given_file_does_not_exist_when_install_file_then_return_true_and_content_is_written(  # noqa: E501
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            file = pathlib.Path(directory) / "exists" / "file.txt"

            self.assertTrue(install_file(file, "content"))
            self.assertEqual(file.read_text(), "content")

    @patch(
        "charm.MagmaAccessGatewayOperatorCharm.PIPELINED_CONFIG_FILE", new_callable=PropertyMock
    )
    @patch("subprocess.run")
    def test_given_block_agw_local_ips_true_when_block_agw_local_ips_config_changed_to_false_then_block_agw_local_ips_value_updated(  # noqa: E501
        self, patched_subprocess_run, patched_pipelined_config_file
    ):
        patched_subprocess_run.side_effect = [Mock(returncode=0), Mock(returncode=0)]
        test_config = {"block-agw-local-ips": False}
        with tempfile.TemporaryDirectory() as tempdir:
            tmpfilepath = os.path.join(tempdir, "fake_pipelined.yml")
            with open(tmpfilepath, "w") as fake_pipelined:
                fake_pipelined.write(self.TEST_PIPELINED_CONFIG)

            patched_pipelined_config_file.return_value = tmpfilepath
            self.harness.update_config(test_config)

            with open(tmpfilepath, "r") as fake_pipelined:
                config = self.yaml.load(fake_pipelined)

            self.assertEqual(config["access_control"]["block_agw_local_ips"], False)
