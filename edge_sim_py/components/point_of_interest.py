"""Contains functionality related to points-of-interest."""

# EdgeSimPy components
from typing import Optional, Self, Tuple

# Mesa modules
from mesa import Agent, Model

from ..component_manager import ComponentManager

DAY_START_IN_MINUTES = 5 * 60
DAY_END_IN_MINUTES = 23 * 60
DAY_CYCLE_IN_MINUTES = DAY_END_IN_MINUTES - DAY_START_IN_MINUTES


def step_to_datetime(step: int) -> str:
    """Converts a step to a datetime string."""
    time_of_day_in_minutes = step % DAY_CYCLE_IN_MINUTES + DAY_START_IN_MINUTES
    hours = time_of_day_in_minutes // 60
    minutes = time_of_day_in_minutes % 60
    return f"Step {step:05d} Time: {hours:02d}:{minutes % 60:02d} Day: {step // DAY_CYCLE_IN_MINUTES + 1}"


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

        self.coordinates: Tuple[float, float] = (0.0, 0.0)
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
        from .user import User

        users_interested = []
        for user in User.all():
            if user.point_of_interest == self:
                users_interested.append(user.id)
        return {
            "Name": self.name,
            "Peak Start": self.peak_start,
            "Peak End": self.peak_end,
            "Coordinates": self.coordinates,
            "Is in peak": self.is_in_peak,
            "Percentage of peak time": f"{self.percentage_of_peak_time() * 100:.1f}%",
            "Users interested": users_interested,
        }

    def is_peak_time(self, current_step: int) -> bool:
        time_of_day_in_minutes = current_step % DAY_CYCLE_IN_MINUTES + DAY_START_IN_MINUTES
        return time_of_day_in_minutes >= self.peak_start and time_of_day_in_minutes < self.peak_end

    def step(self):
        current_step: int = self.model.schedule.steps + 1

        # not in peak yet, but this step will start being
        if not self.is_in_peak and self.is_peak_time(current_step):
            self.is_in_peak = True
            self.__class__._instances_in_peak.append(self)
        # is in peak, but should not be anymore
        elif self.is_in_peak and not self.is_peak_time(current_step):
            self.is_in_peak = False
            self.__class__._instances_in_peak.remove(self)

    def steps_left_in_peak(self) -> int:
        if not self.is_in_peak:
            return 0
        current_step: int = self.model.schedule.steps + 1
        time_of_day_in_minutes = current_step % DAY_CYCLE_IN_MINUTES + DAY_START_IN_MINUTES
        return self.peak_end - time_of_day_in_minutes

    def steps_since_peak_start(self) -> int:
        if not self.is_in_peak:
            return 0
        current_step: int = self.model.schedule.steps + 1
        time_of_day_in_minutes = current_step % DAY_CYCLE_IN_MINUTES + DAY_START_IN_MINUTES
        return time_of_day_in_minutes - self.peak_start

    def percentage_of_peak_time(self) -> float:
        if not self.is_in_peak:
            return 0
        return self.steps_since_peak_start() / (self.peak_end - self.peak_start)

    @classmethod
    def all_in_peak(cls) -> list[Self]:
        return cls._instances_in_peak
