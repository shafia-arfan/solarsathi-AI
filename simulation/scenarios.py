"""simulation/scenarios.py - builds the three demo scenarios (same seed = same data)."""
import json
from pathlib import Path
import numpy as np
from simulation.energy import simulate, summarize, detect_warnings

HOURS = np.arange(24)
OUTAGE_HOURS = [10, 11, 14, 15, 20, 21]      # illustrative 3 x 2-hour load-shedding blocks
NAMES = ["normal_day", "load_shedding", "battery_warning"]


def load_profile(rng, base_kw=1.0, peak_kw=3.0):
    morning = np.exp(-((HOURS - 8) ** 2) / (2 * 1.5 ** 2))
    evening = np.exp(-((HOURS - 20) ** 2) / (2 * 2.0 ** 2))
    load = base_kw + (peak_kw - base_kw) * (0.6 * morning + evening)
    return load * np.clip(1 + rng.normal(0, 0.08, 24), 0.5, None)


def solar_profile(rng, peak_kw=4.0, cloud=0.0):
    sun = np.clip(np.sin(np.pi * (HOURS - 6) / 12), 0, None)
    return peak_kw * sun * (1 - cloud) * np.clip(1 + rng.normal(0, 0.05, 24), 0, None)


def build_scenario(name: str, seed: int = 42):
    rng = np.random.default_rng(seed)
    load = load_profile(rng)
    ambient = 28 + 5 * np.sin(np.pi * (HOURS - 8) / 12)      # warmest mid-afternoon
    if name == "normal_day":
        solar, grid, soc0 = solar_profile(rng), np.ones(24, int), 60.0
    elif name == "load_shedding":
        solar, soc0 = solar_profile(rng, cloud=0.1), 70.0
        grid = np.ones(24, int)
        grid[OUTAGE_HOURS] = 0
    elif name == "battery_warning":
        solar, soc0 = solar_profile(rng, cloud=0.5), 25.0
        ambient = ambient + 10                                # heat wave
        grid = np.ones(24, int)
        grid[19:23] = 0                                       # evening outage, low SOC
    else:
        raise ValueError(f"Unknown scenario: {name}")
    df = simulate(load, solar, grid, soc0=soc0, ambient_c=ambient)
    if name == "battery_warning":
        df.loc[df.hour.between(13, 16), "battery_temp_c"] += 8   # injected thermal event
    return df


if __name__ == "__main__":
    out = Path("data/scenarios")
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for n in NAMES:
        d = build_scenario(n)
        d.to_csv(out / f"{n}.csv", index=False)
        report[n] = {"flags": detect_warnings(d), "summary": summarize(d)}
        print(n, report[n]["flags"], report[n]["summary"])
    (out / "scenario_summary.json").write_text(json.dumps(report, indent=2))
