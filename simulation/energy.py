"""simulation/energy.py - pure-Python energy maths. No LLM, no internet needed."""
import numpy as np
import pandas as pd

# Illustrative home-scale battery (48 V, 10 kWh). Change here, nowhere else.
BATTERY = dict(capacity_kwh=10.0, max_kw=3.0, soc_min=10.0, soc_max=100.0, eff=0.95)
THRESHOLDS = dict(low_soc=20.0, high_temp=45.0, low_voltage=44.0)


def simulate(load_kw, solar_kw, grid_on, soc0=80.0, grid_charge_to=90.0,
             ambient_c=None, battery=None, dt_h=1.0) -> pd.DataFrame:
    """Hour-by-hour dispatch. Rules:
    1) Solar serves the load first; any surplus charges the battery (rest is curtailed).
    2) If solar is short and the grid is ON: grid serves the load and tops the battery up.
    3) If solar is short and the grid is OFF (load-shedding): battery serves the load;
       whatever it cannot supply is 'unserved'.
    """
    b = {**BATTERY, **(battery or {})}
    cap, pmax, smin, smax, eff = (b["capacity_kwh"], b["max_kw"], b["soc_min"],
                                  b["soc_max"], b["eff"])
    n = len(load_kw)
    ambient = np.full(n, 30.0) if ambient_c is None else np.asarray(ambient_c, float)
    soc = float(soc0)
    rows = []
    for i in range(n):
        load, sol, grid_ok = float(load_kw[i]), float(solar_kw[i]), bool(grid_on[i])
        charge = discharge = grid = unserved = curtailed = 0.0
        room_kw = max(0.0, (smax - soc) / 100 * cap / (eff * dt_h))  # charge power that fits
        if sol >= load:                                   # rule 1
            surplus = sol - load
            charge = min(surplus, pmax, room_kw)
            curtailed = surplus - charge
        elif grid_ok:                                     # rule 2
            grid = load - sol
            if soc < grid_charge_to:
                charge = min(pmax, room_kw, (grid_charge_to - soc) / 100 * cap / (eff * dt_h))
                grid += charge
        else:                                             # rule 3
            deficit = load - sol
            avail_kw = max(0.0, (soc - smin) / 100 * cap * eff / dt_h)
            discharge = min(deficit, pmax, avail_kw)
            unserved = deficit - discharge
        soc += (charge * eff - discharge / eff) * dt_h / cap * 100
        rows.append(dict(
            hour=i, load_kw=load, solar_kw=sol, grid_on=int(grid_ok),
            charge_kw=charge, discharge_kw=discharge, grid_kw=grid,
            unserved_kw=unserved, curtailed_kw=curtailed, soc_pct=soc,
            battery_temp_c=ambient[i] + 6 * (charge + discharge) / pmax,
            battery_voltage_v=44 + 8 * soc / 100 - 0.6 * discharge))   # illustrative
    return pd.DataFrame(rows).round(3)


def summarize(df: pd.DataFrame, battery=None, dt_h=1.0) -> dict:
    b = {**BATTERY, **(battery or {})}
    load = df.load_kw.sum() * dt_h
    solar = df.solar_kw.sum() * dt_h
    unserved = df.unserved_kw.sum() * dt_h
    curtailed = df.curtailed_kw.sum() * dt_h
    throughput = (df.charge_kw.sum() + df.discharge_kw.sum()) * dt_h
    out = {
        "total_load_kwh": round(load, 2),
        "total_solar_kwh": round(solar, 2),
        "grid_import_kwh": round(df.grid_kw.sum() * dt_h, 2),
        "unserved_kwh": round(unserved, 2),
        "curtailed_kwh": round(curtailed, 2),
        "peak_load_kw": round(df.load_kw.max(), 2),
        "outage_hours": int((df.grid_on == 0).sum()),
        "min_soc_pct": round(df.soc_pct.min(), 1),
        "end_soc_pct": round(df.soc_pct.iloc[-1], 1),
        "max_temp_c": round(df.battery_temp_c.max(), 1),
        "min_voltage_v": round(df.battery_voltage_v.min(), 1),
        "battery_equiv_cycles": round(throughput / (2 * b["capacity_kwh"]), 2),
        "load_served_pct": round(100 * (load - unserved) / load, 1) if load else 0.0,
        "solar_utilisation_pct": round(100 * (solar - curtailed) / solar, 1) if solar else 0.0,
    }
    return {k: (v if isinstance(v, int) else float(v)) for k, v in out.items()}   # plain Python numbers


def detect_warnings(df: pd.DataFrame, th=None) -> list:
    th = {**THRESHOLDS, **(th or {})}
    flags = []
    if (df.soc_pct < th["low_soc"]).any():
        flags.append("LOW_SOC")
    if (df.battery_temp_c > th["high_temp"]).any():
        flags.append("HIGH_TEMP")
    if (df.battery_voltage_v < th["low_voltage"]).any():
        flags.append("LOW_VOLTAGE")
    if (df.unserved_kw > 0).any():
        flags.append("UNSERVED_LOAD")
    return flags
