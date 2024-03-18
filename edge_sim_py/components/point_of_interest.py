"""Contains functionality related to points-of-interest."""

# EdgeSimPy components
from typing import Optional, Self, Tuple
from ..component_manager import ComponentManager

# Mesa modules
from mesa import Agent, Model


class PointOfInterest(ComponentManager, Agent):
    """Class that represents a Point of Interest."""

    # Class attributes that allow this class to use helper methods from the ComponentManager
    _instances = []
    _instances_in_peak = []
    _object_count = 0

    def __init__(self, obj_id: Optional[int] = None):
        # Adding the new object to the list of instances of its class
        self.__class__._instances.append(self)
        self.__class__._object_count += 1

        # Object's class instance ID
        if obj_id is None:
            obj_id = self.__class__._object_count
        self.id = obj_id

        self.coordinates: Tuple[int, int] = (0, 0)
        self.name: str = ""
        self.peak_start: int = 0
        self.peak_end: int = 0
        self.is_in_peak: bool = False

        # Model-specific attributes (defined inside the model's "initialize()" method)
        self.model: Model = Model()
        self.unique_id: int = 0

    def _to_dict(self) -> dict:
        dictionary = {
            "attributes": {
                "id": self.id,
                "name": self.name,
                "peak_start": self.peak_start,
                "peak_end": self.peak_end,
                "coordinates": self.coordinates,
            },
            "relationships": {},
        }
        return dictionary

    def collect(self) -> dict:
        return {}

    def step(self):
        current_step: int = self.model.schedule.steps + 1
        # NOTE: maybe run this logic should only run if current_step % 100 = 0

        # not in peak yet, but this step will start being
        if not self.is_in_peak and current_step >= self.peak_start and current_step < self.peak_end:
            self.is_in_peak = True
            self.__class__._instances_in_peak.append(self)
        # is in peak, but should not be anymore
        elif self.is_in_peak and (current_step < self.peak_start or current_step >= self.peak_end):
            self.is_in_peak = False
            self.__class__._instances_in_peak.remove(self)

    @classmethod
    def all_in_peak(cls) -> list[Self]:
        return cls._instances_in_peak
