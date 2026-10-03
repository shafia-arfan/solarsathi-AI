from config import (
    MIN_BATTERY_SOC,
    RESERVE_BATTERY_SOC,
    MAX_BATTERY_SOC,
    TRANSFORMER_HIGH_THRESHOLD
)
from models.schemas import (
    TelemetryInput,
    SolarAnalysis,
    GridLoadAnalysis,
    BatteryHealthReport,
    EnergyPlan
)

def analyze_solar_balance(telemetry: TelemetryInput) -> SolarAnalysis:
    """Calculates instantaneous generation vs baseline load."""
    surplus = telemetry.pv_generation_kw - telemetry.load_demand_kw
    can_cover = surplus >= 0
    status = "Surplus Generation" if surplus > 0.1 else ("Deficit Solar" if surplus < -0.1 else "Balanced")
    return SolarAnalysis(
        pv_generation_kw=telemetry.pv_generation_kw,
        net_surplus_kw=round(surplus, 2),
        can_cover_base_load=can_cover,
        status=status
    )

def analyze_grid_and_load(telemetry: TelemetryInput) -> GridLoadAnalysis:
    """Evaluates grid availability, load-shedding, and transformer head-room."""
    effective_load = telemetry.load_demand_kw + telemetry.ev_demand_kw
    is_overloaded = telemetry.transformer_loading_pct > TRANSFORMER_HIGH_THRESHOLD
    
    return GridLoadAnalysis(
        grid_available=telemetry.grid_available,
        is_load_shedding=telemetry.load_shedding,
        effective_load_kw=round(effective_load, 2),
        transformer_overloaded=is_overloaded,
        curtailment_needed=is_overloaded or telemetry.load_shedding
    )

def create_deterministic_energy_plan(
    telemetry: TelemetryInput,
    solar: SolarAnalysis,
    grid: GridLoadAnalysis,
    health: BatteryHealthReport
) -> EnergyPlan:
    """Deterministic power dispatch decision engine."""
    pv = telemetry.pv_generation_kw
    load = telemetry.load_demand_kw
    ev = telemetry.ev_demand_kw
    soc = telemetry.battery_soc
    
    reasons = []
    warnings = []
    
    # Power Flow Allocations
    solar_to_load = 0.0
    solar_to_battery = 0.0
    solar_to_grid = 0.0
    battery_to_load = 0.0
    grid_to_load = 0.0
    
    # Target SOC cutoff depends on load shedding state
    soc_cutoff = RESERVE_BATTERY_SOC if telemetry.load_shedding else MIN_BATTERY_SOC

    # Step 1: Solar Dispatch First
    if pv >= load:
        solar_to_load = load
        surplus = pv - load
        reasons.append("PV covers 100% of household load.")
        
        # Check battery acceptance
        if soc < MAX_BATTERY_SOC and health.status != "Critical":
            # Max charge rate is 0.5C or available surplus
            charge_power = min(surplus, telemetry.battery_capacity_kwh * 0.5)
            solar_to_battery = round(charge_power, 2)
            surplus -= solar_to_battery
            reasons.append(f"Surplus PV ({solar_to_battery} kW) diverted to charge battery.")
        
        # Handle Remaining Surplus
        if surplus > 0.05:
            if telemetry.grid_available and not telemetry.load_shedding:
                solar_to_grid = round(surplus, 2)
                reasons.append(f"Remaining surplus ({solar_to_grid} kW) exported to Grid.")
            else:
                reasons.append("Surplus curtailed: Grid export unavailable during load-shedding.")
                
        solar_action = "Supply Load & Charge Battery" if solar_to_battery > 0 else "Supply Load & Export"
        battery_action = "Charging" if solar_to_battery > 0 else "Idle"
        grid_action = "Exporting Surplus" if solar_to_grid > 0 else "Idle"

    else:
        # Solar Deficit
        solar_to_load = pv
        unmet_load = load - pv
        solar_action = "Partial Load Supply"
        reasons.append(f"PV covers {pv:.1f} kW of {load:.1f} kW demand.")

        # Determine battery contribution
        can_discharge_battery = (soc > soc_cutoff) and (health.status != "Critical")
        
        if can_discharge_battery:
            discharge_power = min(unmet_load, telemetry.battery_capacity_kwh * 0.6)
            battery_to_load = round(discharge_power, 2)
            unmet_load -= battery_to_load
            battery_action = "Discharging to Load"
            reasons.append(f"Battery supplies {battery_to_load} kW to bridge solar deficit.")
        else:
            battery_action = "Idle / Protected"
            if soc <= soc_cutoff:
                warnings.append(f"Battery SOC ({soc:.0f}%) reached reserve threshold ({soc_cutoff:.0f}%).")
            if health.status == "Critical":
                warnings.append("Battery discharge blocked due to Critical SOH status.")

        # Determine Grid contribution
        if unmet_load > 0.05:
            if telemetry.grid_available and not telemetry.load_shedding:
                grid_to_load = round(unmet_load, 2)
                grid_action = f"Importing {grid_to_load} kW"
                reasons.append(f"Grid supplies residual shortfall ({grid_to_load} kW).")
            else:
                grid_action = "Unavailable (Load-Shedding)"
                warnings.append(f"DEFICIT ALERT: {unmet_load:.1f} kW unserved load! Manual load-shedding required.")
        else:
            grid_action = "Standby"

    # Step 2: EV Decision Logic
    ev_action = "Idle"
    if ev > 0:
        if grid.transformer_overloaded:
            ev_action = "Delayed (Transformer Overload Guardrail)"
            warnings.append(f"EV charging blocked: Transformer at {telemetry.transformer_loading_pct}%.")
        elif telemetry.load_shedding:
            ev_action = "Suspended (Load Shedding Active)"
            warnings.append("EV charging suspended during outage to preserve battery reserves.")
        elif pv > (load + ev):
            ev_action = "Charging from 100% Solar Surplus"
        elif telemetry.grid_available:
            ev_action = "Charging from Grid"
        else:
            ev_action = "Delayed"

    flows = {
        "solar_to_load": round(solar_to_load, 2),
        "solar_to_battery": round(solar_to_battery, 2),
        "battery_to_load": round(battery_to_load, 2),
        "grid_to_load": round(grid_to_load, 2),
        "solar_to_grid": round(solar_to_grid, 2)
    }

    return EnergyPlan(
        solar_action=solar_action,
        battery_action=battery_action,
        grid_action=grid_action,
        ev_action=ev_action,
        power_flows=flows,
        reason_codes=reasons,
        safety_status="Safe",
        replanned_iteration=False,
        warning_alerts=warnings
    )
