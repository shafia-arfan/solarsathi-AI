from simulation.energy import summarize, detect_warnings
from simulation.scenarios import build_scenario


def test_normal_day_is_boring():
    df = build_scenario("normal_day")
    assert detect_warnings(df) == []
    s = summarize(df)
    assert s["outage_hours"] == 0 and s["unserved_kwh"] == 0


def test_load_shedding_battery_copes_but_cycles_more():
    df = build_scenario("load_shedding")
    s, n = summarize(df), summarize(build_scenario("normal_day"))
    assert s["outage_hours"] == 6
    assert s["unserved_kwh"] == 0
    assert s["min_soc_pct"] < n["min_soc_pct"]
    assert s["battery_equiv_cycles"] > n["battery_equiv_cycles"]


def test_battery_warning_raises_all_expected_flags():
    df = build_scenario("battery_warning")
    assert set(detect_warnings(df)) == {"LOW_SOC", "HIGH_TEMP", "LOW_VOLTAGE", "UNSERVED_LOAD"}
    assert summarize(df)["unserved_kwh"] > 0
