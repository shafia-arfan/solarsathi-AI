from typing import Tuple
from models.schemas import TelemetryInput, EnergyPlan, BatteryHealthReport
from config import CRITICAL_TEMP_C, MIN_BATTERY_SOC

class SafetyGuardrailAgent:
    """Agent enforcing physical protection, thermal limits, and triggering replanning."""
    def __init__(self):
        self.name = "Safety Guardrail Agent"

    def validate_and_guard(
        self,
        plan: EnergyPlan,
        telemetry: TelemetryInput,
        health: BatteryHealthReport
    ) -> Tuple[EnergyPlan, bool]:
        """
        Validates the proposed energy plan against physical constraints.
        Returns: (Updated EnergyPlan, replanned_flag)
        """
        replanned = False
        updated_plan = plan.model_copy(deep=True)

        # Guardrail 1: Critical Battery Overheating Check
        if telemetry.battery_temp_c >= CRITICAL_TEMP_C:
            if updated_plan.power_flows["solar_to_battery"] > 0 or updated_plan.power_flows["battery_to_load"] > 0:
                updated_plan.power_flows["solar_to_battery"] = 0.0
                updated_plan.power_flows["battery_to_load"] = 0.0
                updated_plan.battery_action = "EMERGENCY THERMAL LOCKOUT"
                updated_plan.warning_alerts.append(
                    f"GUARDRAIL TRIGGERED: Battery temperature ({telemetry.battery_temp_c}°C) breached critical limit. Battery isolated."
                )
                updated_plan.safety_status = "Replanned"
                replanned = True

        # Guardrail 2: Transformer Overload Shedding
        if telemetry.transformer_loading_pct > 85.0 and updated_plan.ev_action != "Delayed (Transformer Overload Guardrail)":
            updated_plan.ev_action = "Delayed (Transformer Overload Guardrail)"
            updated_plan.warning_alerts.append(
                f"GUARDRAIL TRIGGERED: Transformer at {telemetry.transformer_loading_pct}%. EV charging canceled to prevent blackout."
            )
            updated_plan.safety_status = "Replanned"
            replanned = True

        # Guardrail 3: Over-discharge prevention during load shedding
        if telemetry.load_shedding and telemetry.battery_soc < MIN_BATTERY_SOC:
            if updated_plan.power_flows["battery_to_load"] > 0:
                updated_plan.power_flows["battery_to_load"] = 0.0
                updated_plan.battery_action = "Cutoff - Low Battery Reserve"
                updated_plan.warning_alerts.append(
                    "GUARDRAIL TRIGGERED: Discharging halted. Critical reserve reached during outage."
                )
                updated_plan.safety_status = "Replanned"
                replanned = True

        updated_plan.replanned_iteration = replanned
        return updated_plan, replanned
