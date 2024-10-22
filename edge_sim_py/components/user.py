"""Contains user-related functionality."""

# EdgeSimPy components
# Python libraries
import copy
import random
from typing import Callable, Optional, Tuple

import networkx as nx

# Mesa modules
from mesa import Agent, Model

from ..component_manager import ComponentManager
from .application import Application
from .base_station import BaseStation
from .network_switch import NetworkSwitch
from .point_of_interest import PointOfInterest
from .topology import Topology


class User(ComponentManager, Agent):
    """Class that represents an user."""

    # Class attributes that allow this class to use helper methods from the ComponentManager
    _instances = []
    _object_count = 0

    def __init__(self, obj_id: Optional[int] = None):
        """Creates an User object.

        Args:
            obj_id (int, optional): Object identifier. Defaults to None.

        Returns:
            object: Created User object.
        """
        # Adding the new object to the list of instances of its class
        self.__class__._instances.append(self)

        # Object's class instance ID
        self.__class__._object_count += 1
        if obj_id is None:
            obj_id = self.__class__._object_count
        self.id = obj_id

        # User coordinates
        self.coordinates_trace: list[Tuple[int, int]] = []
        self.coordinates: Tuple[int, int] = (0, 0)

        # List of applications accessed by the user
        self.applications: list[Application] = []

        # Reference to the base station the user is connected to
        self.base_station: BaseStation = BaseStation()

        # User access metadata
        self.making_requests = {}
        self.access_patterns = {}

        # User mobility model
        self.mobility_model: Callable[[User], None] = lambda user: None
        self.mobility_model_parameters = {}

        # List of metadata from applications accessed by the user
        self.communication_paths = {}
        self.delays = {}
        self.delay_slas = {}

        # Model-specific attributes (defined inside the model's "initialize()" method)
        self.model: Model = Model()
        self.unique_id: int = 0

        # Custom user mobility attributes
        self.point_of_interest: Optional[PointOfInterest] = None
        self.chance_of_becoming_interested = 100
        self.movement_distance: int = 0

    def _to_dict(self) -> dict:
        """Method that overrides the way the object is formatted to JSON."

        Returns:
            dict: JSON-friendly representation of the object as a dictionary.
        """
        access_patterns = {}
        for app_id, access_pattern in self.access_patterns.items():
            access_patterns[app_id] = {"class": access_pattern.__class__.__name__, "id": access_pattern.id}

        dictionary = {
            "attributes": {
                "id": self.id,
                "coordinates": self.coordinates,
                "coordinates_trace": self.coordinates_trace,
                "delays": copy.deepcopy(self.delays),
                "delay_slas": copy.deepcopy(self.delay_slas),
                "communication_paths": copy.deepcopy(self.communication_paths),
                "making_requests": copy.deepcopy(self.making_requests),
                "mobility_model_parameters": (
                    copy.deepcopy(self.mobility_model_parameters) if self.mobility_model_parameters else {}
                ),
            },
            "relationships": {
                "access_patterns": access_patterns,
                "mobility_model": self.mobility_model.__name__,
                "applications": [{"class": type(app).__name__, "id": app.id} for app in self.applications],
                "base_station": (
                    {"class": type(self.base_station).__name__, "id": self.base_station.id}
                    if self.base_station is not None
                    else {}
                ),
                "point_of_interest": (
                    {"id": self.point_of_interest.id, "name": self.point_of_interest.name}
                    if self.point_of_interest is not None
                    else {}
                ),
            },
        }
        return dictionary

    def collect(self) -> dict:
        """Method that collects a set of metrics for the object.

        Returns:
            metrics (dict): Object metrics.
        """
        access_history = {}
        for app in self.applications:
            access_history[str(app.id)] = self.access_patterns[str(app.id)].history

        metrics = {
            "Instance ID": self.id,
            "Coordinates": self.coordinates,
            "Coordinates Trace": self.coordinates_trace,
            "Base Station": f"{self.base_station} ({self.base_station.coordinates})" if self.base_station else None,
            "Delays": copy.deepcopy(self.delays),
            "Communication Paths": copy.deepcopy(self.communication_paths),
            "Making Requests": copy.deepcopy(self.making_requests),
            "Access History": copy.deepcopy(access_history),
        }
        return metrics

    def step(self):
        """Method that executes the events involving the object at each time step."""
        # Updating user access
        current_step = self.model.schedule.steps + 1

        self.step_point_of_interest()

        for app in self.applications:
            last_access = self.access_patterns[str(app.id)].history[-1]

            # Updating user access waiting and access times. Waiting time represents the period in which the user is waiting for
            # his application to be provisioned. Access time represents the period in which the user is successfully accessing
            # his application, meaning his application is available. We assume that an application is only available when all its
            # services are available.
            if self.making_requests[str(app.id)][str(current_step)] == True:
                if len([s for s in app.services if s._available]) == len(app.services):
                    last_access["access_time"] += 1
                else:
                    last_access["waiting_time"] += 1

            # Updating user's making requests attribute for the next time step
            if current_step + 1 >= last_access["start"] and current_step + 1 <= last_access["end"]:
                self.making_requests[str(app.id)][str(current_step + 1)] = True
            else:
                self.making_requests[str(app.id)][str(current_step + 1)] = False

            # Creating new access request if needed
            if current_step + 1 == last_access["next_access"]:
                self.making_requests[str(app.id)][str(current_step + 1)] = True
                self.access_patterns[str(app.id)].get_next_access(start=current_step + 1)

        # Re-executing user's mobility model in case no future mobility track is known by the simulator
        if len(self.coordinates_trace) <= self.model.schedule.steps:
            self.mobility_model(self)

        # Updating user's location
        if self.coordinates != self.coordinates_trace[self.model.schedule.steps]:
            self.coordinates = self.coordinates_trace[self.model.schedule.steps]

            # Connecting the user to the closest base station
            self.base_station = BaseStation.find_by(attribute_name="coordinates", attribute_value=self.coordinates)

            for application in self.applications:
                # Only updates the routing path of apps available (i.e., whose services are available)
                services_available = len([s for s in application.services if s._available])
                if services_available == len(application.services):
                    # Recomputing user communication paths
                    self.set_communication_path(app=application)
                else:
                    self.communication_paths[str(application.id)] = []
                    self._compute_delay(app=application)

    def _compute_delay(self, app: Application, metric: str = "latency") -> int:
        """Computes the delay of an application accessed by the user.

        Args:
            metric (str, optional): Delay measure (valid options: 'latency' and 'response time'). Defaults to 'latency'.
            app (object): Application accessed by the user.

        Returns:
            delay (int): User-perceived delay when accessing application "app".
        """
        topology = Topology.first()

        services_available = len([s for s in app.services if s._available])
        if services_available < len(app.services):
            # Defining the delay as infinity if any of the application services is not available
            delay = float("inf")
        else:
            # Initializes the application's delay with the time it takes to communicate its client and his base station
            delay = self.base_station.wireless_delay

            # Adding the communication path delay to the application's delay
            for path in self.communication_paths[str(app.id)]:
                delay += topology.calculate_path_delay(path=[NetworkSwitch.find_by_id(i) for i in path])

            if metric.lower() == "response time":
                # We assume that Response Time = Latency * 2
                delay = delay * 2

        # Updating application delay inside user's 'applications' attribute
        self.delays[str(app.id)] = delay

        return delay

    def set_communication_path(self, app: Application, communication_path: list = []) -> list:
        """Updates the set of links used during the communication of user and its application.

        Args:
            app (object): User application.
            communication_path (list, optional): User-specified communication path. Defaults to [].

        Returns:
            list: Updated communication path.
        """
        topology = Topology.first()

        # Releasing links used in the past to connect the user with its application
        if app in self.communication_paths:
            path = [[NetworkSwitch.find_by_id(i) for i in p] for p in self.communication_paths[str(app.id)]]
            topology._release_communication_path(communication_path=path, app=app)

        # Defining communication path
        if len(communication_path) > 0:
            self.communication_paths[str(app.id)] = communication_path
        else:
            self.communication_paths[str(app.id)] = []

            service_hosts_base_stations = [service.server.base_station for service in app.services if service.server]
            communication_chain = [self.base_station] + service_hosts_base_stations

            # Defining a set of links to connect the items in the application's service chain
            for i in range(len(communication_chain) - 1):
                # Defining origin and target nodes
                origin = communication_chain[i]
                target = communication_chain[i + 1]

                # Finding and storing the best communication path between the origin and target nodes
                if origin == target:
                    path = []
                else:
                    path = nx.shortest_path(
                        G=topology,
                        source=origin.network_switch,
                        target=target.network_switch,
                        weight="delay",
                        method="dijkstra",
                    )

                # Adding the best path found to the communication path
                self.communication_paths[str(app.id)].append([network_switch.id for network_switch in path])

                # Computing the new demand of chosen links
                path = [[NetworkSwitch.find_by_id(i) for i in p] for p in self.communication_paths[str(app.id)]]
                topology._allocate_communication_path(communication_path=path, app=app)

        # Computing application's delay
        self._compute_delay(app=app, metric="latency")

        return self.communication_paths[str(app.id)]

    def _connect_to_application(self, app: Application, delay_sla: float):
        """Connects the user to a given application, establishing all the relationship attributes in both objects.

        Args:
            app (object): Application that will be connected to the user.
            delay_sla (float): Delay threshold for the user regarding the specified application.

        Returns:
            self (object): Updated user object.
        """
        # Defining the relationship attributes between the user and its new application
        self.applications.append(app)
        app.users.append(self)

        # Assigning delay and delay SLA attributes. Delay is initially None, and must be overwritten by the service placement
        self.delay_slas[str(app.id)] = delay_sla
        self.delays[str(app.id)] = None

    def _set_initial_position(self, coordinates: list, number_of_replicates: int = 0) -> object:
        """Defines the initial coordinates for the user, automatically connecting to a base station in that position.

        Args:
            coordinates (list): Initial user coordinates.
            number_of_replicates (int, optional): Number of times the initial coordinates will replicated in the coordinates trace. Defaults to 0.

        Returns:
            self (object): Updated user object.
        """
        # Defining the "coordinates" and "coordinates_trace" attributes
        self.coordinates = coordinates
        self.coordinates_trace = [coordinates for _ in range(number_of_replicates - 1)]

        # Connecting the user to the base station that shares his initial position
        base_station = BaseStation.find_by(attribute_name="coordinates", attribute_value=self.coordinates)

        if base_station is None:
            raise Exception(f"No base station was found at coordinates {coordinates} to connect to user {self}.")

        self.base_station = base_station
        base_station.users.append(self)

    def step_point_of_interest(self):
        """Step logic for point of interest.

        Chooses a random point of interest if user doesn't already have one.
        There is a chance of 40% of not picking any POIs.
        If user has POI, but is is not in peak, this method removes it.
        """
        # doesn't have a poi yet
        if self.point_of_interest is None:
            # Random 60% chance of getting a point of interest
            if random.randint(0, 100) < self.chance_of_becoming_interested:
                pois_in_peak = PointOfInterest.all_in_peak()
                self.point_of_interest = random.choice(pois_in_peak) if len(pois_in_peak) > 0 else None

        # already has an poi, but it isn't in peak anymore
        elif not self.point_of_interest.is_in_peak:
            self.point_of_interest = None

    @classmethod
    def random_user_placement(cls, grid_coordinates: list[tuple[int, int]]) -> tuple[int, int]:
        """Method that determines the coordinates of a given user randomly.

        Returns:
            coordinates (tuple): Random user coordinates.
        """
        coordinates = random.choice(grid_coordinates)
        return coordinates
