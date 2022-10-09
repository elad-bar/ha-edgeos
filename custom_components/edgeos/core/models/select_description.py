from dataclasses import dataclass

from homeassistant.components.select import SelectEntityDescription


@dataclass
class SelectDescription(SelectEntityDescription):
    """A class that describes select entities."""

    options: tuple = ()
