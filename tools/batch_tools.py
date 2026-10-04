import io
import pandas as pd
from typing import Union
from agents.supervisor import SupervisorAgent
from tools.validation import validate_telemetry_dict

def process_batch_telemetry(file_or_buffer: Union[str, io.BytesIO], supervisor: SupervisorAgent) -> pd.DataFrame:
    """
    Ingests batch/time-series CSV data and executes the full SolarSathi
    multi-agent dispatch and safety guardrail engine row-by-row.
    """
    df = pd.read_csv(file_or_buffer)
    
    # Clean header whitespaces
    df.columns = df.columns.str.strip()

    solar_actions = []
    battery_actions = []
    grid_actions = []
    ev_actions = []
    health_scores = []
    health_statuses = []
    p_solar_load = []
    p_solar_batt = []
    p_batt_load = []
    p_grid_load = []
    p_solar_grid = []
    replanned_flags = []
    safety_alerts = []

    for _, row in df.iterrows():
        # Map CSV column variants safely to schema expectations
        telemetry_dict = {
            "pv_generation_kw": float(row.get("pv_generation_kw", row.get("PV", row.get("solar_kw", 0.0)))),
            "load_demand_kw": float(row.get("load_demand_kw", row.get("Load", row.get("demand_kw", 1.0)))),
            "battery_soc": float(row.get("battery_soc", row.get("SOC", 50.0))),
            "battery_capacity_kwh": float(row.get("battery_capacity_kwh", 10.0)),
            "battery_age_years": float(row.get("battery_age_years", 1.5)),
            "battery_temp_c": float(row.get("battery_temp_c", 30.0)),
            "battery_internal_res_mohm": float(row.get("battery_internal_res_mohm", 22.0)),
            "rated_capacity_ah": float(row.get("rated_capacity_ah", 200.0)),
            "actual_capacity_ah": float(row.get("actual_capacity_ah", 185.0)),
            "grid_available": bool(row.get("grid_available", True)),
            "load_shedding": bool(row.get("load_shedding", False)),
            "ev_demand_kw": float(row.get("ev_demand_kw", 0.0)),
            "transformer_loading_pct": float(row.get("transformer_loading_pct", 50.0)),
        }

        telemetry, err = validate_telemetry_dict(telemetry_dict)
        if telemetry:
            outcome = supervisor.coordinate(telemetry)
            plan = outcome["plan"]
            batt = outcome["battery"]

            solar_actions.append(plan.solar_action)
            battery_actions.append(plan.battery_action)
            grid_actions.append(plan.grid_action)
            ev_actions.append(plan.ev_action)
            health_scores.append(batt.health_score)
            health_statuses.append(batt.status)
            p_solar_load.append(plan.power_flows.get("solar_to_load", 0.0))
            p_solar_batt.append(plan.power_flows.get("solar_to_battery", 0.0))
            p_batt_load.append(plan.power_flows.get("battery_to_load", 0.0))
            p_grid_load.append(plan.power_flows.get("grid_to_load", 0.0))
            p_solar_grid.append(plan.power_flows.get("solar_to_grid", 0.0))
            replanned_flags.append(outcome["replanned"])
            safety_alerts.append("; ".join(plan.warning_alerts) if plan.warning_alerts else "Nominal")
        else:
            solar_actions.append("Invalid Row")
            battery_actions.append("Invalid Row")
            grid_actions.append("Invalid Row")
            ev_actions.append("Invalid Row")
            health_scores.append(0.0)
            health_statuses.append("Error")
            p_solar_load.append(0.0)
            p_solar_batt.append(0.0)
            p_batt_load.append(0.0)
            p_grid_load.append(0.0)
            p_solar_grid.append(0.0)
            replanned_flags.append(False)
            safety_alerts.append(f"Format Error: {err}")

    # Append deterministic agent results directly into the dataframe
    df["Agent_Solar_Action"] = solar_actions
    df["Agent_Battery_Action"] = battery_actions
    df["Agent_Grid_Action"] = grid_actions
    df["Agent_EV_Action"] = ev_actions
    df["Battery_SOH_Score"] = health_scores
    df["Battery_Health_Status"] = health_statuses
    df["Flow_Solar_to_Load_kW"] = p_solar_load
    df["Flow_Solar_to_Battery_kW"] = p_solar_batt
    df["Flow_Battery_to_Load_kW"] = p_batt_load
    df["Flow_Grid_to_Load_kW"] = p_grid_load
    df["Flow_Solar_to_Grid_kW"] = p_solar_grid
    df["Safety_Replanned"] = replanned_flags
    df["Safety_Diagnostics"] = safety_alerts

    return df
