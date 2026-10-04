"""simulation/adapter.py - turns scenario rows into the team's TelemetryInput format
(models/schemas.py) and gives reference power flows for testing the energy planner.
Run:  python -m simulation.adapter   -> writes data/scenarios/telemetry_<name>.json"""
import json
from pathlib import Path
from simulation.energy import BATTERY
from simulation.scenarios import NAMES, build_scenario

# Battery-health fields do not change hour to hour, so each scenario gets one set.
# Values are ILLUSTRATIVE - agree thresholds with the teammate who owns tools/.
HEALTH = {
    "normal_day":      dict(battery_age_years=1.0, battery_internal_res_mohm=60.0,
                            rated_capacity_ah=200.0, actual_capacity_ah=190.0),
    "load_shedding":   dict(battery_age_years=2.5, battery_internal_res_mohm=85.0,
                            rated_capacity_ah=200.0, actual_capacity_ah=176.0),
    "battery_warning": dict(battery_age_years=5.0, battery_internal_res_mohm=140.0,
                            rated_capacity_ah=200.0, actual_capacity_ah=138.0),
}


def to_telemetry(df, name):
    """One dict per hour. Each dict works as TelemetryInput(**row)."""
    rows = []
    for r in df.itertuples():
        rows.append(dict(
            pv_generation_kw=float(r.solar_kw),
            load_demand_kw=float(r.load_kw),
            battery_soc=min(100.0, max(0.0, float(r.soc_pct))),
            battery_capacity_kwh=float(BATTERY["capacity_kwh"]),
            battery_temp_c=float(r.battery_temp_c),
            **HEALTH[name],
            grid_available=bool(r.grid_on),
            load_shedding=not bool(r.grid_on),   # in our scenarios every outage is load-shedding
        ))
    return rows


def expected_flows(df):
    """Reference power flows per hour, same keys as EnergyPlan.power_flows.
    solar_to_grid is always 0 because this simulation does not export (surplus is curtailed)."""
    out = []
    for r in df.itertuples():
        deficit = r.load_kw - r.solar_kw
        out.append(dict(
            solar_to_load=round(min(r.load_kw, r.solar_kw), 3),
            solar_to_battery=round(r.charge_kw if deficit <= 0 else 0.0, 3),
            battery_to_load=round(r.discharge_kw, 3),
            grid_to_load=round(deficit if (r.grid_on and deficit > 0) else 0.0, 3),
            solar_to_grid=0.0))
    return out


if __name__ == "__main__":
    out = Path("data/scenarios")
    for n in NAMES:
        (out / f"telemetry_{n}.json").write_text(json.dumps(to_telemetry(build_scenario(n), n), indent=1))
        print("wrote", f"telemetry_{n}.json")
