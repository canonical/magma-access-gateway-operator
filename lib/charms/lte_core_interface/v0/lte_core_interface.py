# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Library for the `lte-core` relation.

This library contains the Requires and Provides classes for handling the `lte-core`
interface.

The purpose of the library is to relate a charmed EPC (Provider) with charmed simulated enodeB and
user equipment (UEs) (Requirer). The interface will share the IP address of the MME
(Mobility Management Entity) from EPC to the charm which contains the corresponding
simulated enodeBs and UEs.

## Getting Started
From a charm directory, fetch the library using `charmcraft`:

```shell
charmcraft fetch-lib charms.lte_core_interface.v0.lte_core_interface
```

Add the following libraries to the charm's `requirements.txt` file:
- jsonschema

### Requirer charm
The requirer charm is the one requiring to connect to the LTE core
from another charm that provides this interface.

Example:
```python

from ops.charm import CharmBase
from ops.main import main

from charms.lte_core_interface.v0.lte_core_interface import (
    LTECoreAvailableEvent,
    LTECoreRequires,
)


class DummyLTECoreRequirerCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lte_core_requirer = LTECoreRequires(self, "lte-core")
        self.framework.observe(
            self.lte_core_requirer.on.lte_core_available,
            self._on_lte_core_available,
        )

    def _on_lte_core_available(self, event: LTECoreAvailableEvent):
        mme_ipv4_address = event.mme_ipv4_address
        <Do something with the mme_ipv4_address>


if __name__ == "__main__":
    main(DummyLTECoreRequirerCharm)
```

### Provider charm
The provider charm is the one providing information about the LTE core network
for another charm that requires this interface.

Example:
```python

from ops.charm import CharmBase, RelationJoinedEvent
from ops.main import main

from charms.lte_core_interface.v0.lte_core_interface import (
    LTECoreProvides,
)


class DummyLTECoreProviderCharm(CharmBase):
    def __init__(self, *args):
        super().__init__(*args)
        self.lte_core_provider = LTECoreProvides(self, "lte-core")
        self.framework.observe(
            self.on.lte_core_relation_joined, self._on_lte_core_relation_joined
        )

    def _on_lte_core_relation_joined(self, event: RelationJoinedEvent) -> None:
        if not self.unit.is_leader():
            return
        mme_ipv4_address = "some code for fetching the mme ipv4 address"
        self.lte_core_provider.set_lte_core_information(mme_ipv4_address=mme_ipv4_address)


if __name__ == "__main__":
    main(DummyLTECoreProviderCharm)
```

"""

import logging
from ipaddress import AddressValueError, IPv4Address

from jsonschema import exceptions, validate  # type: ignore[import]
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Handle, Object

# The unique Charmhub library identifier, never change it
LIBID = "3fbbdca922ec4ddd9598c3382034ad61"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 3


logger = logging.getLogger(__name__)

REQUIRER_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "`lte-core` requirer root schema",
    "type": "object",
    "description": "The `lte-core` root schema comprises the entire requirer databag for this interface.",  # noqa: E501
    "examples": [
        {
            "mme_ipv4_address": "127.0.0.1",  # noqa: E501
        }
    ],
    "properties": {
        "mme_ipv4_address": {
            "description": "The IP address of the MME (Mobility Management Entity) from the LTE core.",  # noqa: E501
            "type": "string",
            "format": "ipv4",
        },
    },
    "required": [
        "mme_ipv4_address",
    ],
    "additionalProperties": True,
}


class LTECoreAvailableEvent(EventBase):
    """Charm event emitted when a LTE core is available. It carries the mme ipv4 address."""

    def __init__(self, handle: Handle, mme_ipv4_address: str):
        """Init."""
        super().__init__(handle)
        self.mme_ipv4_address = mme_ipv4_address

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {"mme_ipv4_address": self.mme_ipv4_address}

    def restore(self, snapshot: dict) -> None:
        """Restores snapshot."""
        self.mme_ipv4_address = snapshot["mme_ipv4_address"]


class LTECoreRequirerCharmEvents(CharmEvents):
    """List of events that the LTE core requirer charm can leverage."""

    lte_core_available = EventSource(LTECoreAvailableEvent)


class LTECoreRequires(Object):
    """Class to be instantiated by the charm requiring the LTE core."""

    on = LTECoreRequirerCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str):
        """Init."""
        super().__init__(charm, relationship_name)
        self.charm = charm
        self.relationship_name = relationship_name
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_relation_changed
        )

    @staticmethod
    def _relation_data_is_valid(remote_app_relation_data: dict) -> bool:
        try:
            validate(instance=remote_app_relation_data, schema=REQUIRER_JSON_SCHEMA)
            return True
        except exceptions.ValidationError as e:
            logger.error("Invalid relation data: %s", e)
            return False

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handler triggered on relation changed event.

        Args:
            event: Juju event (RelationChangedEvent)

        Returns:
            None
        """
        relation = event.relation
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relationship_name)
            return
        remote_app_relation_data = relation.data[relation.app]
        if not self._relation_data_is_valid(dict(remote_app_relation_data)):
            logger.warning(
                "Provider relation data did no pass JSON Schema validation: \n%s",
                event.relation.app[event.app],  # type: ignore[index]
            )
            return
        self.on.lte_core_available.emit(
            mme_ipv4_address=remote_app_relation_data["mme_ipv4_address"],
        )


class LTECoreProvides(Object):
    """Class to be instantiated by the charm providing the LTE core."""

    def __init__(self, charm: CharmBase, relationship_name: str):
        """Init."""
        super().__init__(charm, relationship_name)
        self.relationship_name = relationship_name
        self.charm = charm

    @staticmethod
    def _mme_ipv4_address_is_valid(mme_ipv4_address: str) -> bool:
        """Returns whether mme ipv4 address is valid."""
        try:
            IPv4Address(mme_ipv4_address)
            return True
        except (AddressValueError):  # noqa: E722
            return False

    def set_lte_core_information(self, mme_ipv4_address: str) -> None:
        """Sets mme_ipv4_address in the application relation data.

        Args:
            mme_ipv4_address: MME ipv4 address
        Returns:
            None
        Raises:
            AddressValueError: If mme_ipv4_address is not a valid IPv4 address
        """
        if not self.model.get_relation(self.relationship_name):
            raise RuntimeError(f"Relation {self.relationship_name} not created yet.")
        if not self._mme_ipv4_address_is_valid(mme_ipv4_address):
            raise AddressValueError("Invalid MME IPv4 address.")
        relation = self.model.get_relation(self.relationship_name)
        relation.data[self.charm.app].update({"mme_ipv4_address": mme_ipv4_address})  # type: ignore[union-attr]  # noqa: E501
