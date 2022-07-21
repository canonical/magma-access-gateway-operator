# magma-access-gateway-operator

The Access Gateway (AGW) provides network services and policy enforcement. In an LTE network, 
the AGW implements an evolved packet core (EPC), and a combination of an AAA and a PGW. It works 
with existing, unmodified commercial radio hardware.


## Usage

```bash
juju add-space sgi 10.1.1.0/24
juju add-space s1 10.1.2.0/24
juju add-machine --constraints="cores=2 mem=8G spaces=sgi,s1"
juju deploy magma-access-gateway-operator
```
