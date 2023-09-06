"""Test FlexMeasures integration services."""

from datetime import datetime
from unittest.mock import patch

import pandas as pd

from homeassistant.components.flexmeasures.const import (
    DOMAIN,
    RESOLUTION,
    SERVICE_CHANGE_CONTROL_TYPE,
)
from homeassistant.components.flexmeasures.helpers import time_ceil
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util


async def test_change_control_type_service(
    hass: HomeAssistant, setup_fm_integration
) -> None:
    """Test that the method activate_control_type is called when calling the service active_control_type."""
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CHANGE_CONTROL_TYPE,
        service_data={"control_type": "NO_SELECTION"},
        blocking=True,
    )


async def test_trigger_and_get_schedule(
    hass: HomeAssistant, setup_fm_integration
) -> None:
    """Test that the method trigger_and_get_schedule is awaited when calling the service trigger_and_get_schedule."""
    with patch(
        "flexmeasures_client.client.FlexMeasuresClient.trigger_and_get_schedule",
        return_value={"values": [0.5, 0.41492, -0.0, -0.0]},
    ) as mocked_FlexmeasuresClient:
        await hass.services.async_call(
            DOMAIN,
            "trigger_and_get_schedule",
            service_data={"soc_at_start": 10},
            blocking=True,
        )
        tzinfo = dt_util.get_time_zone(hass.config.time_zone)
        mocked_FlexmeasuresClient.assert_awaited_with(
            sensor_id=1,
            start=time_ceil(datetime.now(tz=tzinfo), pd.Timedelta(RESOLUTION)),
            duration="PT24H",
            soc_unit="MWh",
            soc_min=0.0,
            soc_max=0.001,
            consumption_price_sensor=2,
            production_price_sensor=2,
            soc_at_start=10,
        )


async def test_post_measurements(hass: HomeAssistant, setup_fm_integration) -> None:
    """Test that the method post measuresments is called when calling the service post_measurements."""

    with patch(
        "flexmeasures_client.client.FlexMeasuresClient.post_measurements",
        return_value=None,
    ) as mocked_FlexmeasuresClient:
        await hass.services.async_call(
            DOMAIN,
            "post_measurements",
            service_data={
                "sensor_id": 1,
                "start": None,
                "duration": "PT24H",
                "values": [1, 1, 1, 3],
                "unit": "kWh",
                "prior": None,
            },
            blocking=True,
        )
        mocked_FlexmeasuresClient.assert_called_with(
            sensor_id=1,
            start=None,
            duration="PT24H",
            values=[1, 1, 1, 3],
            unit="kWh",
            prior=None,
        )
