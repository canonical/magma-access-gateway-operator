# magma-access-gateway-operator

The Access Gateway (AGW) provides network services and policy enforcement. In an LTE network,
the AGW implements an evolved packet core (EPC), and a combination of an AAA and a PGW. It works
with existing, unmodified commercial radio hardware.

## Usage

Deploying the Magma Access Gateway requires a machine with two network
interfaces, for the SGi interface (this interface will be used to route traffic
to the Internet) and the S1 interface (this interface will be used to connect
to the eNodeB).

Production deployment are highly recommended to be deployed on physical
hardware.

For testing the deployment, a VM with two DHCP networks attached will do. You
can use this command to deploy it. The interface names will need to be adjusted
based on your specific machine.

```bash
juju deploy magma-access-gateway-operator --config sgi=enp0s1 --config s1=enp0s2
```

For static network configuration, the easiest method is to use a YAML
configuration file:

```yaml
---
magma-access-gateway-operator:
  sgi: enp0s1
  sgi-ipv4-address: 192.168.0.2/24
  sgi-ipv4-gateway: 192.168.0.1
  sgi-ipv6-address: fd7d:3797:378b:a502::2/64
  sgi-ipv6-gateway: fd7d:3797:378b:a502::1
  s1: enp0s2
  s1-ipv4-address: 192.168.1.2/24
  s1-ipv6-address: fd7d:3797:378b:a503::2/64
  dns: '["8.8.8.8", "208.67.222.222"]'
```

*WARNING* IPv6 support has been added to Magma in version 1.7.0. This charm
installs the right version, but your orchestrator will need to be at 1.7.0
minimum also.

You can then deploy the Access Gateway with this command:

```bash
juju deploy magma-access-gateway-operator --config agw_config.yaml
```
