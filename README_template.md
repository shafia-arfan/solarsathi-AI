# 🔋 Battery AI Pro & Power System

AI crew (CrewAI) that analyses battery and power-system data, finds faults, and writes a report.
Live app: <paste Streamlit URL here>

## Quick start
```bash
git clone https://github.com/<leader-username>/battery-ai-pro.git
cd battery-ai-pro
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # only if you want to run tests
streamlit run app.py
```
Secrets: create `.streamlit/secrets.toml` (never commit it):
```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "your-key"
```

## Sample data and scenarios
| File (data/scenarios/) | Story | Expected warnings |
|---|---|---|
| normal_day.csv | Grid on all day, sunny | none |
| load_shedding.csv | 3 x 2 h outages, battery covers them | none (battery copes) |
| battery_warning.csv | Low charge, heat wave, evening outage | LOW_SOC, HIGH_TEMP, LOW_VOLTAGE, UNSERVED_LOAD |

Regenerate: `python -m simulation.scenarios`   |   Run tests: `pytest -q`

## Data dictionary
hour (0-23), load_kw, solar_kw, grid_on (1/0), charge_kw, discharge_kw, grid_kw,
unserved_kw (load not served), curtailed_kw (solar wasted), soc_pct, battery_temp_c, battery_voltage_v

## How the numbers are produced
Rules and battery settings live in `simulation/energy.py`. All data is simulated and illustrative, not measured.

## Project structure
(paste the tree here) | Team and roles | Known issues | Roadmap
