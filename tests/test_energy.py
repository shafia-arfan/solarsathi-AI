import numpy as np
import pytest
from simulation.energy import simulate, summarize, detect_warnings, BATTERY
from simulation.scenarios import build_scenario, NAMES


@pytest.mark.parametrize("name", NAMES)
def test_scenario_shape_and_no_nans(name):
    df = build_scenario(name)
    assert len(df) == 24
    assert not df.isna().any().any()
    assert (df[["load_kw", "solar_kw"]] >= 0).all().all()


@pytest.mark.parametrize("name", NAMES)
def test_soc_stays_inside_limits(name):
    df = build_scenario(name)
    assert df.soc_pct.min() >= BATTERY["soc_min"] - 0.01
    assert df.soc_pct.max() <= BATTERY["soc_max"] + 0.01


@pytest.mark.parametrize("name", NAMES)
def test_energy_balance_every_hour(name):
    """sources (solar+grid+discharge) = sinks (served load+charge+curtailed)"""
    df = build_scenario(name)
    sources = df.solar_kw + df.grid_kw + df.discharge_kw
    sinks = (df.load_kw - df.unserved_kw) + df.charge_kw + df.curtailed_kw
    assert np.allclose(sources, sinks, atol=0.01)


@pytest.mark.parametrize("name", NAMES)
def test_battery_never_charges_and_discharges_together(name):
    df = build_scenario(name)
    assert not ((df.charge_kw > 0) & (df.discharge_kw > 0)).any()


def test_same_seed_gives_same_data():
    assert build_scenario("load_shedding", seed=1).equals(build_scenario("load_shedding", seed=1))


def test_hand_calculated_case():
    # 1 hour, 2 kW load, no solar, grid OFF, battery at 50% of 10 kWh, eff 0.95
    df = simulate([2.0], [0.0], [0], soc0=50.0)
    assert df.discharge_kw[0] == pytest.approx(2.0)
    assert df.soc_pct[0] == pytest.approx(50 - 2.0 / 0.95 / 10 * 100, abs=0.01)  # 28.95
    assert df.unserved_kw[0] == 0


def test_empty_battery_causes_unserved_load():
    df = simulate([2.0], [0.0], [0], soc0=10.0)       # already at the floor
    assert df.unserved_kw[0] == pytest.approx(2.0)


def test_summary_numbers_are_plain_python():
    s = summarize(build_scenario("normal_day"))
    assert all(type(v) in (int, float) for v in s.values())
