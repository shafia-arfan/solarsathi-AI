from simulation.checks import check_report
from simulation.energy import summarize, detect_warnings
from simulation.scenarios import build_scenario

df = build_scenario("battery_warning")
FACTS = {**summarize(df), "flags": detect_warnings(df)}
FLAGS = FACTS["flags"]

GOOD = (f"Battery fell to {FACTS['min_soc_pct']}% charge (LOW_SOC) and reached "
        f"{FACTS['max_temp_c']} C (HIGH_TEMP). Voltage dropped to {FACTS['min_voltage_v']} V "
        f"(LOW_VOLTAGE), so {FACTS['unserved_kwh']} kWh of load was not served (UNSERVED_LOAD). "
        "Recommend charging before the 19:00 outage.")


def test_good_report_passes():
    assert check_report(GOOD, FACTS, FLAGS) == []


def test_hallucinated_number_is_caught():
    bad = GOOD.replace(str(FACTS["max_temp_c"]), "73.4")
    assert any("73.4" in p for p in check_report(bad, FACTS, FLAGS))


def test_missing_warning_is_caught():
    bad = GOOD.replace("HIGH_TEMP", "something").replace("C (", "C (")
    assert any("HIGH_TEMP" in p for p in check_report(bad, FACTS, FLAGS))


def test_empty_report_is_caught():
    assert check_report("", FACTS, FLAGS)
