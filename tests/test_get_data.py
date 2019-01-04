import logging

import pytest

import aocd
from aocd import AocdError


def test_get_from_server(requests_mock):
    mock = requests_mock.get(
        url="https://adventofcode.com/2018/day/1/input",
        text="fake data for year 2018 day 1",
    )
    data = aocd.get_data(year=2018, day=1)
    assert data == "fake data for year 2018 day 1"
    assert mock.called
    assert mock.call_count == 1


def test_get_data_uses_current_date_if_unspecified(requests_mock, freezer):
    mock = requests_mock.get(
        url="https://adventofcode.com/2017/day/17/input",
        text="fake data for year 2017 day 17",
    )
    freezer.move_to("2017-12-17 12:00:00Z")
    data = aocd.get_data()
    assert data == "fake data for year 2017 day 17"
    assert mock.called
    assert mock.call_count == 1


def test_saved_data_is_reused_if_available(tmpdir, requests_mock):
    mock = requests_mock.get(
        url="https://adventofcode.com/2018/day/1/input",
        text="fake data for year 2018 day 1",
    )
    cached = tmpdir / ".config/aocd/thetesttoken/2018/1.txt"
    cached.ensure(file=True)
    cached.write("saved data for year 2018 day 1")
    data = aocd.get_data(year=2018, day=1)
    assert data == "saved data for year 2018 day 1"
    assert not mock.called


def test_server_error(requests_mock, caplog):
    mock = requests_mock.get(
        url="https://adventofcode.com/2101/day/1/input",
        text='Not Found',
        status_code=404,
    )
    with pytest.raises(AocdError("Unexpected response")):
        aocd.get_data(year=2101, day=1)
    assert mock.called
    assert mock.call_count == 1
    assert caplog.record_tuples == [
        ('aocd', logging.ERROR, 'got 404 status code'),
        ('aocd', logging.ERROR, 'Not Found'),
    ]


def test_session_token_in_req_headers(requests_mock):
    mock = requests_mock.get("https://adventofcode.com/2018/day/1/input")
    aocd.get_data(year=2018, day=1)
    assert mock.call_count == 1
    headers = mock.last_request._request.headers
    assert headers["Cookie"] == "session=thetesttoken"


def test_aocd_user_agent_in_req_headers(requests_mock):
    mock = requests_mock.get("https://adventofcode.com/2018/day/1/input")
    aocd.get_data(year=2018, day=1)
    assert mock.call_count == 1
    headers = mock.last_request._request.headers
    assert headers["User-Agent"] == "aocd.py/v{}".format(aocd.__version__)


def test_data_is_cached_from_successful_request(tmpdir, requests_mock):
    requests_mock.get(
        url="https://adventofcode.com/2018/day/1/input",
        text="fake data for year 2018 day 1",
    )
    cached = tmpdir / ".config/aocd/thetesttoken/2018/1.txt"
    assert not cached.exists()
    aocd.get_data(year=2018, day=1)
    assert cached.exists()
    assert cached.read() == "fake data for year 2018 day 1"


def test_rate_limit(tmpdir, requests_mock, capsys, mocked_sleep, freezer):
    requests_mock.get(
        "https://adventofcode.com/2018/day/1/input",
        [{"text": "first request"}, {"text": "second request"}],
    )
    cached = tmpdir / ".config/aocd/thetesttoken/2018/1.txt"
    freezer.move_to("2018-12-01 12:00:00.000Z")
    data1 = aocd.get_data(year=2018, day=1)
    cached.remove()
    freezer.move_to("2018-12-01 12:00:00.5000Z")
    data2 = aocd.get_data(year=2018, day=1)
    assert data1 == "first request"
    assert data2 == "second request"
    mocked_sleep.assert_called_with(.5)
    out, err = capsys.readouterr()
    assert "You are being rate-limited" in out
    assert "Sleeping 0.5 seconds..." in out


def test_saved_data_multitenancy(tmpdir):
    cachedA = tmpdir / ".config/aocd/tokenA/2018/1.txt"
    cachedB = tmpdir / ".config/aocd/tokenB/2018/1.txt"
    cachedA.ensure(file=True)
    cachedA.write("data for user A")
    cachedB.ensure(file=True)
    cachedB.write("data for user B")
    data = aocd.get_data(session="tokenB", year=2018, day=1)
    assert data == "data for user B"


def test_corrupted_cache(tmpdir):
    cached = tmpdir / ".config/aocd/thetesttoken/2018/1.txt"
    cached.ensure_dir()
    with pytest.raises(IOError):
        aocd.get_data(year=2018, day=1)


# def test_problem_creating_saved_copy(tmpdir, requests_mock):
#     cached = tmpdir / ".config/aocd/thetesttoken/2018/1.txt"
#     with pytest.raises(AocdError):
#         aocd.get_data(session="whatever", year=2018, day=1)