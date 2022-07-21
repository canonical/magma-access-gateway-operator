# Contributing

## Developing

Create and activate a virtualenv with the development requirements:

    virtualenv -p python3 venv
    source venv/bin/activate


## Testing

### Unit tests

```bash
tox -e unit
```

### Static analysis

```bash
tox -e static
```

### Linting

```bash
tox -e lint
```

## Deploying an unpublished charm

```bash
charmcraft pack
juju deploy ./magma-access-gateway-operator_ubuntu-20.04-amd64.charm
```
