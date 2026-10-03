from config import (
    MAX_OPERATING_TEMP_C,
    CRITICAL_TEMP_C,
    NORMAL_INTERNAL_RES_MOHM,
    HIGH_INTERNAL_RES_MOHM,
    MAX_BATTERY_AGE_YEARS,
    CRITICAL_SOH_SCORE,
    WARNING_SOH_SCORE
)
from models.schemas import TelemetryInput, BatteryHealthReport

def calculate_battery_health(telemetry: TelemetryInput) -> BatteryHealthReport:
    """Calculates battery health score and flags failure risks without LLM hallucination."""
    concerns = []
    causes = []
    checks = []

    # 1. Capacity Retention Score (40% weight)
    retention_pct = min(100.0, (telemetry.actual_capacity_ah / telemetry.rated_capacity_ah) * 100.0)
    capacity_score = retention_pct

    # 2. Internal Resistance Score (30% weight)
    ir = telemetry.battery_internal_res_mohm
    if ir <= NORMAL_INTERNAL_RES_MOHM:
        ir_score = 100.0
    elif ir >= HIGH_INTERNAL_RES_MOHM:
        ir_score = max(0.0, 100.0 - ((ir - HIGH_INTERNAL_RES_MOHM) * 2.5 + 40.0))
        concerns.append(f"Elevated internal resistance ({ir:.1f} mΩ).")
        causes.append("Plate sulfation, grid corrosion, or dry electrolyte.")
        checks.append("Perform impedance testing and check cell terminal torque.")
    else:
        ir_score = 100.0 - ((ir - NORMAL_INTERNAL_RES_MOHM) / (HIGH_INTERNAL_RES_MOHM - NORMAL_INTERNAL_RES_MOHM)) * 30.0

    # 3. Thermal Score (15% weight)
    temp = telemetry.battery_temp_c
    if temp > CRITICAL_TEMP_C:
        temp_score = 20.0
        concerns.append(f"CRITICAL Temperature ({temp:.1f}°C) exceeding safety boundary.")
        causes.append("Thermal runaway hazard or aggressive over-cycling.")
        checks.append("Immediate active cooling and emergency discharge throttling.")
    elif temp > MAX_OPERATING_TEMP_C:
        temp_score = 60.0
        concerns.append(f"High operating temperature ({temp:.1f}°C).")
        causes.append("Insufficient enclosure ventilation or elevated ambient heat.")
        checks.append("Verify inverter fan functionality and room ventilation.")
    else:
        temp_score = 100.0

    # 4. Age Score (15% weight)
    age = telemetry.battery_age_years
    if age > MAX_BATTERY_AGE_YEARS:
        age_score = max(20.0, 100.0 - ((age - MAX_BATTERY_AGE_YEARS) * 20.0))
        concerns.append(f"Battery operational age ({age:.1f} years) exceeds nominal lifespan.")
        causes.append("Active material shedding and calendar aging.")
        checks.append("Schedule full capacity discharge test.")
    else:
        age_score = 100.0 - (age / MAX_BATTERY_AGE_YEARS) * 20.0

    # Weighted Overall Health Score (SOH)
    overall_health = (capacity_score * 0.40) + (ir_score * 0.30) + (temp_score * 0.15) + (age_score * 0.15)
    overall_health = round(max(0.0, min(100.0, overall_health)), 1)

    if overall_health >= WARNING_SOH_SCORE:
        status = "Healthy"
        op_behavior = "Standard cycling permitted. Continuous full discharge supported."
    elif overall_health >= CRITICAL_SOH_SCORE:
        status = "Warning"
        op_behavior = "Throttle deep discharge cycles. Cap discharge rate and protect battery."
    else:
        status = "Critical"
        op_behavior = "Avoid autonomous discharge. Isolate battery to emergency loads only."

    if not concerns:
        concerns.append("All physical parameters within nominal operating bands.")
        causes.append("Normal healthy operation.")
        checks.append("Routine quarterly terminal inspection.")

    return BatteryHealthReport(
        health_score=overall_health,
        status=status,
        capacity_retention_pct=round(retention_pct, 1),
        observed_concerns=concerns,
        possible_causes=causes,
        recommended_checks=checks,
        recommended_operating_behavior=op_behavior
    )
