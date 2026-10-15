"""Sensor platform for daikin_one_open_api."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import UnitOfTemperature

from .api_types import EquipmentStatus, FanCirculateSchedule, ThermostatMode
from .entity import DaikinOneOpenApiEntity

if TYPE_CHECKING:
    from enum import IntFlag

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .data import DaikinOneOpenApiConfigEntry, DaikinOneOpenApiConfigEntryDeviceData

FAN_AUTO = "Auto"
FAN_ON = "On"
FAN_SCHEDULE = "Schedule"


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: DaikinOneOpenApiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform."""
    for device in entry.runtime_data.devices.values():
        async_add_entities(
            [
                DaikinOneOpenApiClimate(
                    device,
                )
            ]
        )


class DaikinOneOpenApiClimate(DaikinOneOpenApiEntity, ClimateEntity):
    """Climate class."""

    def __init__(
        self,
        device: DaikinOneOpenApiConfigEntryDeviceData,
    ) -> None:
        """Initialize the climate class."""
        super().__init__(device)

        self._attr_unique_id = f"{device.device_metadata.id}_climate"

        self._attr_name = device.device_metadata.name
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.AUTO,
        ]
        self._attr_fan_modes = [FAN_AUTO, FAN_ON, FAN_SCHEDULE]
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            | ClimateEntityFeature.FAN_MODE
        )

    @property
    def supported_features(self) -> IntFlag:
        """Get supported features."""
        supported_features = ClimateEntityFeature.FAN_MODE

        if self.coordinator.data.mode in (
            ThermostatMode.COOL,
            ThermostatMode.HEAT,
            ThermostatMode.EMERGENCY_HEAT,
        ):
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE

        if self.coordinator.data.mode == ThermostatMode.AUTO:
            supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

        return supported_features

    @property
    def current_temperature(self) -> float | None:
        """Get current temperature."""
        return self.coordinator.data.temp_indoor

    @property
    def max_temp(self) -> float | None:
        """Get max temperature."""
        return self.coordinator.data.setpoint_maximum

    @property
    def min_temp(self) -> float | None:
        """Get min temperature."""
        return self.coordinator.data.setpoint_minimum

    @property
    def current_humidity(self) -> float | None:
        """Get current humidity."""
        return self.coordinator.data.hum_indoor

    @property
    def fan_mode(self) -> str | None:
        """Get current fan mode."""
        if self.coordinator.data.fan_circulate == FanCirculateSchedule.OFF:
            return FAN_AUTO
        if self.coordinator.data.fan_circulate == FanCirculateSchedule.ALWAYS_ON:
            return FAN_ON
        if self.coordinator.data.fan_circulate == FanCirculateSchedule.SCHEDULE:
            return FAN_SCHEDULE

        return FAN_AUTO

    @property
    def hvac_action(self) -> HVACAction | None:  # noqa: PLR0911
        """Get current hvac action."""
        if self.coordinator.data.equipment_status == EquipmentStatus.UNKNOWN:
            return HVACAction.OFF
        if self.coordinator.data.equipment_status == EquipmentStatus.IDLE:
            return HVACAction.IDLE
        if self.coordinator.data.equipment_status == EquipmentStatus.COOL:
            return HVACAction.COOLING
        if self.coordinator.data.equipment_status == EquipmentStatus.HEAT:
            return HVACAction.HEATING
        if self.coordinator.data.equipment_status == EquipmentStatus.FAN:
            return HVACAction.FAN
        if (
            self.coordinator.data.equipment_status
            == EquipmentStatus.OVERCOOL_FOR_DEHUMIDIFY
        ):
            return HVACAction.DRYING

        return HVACAction.OFF

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Get current hvac mode."""
        if self.coordinator.data.mode == ThermostatMode.OFF:
            return HVACMode.OFF
        if self.coordinator.data.mode == ThermostatMode.COOL:
            return HVACMode.COOL
        if self.coordinator.data.mode == ThermostatMode.HEAT:
            return HVACMode.HEAT
        if self.coordinator.data.mode == ThermostatMode.EMERGENCY_HEAT:
            return HVACMode.HEAT
        if self.coordinator.data.mode == ThermostatMode.AUTO:
            return HVACMode.AUTO

        return HVACMode.OFF

    @property
    def target_temperature(self) -> float | None:
        """Get current hvac target temperature."""
        if self.coordinator.data.mode in (
            ThermostatMode.HEAT,
            ThermostatMode.EMERGENCY_HEAT,
        ):
            return self.coordinator.data.heat_setpoint
        if self.coordinator.data.mode == ThermostatMode.COOL:
            return self.coordinator.data.cool_setpoint
        return None

    @property
    def target_temperature_high(self) -> float | None:
        """Get current hvac high target temperature."""
        return self.coordinator.data.cool_setpoint

    @property
    def target_temperature_low(self) -> float | None:
        """Get current hvac low target temperature."""
        return self.coordinator.data.heat_setpoint

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.set_device_mode_and_setpoints(
                mode=ThermostatMode.OFF
            )
        if hvac_mode == HVACMode.COOL:
            await self.coordinator.set_device_mode_and_setpoints(
                mode=ThermostatMode.COOL
            )
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.set_device_mode_and_setpoints(
                mode=ThermostatMode.HEAT
            )
        if hvac_mode == HVACMode.AUTO:
            await self.coordinator.set_device_mode_and_setpoints(
                mode=ThermostatMode.AUTO
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        if fan_mode == FAN_AUTO:
            await self.coordinator.set_device_fan_mode(
                fan_circulate=FanCirculateSchedule.OFF
            )
        if fan_mode == FAN_ON:
            await self.coordinator.set_device_fan_mode(
                fan_circulate=FanCirculateSchedule.ALWAYS_ON
            )
        if fan_mode == FAN_SCHEDULE:
            await self.coordinator.set_device_fan_mode(
                fan_circulate=FanCirculateSchedule.SCHEDULE
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the temperature."""
        if "temperature" in kwargs:
            if self.coordinator.data.mode in (
                ThermostatMode.HEAT,
                ThermostatMode.EMERGENCY_HEAT,
            ):
                await self.coordinator.set_device_mode_and_setpoints(
                    heat_setpoint=kwargs["temperature"],
                )
                return

            if self.coordinator.data.mode == ThermostatMode.COOL:
                await self.coordinator.set_device_mode_and_setpoints(
                    cool_setpoint=kwargs["temperature"],
                )
                return
        if (
            "target_temp_low" in kwargs
            and "target_temp_high" in kwargs
            and self.coordinator.data.mode == ThermostatMode.AUTO
        ):
            await self.coordinator.set_device_mode_and_setpoints(
                heat_setpoint=kwargs["target_temp_low"],
                cool_setpoint=kwargs["target_temp_high"],
            )

        msg = "Bad state."
        raise RuntimeError(msg)
