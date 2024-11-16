"""Contains a method that creates user mobility traces according to a custom Point of Interest mobility model."""

import math

from ..user import User


def point_of_interest_mobility(user: User):
    """Creates a mobility path for an user based on a custom point of interest model.

    Args:
        user (User): User whose mobility will be defined.
    """
    if user.point_of_interest is None:
        user.coordinates_trace.extend([user.coordinates_trace[-1]])
        user.coordinates = user.coordinates_trace[-1]
        return

    parameters = getattr(user, "mobility_model_parameters", {})
    # Number of "mobility routines" added each time the method is called. Defaults to 1.
    n_moves = parameters.get("n_moves", 1)

    mobility_path = []

    for _ in range(n_moves):
        (x1, y1) = user.coordinates
        (x2, y2) = user.point_of_interest.coordinates
        (x3, y3) = (0, 0)
        total_distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

        if total_distance <= user.movement_distance:
            x3 = x2
            y3 = y2
        else:
            ratio = user.movement_distance / total_distance
            x3 = x1 + (x2 - x1) * ratio
            y3 = y1 + (y2 - y1) * ratio

        mobility_path.append((x3, y3))

    # # We assume that users do not necessarily move from one step to another, as one step may represent a very small time interval
    # # (e.g., 1 millisecond). Therefore, each position on the mobility path is repeated N times, so that user takes a predefined
    # # amount of time steps to move from one position to another. By default, users take at least 60 seconds to move across positions
    # # in the map. This parameter can be changed by passing a "seconds_to_move" key to the "parameters" parameter.
    # if "seconds_to_move" in parameters and type(parameters["seconds_to_move"]) is int and parameters["seconds_to_move"] < 1:
    #     raise Exception("The 'seconds_to_move' key passed inside the mobility model's 'parameters' attribute must be > 1.")
    # seconds_to_move = parameters["seconds_to_move"] if "seconds_to_move" in parameters else 60
    # mobility_path = [item for item in mobility_path for _ in range(int(seconds_to_move / user.model.tick_duration))]

    # Adding the path that connects the current to the target location to the client's mobility trace
    user.coordinates_trace.extend(mobility_path)
    user.coordinates = user.coordinates_trace[-1]
