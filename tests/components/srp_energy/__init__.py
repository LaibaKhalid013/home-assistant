"""Tests for the SRP Energy integration."""

from homeassistant.components.srp_energy import CONF_IS_TOU
from homeassistant.const import CONF_ID, CONF_PASSWORD, CONF_USERNAME

PHOENIX_TIME_ZONE = "America/Phoenix"

ACCNT_ID = "123456789"
ACCNT_ID_2 = "987654321"
ACCNT_IS_TOU = False
ACCNT_PASSWORD = "ana"
ACCNT_USERNAME = "abba"

TEST_USER_INPUT = {
    CONF_ID: ACCNT_ID,
    CONF_USERNAME: ACCNT_USERNAME,
    CONF_PASSWORD: ACCNT_PASSWORD,
    CONF_IS_TOU: ACCNT_IS_TOU,
}

TEST_USER_INPUT_2 = {
    CONF_ID: ACCNT_ID_2,
    CONF_USERNAME: ACCNT_USERNAME,
    CONF_PASSWORD: ACCNT_PASSWORD,
    CONF_IS_TOU: ACCNT_IS_TOU,
}

ENTRY_OPTIONS: dict[str, str] = {}

MOCK_USAGE = [
    ("7/31/2022", "00:00 AM", "2022-07-31T00:00:00", "1.2", "0.19"),
    ("7/31/2022", "01:00 AM", "2022-07-31T01:00:00", "1.3", "0.20"),
    ("7/31/2022", "02:00 AM", "2022-07-31T02:00:00", "1.1", "0.17"),
    ("7/31/2022", "03:00 AM", "2022-07-31T03:00:00", "1.2", "0.18"),
    ("7/31/2022", "04:00 AM", "2022-07-31T04:00:00", "0.8", "0.13"),
    ("7/31/2022", "05:00 AM", "2022-07-31T05:00:00", "0.9", "0.14"),
    ("7/31/2022", "06:00 AM", "2022-07-31T06:00:00", "1.6", "0.24"),
    ("7/31/2022", "07:00 AM", "2022-07-31T07:00:00", "3.7", "0.53"),
    ("7/31/2022", "08:00 AM", "2022-07-31T08:00:00", "1.0", "0.16"),
    ("7/31/2022", "09:00 AM", "2022-07-31T09:00:00", "0.7", "0.12"),
    ("7/31/2022", "10:00 AM", "2022-07-31T10:00:00", "1.9", "0.28"),
    ("7/31/2022", "11:00 AM", "2022-07-31T11:00:00", "4.3", "0.61"),
    ("7/31/2022", "12:00 PM", "2022-07-31T12:00:00", "2.0", "0.29"),
    ("7/31/2022", "01:00 PM", "2022-07-31T13:00:00", "3.9", "0.55"),
    ("7/31/2022", "02:00 PM", "2022-07-31T14:00:00", "5.3", "0.75"),
    ("7/31/2022", "03:00 PM", "2022-07-31T15:00:00", "5.0", "0.70"),
    ("7/31/2022", "04:00 PM", "2022-07-31T16:00:00", "2.2", "0.31"),
    ("7/31/2022", "05:00 PM", "2022-07-31T17:00:00", "2.6", "0.37"),
    ("7/31/2022", "06:00 PM", "2022-07-31T18:00:00", "4.5", "0.64"),
    ("7/31/2022", "07:00 PM", "2022-07-31T19:00:00", "2.5", "0.35"),
    ("7/31/2022", "08:00 PM", "2022-07-31T20:00:00", "2.9", "0.42"),
    ("7/31/2022", "09:00 PM", "2022-07-31T21:00:00", "2.2", "0.32"),
    ("7/31/2022", "10:00 PM", "2022-07-31T22:00:00", "2.1", "0.30"),
    ("7/31/2022", "11:00 PM", "2022-07-31T23:00:00", "2.0", "0.28"),
    ("8/01/2022", "00:00 AM", "2022-08-01T00:00:00", "1.8", "0.26"),
    ("8/01/2022", "01:00 AM", "2022-08-01T01:00:00", "1.7", "0.26"),
    ("8/01/2022", "02:00 AM", "2022-08-01T02:00:00", "1.7", "0.26"),
    ("8/01/2022", "03:00 AM", "2022-08-01T03:00:00", "0.8", "0.14"),
    ("8/01/2022", "04:00 AM", "2022-08-01T04:00:00", "1.2", "0.19"),
    ("8/01/2022", "05:00 AM", "2022-08-01T05:00:00", "1.6", "0.23"),
    ("8/01/2022", "06:00 AM", "2022-08-01T06:00:00", "1.2", "0.18"),
    ("8/01/2022", "07:00 AM", "2022-08-01T07:00:00", "3.1", "0.44"),
    ("8/01/2022", "08:00 AM", "2022-08-01T08:00:00", "2.5", "0.35"),
    ("8/01/2022", "09:00 AM", "2022-08-01T09:00:00", "3.3", "0.47"),
    ("8/01/2022", "10:00 AM", "2022-08-01T10:00:00", "2.6", "0.37"),
    ("8/01/2022", "11:00 AM", "2022-08-01T11:00:00", "0.8", "0.13"),
    ("8/01/2022", "12:00 PM", "2022-08-01T12:00:00", "0.6", "0.11"),
    ("8/01/2022", "01:00 PM", "2022-08-01T13:00:00", "6.4", "0.9"),
    ("8/01/2022", "02:00 PM", "2022-08-01T14:00:00", "3.6", "0.52"),
    ("8/01/2022", "03:00 PM", "2022-08-01T15:00:00", "5.5", "0.79"),
    ("8/01/2022", "04:00 PM", "2022-08-01T16:00:00", "3", "0.43"),
    ("8/01/2022", "05:00 PM", "2022-08-01T17:00:00", "5", "0.71"),
    ("8/01/2022", "06:00 PM", "2022-08-01T18:00:00", "4.4", "0.63"),
    ("8/01/2022", "07:00 PM", "2022-08-01T19:00:00", "3.8", "0.54"),
    ("8/01/2022", "08:00 PM", "2022-08-01T20:00:00", "3.6", "0.51"),
    ("8/01/2022", "09:00 PM", "2022-08-01T21:00:00", "2.9", "0.4"),
    ("8/01/2022", "10:00 PM", "2022-08-01T22:00:00", "3.4", "0.49"),
    ("8/01/2022", "11:00 PM", "2022-08-01T23:00:00", "2.9", "0.41"),
    ("8/02/2022", "00:00 AM", "2022-08-02T00:00:00", "2", "0.3"),
    ("8/02/2022", "01:00 AM", "2022-08-02T01:00:00", "2", "0.29"),
    ("8/02/2022", "02:00 AM", "2022-08-02T02:00:00", "1.9", "0.28"),
    ("8/02/2022", "03:00 AM", "2022-08-02T03:00:00", "1.8", "0.27"),
    ("8/02/2022", "04:00 AM", "2022-08-02T04:00:00", "1.8", "0.26"),
    ("8/02/2022", "05:00 AM", "2022-08-02T05:00:00", "1.6", "0.23"),
    ("8/02/2022", "06:00 AM", "2022-08-02T06:00:00", "0.8", "0.14"),
    ("8/02/2022", "07:00 AM", "2022-08-02T07:00:00", "4", "0.56"),
    ("8/02/2022", "08:00 AM", "2022-08-02T08:00:00", "2.4", "0.34"),
    ("8/02/2022", "09:00 AM", "2022-08-02T09:00:00", "4.1", "0.58"),
    ("8/02/2022", "10:00 AM", "2022-08-02T10:00:00", "2.6", "0.37"),
    ("8/02/2022", "11:00 AM", "2022-08-02T11:00:00", "0.5", "0.1"),
    ("8/02/2022", "00:00 AM", "2022-08-02T12:00:00", "1", "0.16"),
]
