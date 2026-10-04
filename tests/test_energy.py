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
    df = build_scenario(name)
    sources = df.solar_kw + df.grid_kw + df.discharge_kw
    sinks = (df.load_kw - df.unserved_kw) + df.charge_kw + df.curtailed_kw
    assert np.allclose(sources, sinks, atol=0.01)

@pytest.mark.parametrize("name", NAMES)
def test_battery_never_charges_and_discharges_together(name):
    df = build_scenario(name)
    assert not ((df.charge_kw > 0) & (df.discharge_kw > 0)).any()

def test_hand_calculated_case():
    df = simulate([2.0], [0.0], [0], soc0=50.0)
    assert df.discharge_kw[0] == pytest.approx(2.0)
    assert df.soc_pct[0] == pytest.approx(50 - 2.0 / 0.95 / 10 * 100, abs=0.01)
    assert df.unserved_kw[0] == 0

def test_empty_battery_causes_unserved_load():
    df = simulate([2.0], [0.0], [0], soc0=10.0)
    assert df.unserved_kw[0] == pytest.approx(2.0)
