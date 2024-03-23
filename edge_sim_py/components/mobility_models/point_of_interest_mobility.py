"""Contains a method that creates user mobility traces according to a custom Point of Interest mobility model."""

import math

from ..user import User


def point_of_interest_mobility(user: User):
    """Creates a mobility path for an user based on a custom point of interest model.

    Args:
        user (User): User whose mobility will be defined.
    """
    if user.point_of_interest is None:
        return

    _parameters = getattr(user, "mobility_model_parameters", {})
    (x1, y1) = user.coordinates_trace[-1]
    (x2, y2) = user.point_of_interest.coordinates
    total_distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    if total_distance <= user.movement_distance:
        user.coordinates_trace.extend((x2, y2))
        user.coordinates = (x2, y2)
        return

    ratio = user.movement_distance / total_distance
    x3 = x1 + (x2 - x1) * ratio
    y3 = y1 + (y2 - y1) * ratio
    user.coordinates_trace.append((x3, y3))
    user.coordinates = (x3, y3)
