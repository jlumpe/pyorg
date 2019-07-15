"""Test the pyorg.util module."""

from datetime import date, datetime, timezone, timedelta

import pytest

from pyorg import util


def test_parse_iso_date():
	"""Test the pyorg.util.parse_iso_date function."""

	assert util.parse_iso_date('2000') == date(2000, 1, 1)
	assert util.parse_iso_date('2000-01') == date(2000, 1, 1)
	assert util.parse_iso_date('2000-01-01') == date(2000, 1, 1)
	assert util.parse_iso_date('2019-07-11') == date(2019, 7, 11)
	assert util.parse_iso_date('2019-07-11T10') == datetime(2019, 7, 11, 10)
	assert util.parse_iso_date('2019-07-11T10:23') == datetime(2019, 7, 11, 10, 23)
	assert util.parse_iso_date('2019-07-11T10:23:42') == datetime(2019, 7, 11, 10, 23, 42)
	assert util.parse_iso_date('2019-07-11T10:23:42.123') == \
	       datetime(2019, 7, 11, 10, 23, 42, 123000)
	assert util.parse_iso_date('2019-07-11T10:23:42.123456') == \
	       datetime(2019, 7, 11, 10, 23, 42, 123456)

	# Time zone
	assert util.parse_iso_date('2019-07-11T10:23Z') == \
	       datetime(2019, 7, 11, 10, 23, tzinfo=timezone.utc)
	assert util.parse_iso_date('2019-07-11T10:23+02:30') == \
	       datetime(2019, 7, 11, 10, 23, tzinfo=timezone(timedelta(hours=2, minutes=30)))
	assert util.parse_iso_date('2019-07-11T10:23-02:30') == \
	       datetime(2019, 7, 11, 10, 23, tzinfo=timezone(-timedelta(hours=2, minutes=30)))

	with pytest.raises(ValueError):
		util.parse_iso_date('foo')
