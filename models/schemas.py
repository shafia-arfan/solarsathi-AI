from typing import List, Optional
from pydantic import BaseModel, Field

class TelemetryInput(BaseModel):
    pv_generation_kw: float = Field(ge=0.0)
    load_demand_kw: float = Field(ge=0.0)
    battery_soc: float = Field(ge=0.0, le=100.0)
    battery_capacity_kwh: float = Field(gt=0.0)
    battery_age_years: float = Field(ge=0.0)
    battery_temp_c: float
    battery_internal_res_mohm: float = Field(ge=0.0)
    rated_capacity_ah: float = Field(gt=0.0)
    actual_capacity_ah: float = Field(ge=0.0)
    grid_available: bool
    load_shedding: bool
    ev_demand_kw: float = Field(default=0.0, ge=0.0)
    transformer_loading_pct: float = Field(default=50.0, ge=0.0, le=150.0)

class SolarAnalysis(BaseModel):
    pv_generation_kw: float
    net_surplus_kw: float
    can_cover_base_load: bool
    status: str

class BatteryHealthReport(BaseModel):
    health_score: float
    status: str  # "Healthy", "Warning", "Critical"
    capacity_retention_pct: float
    observed_concerns: List[str]
    possible_causes: List[str]
    recommended_checks: List[str]
    recommended_operating_behavior: str

class GridLoadAnalysis(BaseModel):
    grid_available: bool
    is_load_shedding: bool
    effective_load_kw: float
    transformer_overloaded: bool
    curtailment_needed: bool

class EnergyPlan(BaseModel):
    solar_action: str
    battery_action: str
    grid_action: str
    ev_action: str
    power_flows: dict  # Keys: solar_to_load, solar_to_battery, battery_to_load, grid_to_load, solar_to_grid
    reason_codes: List[str]
    safety_status: str  # "Safe", "Replanned", "Emergency_Cutoff"
    replanned_iteration: bool = False
    warning_alerts: List[str]
