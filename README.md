# magma-access-gateway-operator

## Description

Magma is an open-source software platform that gives network operators a mobile core network
solution. Magma has three major components:

1. **Access Gateway**
2. Orchestrator
3. Federation Gateway

The Access Gateway (AGW) provides network services and policy enforcement. In an LTE network,
the AGW implements an evolved packet core (EPC), and a combination of an AAA and a PGW. It works
with existing, unmodified commercial radio hardware.<br>
For more information on Magma please visit the [official website](https://magmacore.org/).

> :warning: Installing this charm will affect the target computer's networking configuration.
> Make sure it is installed on designated hardware (personal computers are strongly discouraged).

## System requirements

### Hardware (baremetal strongly recommended)

- Processor: x86-64 dual-core processor (around 2GHz clock speed or faster)
- Memory: 4GB RAM
- Storage: 32GB or greater SSD

### Networking

At least two ethernet interfaces (SGi and S1)

- SGi for internet connectivity
- S1 for enodeB connectivity

### Operating System

- Ubuntu 20.04 LTS
  ([Ubuntu installation guide](https://help.ubuntu.com/lts/installation-guide/amd64/index.html))
- Linux Kernel version `5.4`

> :warning: Some clouds like AWS use newer kernel versions by default. If you want to downgrade your kernel, please refer to the following [guide](https://discourse.ubuntu.com/t/how-to-downgrade-the-kernel-on-ubuntu-20-04-to-the-5-4-lts-version/26459).

## Usage

Deploying the Magma Access Gateway requires a machine with two network
interfaces, for the SGi interface (this interface will be used to route traffic
to the Internet) and the S1 interface (this interface will be used to connect
to the eNodeB).

Production deployment are highly recommended to be deployed on physical
hardware.

### 1. Install

**Using DHCP network configuration**

For testing the deployment, a VM with two DHCP networks attached will do. Use this command to deploy it:

> :warning: The interface names will need to be adjusted based on your specific machine.

```bash
juju deploy magma-access-gateway-operator --config sgi=enp0s1 --config s1=enp0s2
```

**Using static network configuration**

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

_WARNING_ IPv6 support has been added to Magma in version 1.7.0. This charm
installs the right version, but your orchestrator will need to be at 1.7.0
minimum also.

Deploy the Access Gateway with this command:

```bash
juju deploy magma-access-gateway-operator --config agw_config.yaml
```

### 2. Register AGW with an Orchestrator

Fetch AGW's `Hardware ID` and `Challenge Key`:

```bash
juju run-action magma-access-gateway-operator/<unit number> get-access-gateway-secrets --wait
```

Navigate to "Equipment" on the NMS via the left navigation bar, hit "Add Gateway" on the upper right, and fill out the multi-step modal form. Use the secrets from above for the "Hardware UUID" and "Challenge Key" fields.

**TODO: Fill when orc8r-AGW relation ready**

### 3. Verify the deployment

Run the following command:

```bash
juju run-action magma-access-gateway-operator/<unit number> post-install-checks --wait
```

Successful AGW deployment will be indicated by the `Magma AGW post-installation checks finished successfully.` message.

> :warning: Success will only occur when attached with an Orchestrator.
