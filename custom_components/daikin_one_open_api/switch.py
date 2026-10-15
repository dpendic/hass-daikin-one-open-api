"""Sensor platform for daikin_one_open_api."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.exceptions import HomeAssistantError

from .api_types import ModeEmergencyHeatAvailable, ThermostatMode
from .entity import DaikinOneOpenApiEntity

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api_types import DaikinOneOpenApiThermostatStateResponse
    from .coordinator import DaikinOneOpenApiDataUpdateCoordinator
    from .data import DaikinOneOpenApiConfigEntry, DaikinOneOpenApiConfigEntryDeviceData


@dataclasses.dataclass(frozen=True, kw_only=True)
class DaikinOneOpenApiSwitchEntityDescription(SwitchEntityDescription):
    """A custom sensor entity description."""

    value_fn: Callable[[DaikinOneOpenApiThermostatStateResponse], bool | None]
    change_fn: Callable[[DaikinOneOpenApiDataUpdateCoordinator, bool], Awaitable[None]]
    exists_fn: Callable[[DaikinOneOpenApiThermostatStateResponse], bool] = lambda _: (
        True
    )


async def _handle_schedule_enabled_change(
    coordinator: DaikinOneOpenApiDataUpdateCoordinator,
    desired_state: bool,  # noqa: FBT001
) -> None:
    """Handle schedule enabled change."""
    await coordinator.set_device_schedule(schedule_enabled=desired_state)


def _emergency_heat_available(data: DaikinOneOpenApiThermostatStateResponse) -> bool:
    """Return whether the thermostat offers emergency heat as a mode."""
    return data.mode_em_heat_available == ModeEmergencyHeatAvailable.AVAILABLE


async def _handle_emergency_heat_change(
    coordinator: DaikinOneOpenApiDataUpdateCoordinator,
    desired_state: bool,  # noqa: FBT001
) -> None:
    """Switch between emergency heat and regular heat."""
    if desired_state:
        if not _emergency_heat_available(coordinator.data):
            msg = "Emergency heat is not currently available on this thermostat"
            raise HomeAssistantError(msg)
        await coordinator.set_device_mode_and_setpoints(
            mode=ThermostatMode.EMERGENCY_HEAT
        )
    elif coordinator.data.mode == ThermostatMode.EMERGENCY_HEAT:
        # Turning emergency heat off falls back to regular heat, not off.
        await coordinator.set_device_mode_and_setpoints(mode=ThermostatMode.HEAT)


ENTITY_DESCRIPTIONS = [
    DaikinOneOpenApiSwitchEntityDescription(
        key="schedule_enabled",
        name="Schedule Enabled",
        icon="mdi:calendar",
        value_fn=lambda data: data.schedule_enabled,
        change_fn=_handle_schedule_enabled_change,
    ),
    DaikinOneOpenApiSwitchEntityDescription(
        key="emergency_heat",
        name="Emergency Heat",
        icon="mdi:heating-coil",
        value_fn=lambda data: data.mode == ThermostatMode.EMERGENCY_HEAT,
        change_fn=_handle_emergency_heat_change,
        exists_fn=_emergency_heat_available,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: DaikinOneOpenApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    for device in entry.runtime_data.devices.values():
        async_add_entities(
            [
                DaikinOneOpenApiSwitch(
                    device,
                    entity_description,
                )
                for entity_description in ENTITY_DESCRIPTIONS
                if entity_description.exists_fn(device.coordinator.data)
            ]
        )


class DaikinOneOpenApiSwitch(DaikinOneOpenApiEntity, SwitchEntity):
    """Binary sensor class."""

    entity_description: DaikinOneOpenApiSwitchEntityDescription

    def __init__(
        self,
        device: DaikinOneOpenApiConfigEntryDeviceData,
        entity_description: DaikinOneOpenApiSwitchEntityDescription,
    ) -> None:
        """Initialize the binary sensor class."""
        super().__init__(device)
        self.entity_description = dataclasses.replace(
            entity_description,
            key=f"{device.device_metadata.id}_{entity_description.key}",
            name=f"{device.device_metadata.name} {entity_description.name}",
        )

        self._attr_unique_id = self.entity_description.key

    @property
    def is_on(self) -> bool | None:
        """Return the value of the switch."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn on the switch."""
        await self.entity_description.change_fn(self.coordinator, True)  # noqa: FBT003

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Turn off the switch."""
        await self.entity_description.change_fn(self.coordinator, False)  # noqa: FBT003
