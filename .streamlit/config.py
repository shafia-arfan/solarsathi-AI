"""Centralized Configuration and Engineering Thresholds for SolarSathi AI."""

# Energy Balance Constraints
MIN_BATTERY_SOC = 20.0          # Critical low cutoff (%)
RESERVE_BATTERY_SOC = 35.0       # Minimum reserve during load shedding (%)
MAX_BATTERY_SOC = 95.0          # Maximum charge cutoff (%)
TRANSFORMER_HIGH_THRESHOLD = 85.0 # Max allowable transformer load (%)

# Battery Health Thresholds
MAX_OPERATING_TEMP_C = 45.0     # Thermal warning threshold (°C)
CRITICAL_TEMP_C = 55.0          # Critical thermal runaway risk (°C)
NORMAL_INTERNAL_RES_MOHM = 25.0 # Baseline healthy internal resistance (mOhm)
HIGH_INTERNAL_RES_MOHM = 50.0   # Degraded internal resistance threshold (mOhm)
MAX_BATTERY_AGE_YEARS = 4.0     # Expected warranty/degradation lifecycle (years)
CRITICAL_SOH_SCORE = 50.0       # SOH score below which battery is Critical
WARNING_SOH_SCORE = 75.0        # SOH score below which battery is Warning

# Free-Tier Gemini Model Defaults
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
FALLBACK_GEMINI_MODEL = "gemini-1.5-flash"

# Demo Scenarios Data
DEMO_SCENARIOS = {
    "Sunny Day": {
        "pv_generation_kw": 6.8,
        "load_demand_kw": 2.2,
        "battery_soc": 65.0,
        "battery_capacity_kwh": 10.0,
        "battery_age_years": 1.0,
        "battery_temp_c": 30.0,
        "battery_internal_res_mohm": 18.0,
        "rated_capacity_ah": 200.0,
        "actual_capacity_ah": 195.0,
        "grid_available": True,
        "load_shedding": False,
        "ev_demand_kw": 0.0,
        "transformer_loading_pct": 45.0,
    },
    "Evening Peak": {
        "pv_generation_kw": 0.3,
        "load_demand_kw": 4.8,
        "battery_soc": 80.0,
        "battery_capacity_kwh": 10.0,
        "battery_age_years": 1.5,
        "battery_temp_c": 32.0,
        "battery_internal_res_mohm": 20.0,
        "rated_capacity_ah": 200.0,
        "actual_capacity_ah": 190.0,
        "grid_available": True,
        "load_shedding": False,
        "ev_demand_kw": 2.0,
        "transformer_loading_pct": 78.0,
    },
    "Load-Shedding": {
        "pv_generation_kw": 1.2,
        "load_demand_kw": 3.5,
        "battery_soc": 30.0,
        "battery_capacity_kwh": 10.0,
        "battery_age_years": 2.0,
        "battery_temp_c": 35.0,
        "battery_internal_res_mohm": 24.0,
        "rated_capacity_ah": 200.0,
        "actual_capacity_ah": 180.0,
        "grid_available": False,
        "load_shedding": True,
        "ev_demand_kw": 0.0,
        "transformer_loading_pct": 0.0,
    },
    "Battery Health Warning": {
        "pv_generation_kw": 5.0,
        "load_demand_kw": 3.0,
        "battery_soc": 40.0,
        "battery_capacity_kwh": 10.0,
        "battery_age_years": 4.5,
        "battery_temp_c": 47.0,
        "battery_internal_res_mohm": 58.0,
        "rated_capacity_ah": 200.0,
        "actual_capacity_ah": 125.0,
        "grid_available": True,
        "load_shedding": False,
        "ev_demand_kw": 1.5,
        "transformer_loading_pct": 50.0,
    },
}
