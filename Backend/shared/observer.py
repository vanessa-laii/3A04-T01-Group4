"""
SCEMAS Shared — Observer Interfaces
PAC Architecture: Observer pattern interfaces shared across agents.

Defines the four observer/subject interfaces from the UML:
  CitySubject   — implemented by CityController
  CityObserver  — implemented by CityDashboard
  PublicSubject — implemented by PublicController
  PublicObserver — implemented by PublicAPI

These are kept here so that any agent that needs to register as an
observer or implement a subject does not duplicate the interface
definition. The concrete implementations remain in each agent's own
controller.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# TYPE_CHECKING imports avoid circular dependencies at runtime.
# Agents import the concrete schema types from shared.schemas instead.
if TYPE_CHECKING:
    from shared.schemas import SensorDataSchema


# ---------------------------------------------------------------------------
# City Observer pattern
# UML: CitySubject <<interface>>, CityObserver <<interface>>
# ---------------------------------------------------------------------------

class CityObserver(ABC):
    """
    <<Interface>> CityObserver

    UML method:
      + update(CityDashboard)

    Implemented by: CityDashboard (city agent)
    Any class that wants to receive city sensor data updates must
    implement this interface and register with a CitySubject.
    """

    @abstractmethod
    def update(self, sensor_data: "SensorDataSchema") -> None:
        """
        Called by CitySubject.notify_observers() when new sensor data
        is available. Concrete implementations update their internal
        state and re-render the dashboard or trigger downstream actions.
        """
        pass


class CitySubject(ABC):
    """
    <<Interface>> CitySubject

    UML methods:
      + addObserver()
      + removeObserver()
      + notifyObservers()

    Implemented by: CityController (city agent)
    """

    @abstractmethod
    def add_observer(self) -> None:
        pass

    @abstractmethod
    def remove_observer(self) -> None:
        pass

    @abstractmethod
    async def notify_observers(self, sensor_data: "SensorDataSchema") -> None:
        pass


# ---------------------------------------------------------------------------
# Public Observer pattern
# UML: PublicSubject <<interface>>, PublicObserver <<interface>>
# ---------------------------------------------------------------------------

class PublicObserver(ABC):
    """
    <<Interface>> PublicObserver

    UML method:
      + update(PublicAPI)

    Implemented by: PublicAPI (public agent)
    Any class that wants to receive public-facing data updates must
    implement this interface and register with a PublicSubject.
    """

    @abstractmethod
    def update(self, snapshot: "object") -> None:
        """
        Called by PublicSubject.notify_observers() when the public
        sensor data or alert list changes.
        """
        pass


class PublicSubject(ABC):
    """
    <<Interface>> PublicSubject

    UML methods:
      + addObserver()
      + removeObserver()
      + notifyObservers()

    Implemented by: PublicController (public agent)
    """

    @abstractmethod
    def add_observer(self) -> None:
        pass

    @abstractmethod
    def remove_observer(self) -> None:
        pass

    @abstractmethod
    async def notify_observers(self) -> None:
        pass