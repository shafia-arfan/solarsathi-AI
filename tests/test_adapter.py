import pytest
from simulation.adapter import to_telemetry, expected_flows
from simulation.scenarios import build_scenario, NAMES


@pytest.mark.parametrize("name", NAMES)
def test_flows_add_up_to_served_load(name):
    df = build_scenario(name)
    for r, f in zip(df.itertuples(), expected_flows(df)):
        served = f["solar_to_load"] + f["battery_to_load"] + f["grid_to_load"]
        assert abs(served - (r.load_kw - r.unserved_kw)) < 0.01


@pytest.mark.parametrize("name", NAMES)
def test_rows_match_team_schema(name):
    try:
        from models.schemas import TelemetryInput      # the team's file
    except ImportError:
        pytest.skip("models.schemas not importable (run tests from the repo root)")
    rows = to_telemetry(build_scenario(name), name)
    assert len(rows) == 24
    for row in rows:
        TelemetryInput(**row)                          # raises if a field is wrong


def test_outage_hours_marked_as_load_shedding():
    rows = to_telemetry(build_scenario("load_shedding"), "load_shedding")
    assert sum(r["load_shedding"] for r in rows) == 6
    assert all(r["load_shedding"] != r["grid_available"] for r in rows)
