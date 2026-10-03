from models.schemas import (
    TelemetryInput,
    SolarAnalysis,
    BatteryHealthReport,
    GridLoadAnalysis,
    EnergyPlan
)
from agents.solar_agent import SolarAgent
from agents.battery_agent import BatteryHealthAgent
from agents.grid_agent import GridAgent
from agents.safety_agent import SafetyGuardrailAgent
from tools.energy_tools import create_deterministic_energy_plan

class SupervisorAgent:
    """Supervisory agent that coordinates specialized agents and manages replanning."""
    def __init__(self):
        self.solar_agent = SolarAgent()
        self.battery_agent = BatteryHealthAgent()
        self.grid_agent = GridAgent()
        self.safety_agent = SafetyGuardrailAgent()

    def coordinate(self, telemetry: TelemetryInput):
        """
        Coordinates multi-agent analysis:
        1. Solar Agent analyzes generation.
        2. Battery Agent evaluates SOH.
        3. Grid Agent evaluates grid status.
        4. Supervisor compiles draft Energy Plan.
        5. Safety Agent verifies constraints and replans if needed.
        """
        # Step 1: Specialist Agents evaluate concurrently
        solar_analysis: SolarAnalysis = self.solar_agent.run(telemetry)
        battery_health: BatteryHealthReport = self.battery_agent.run(telemetry)
        grid_analysis: GridLoadAnalysis = self.grid_agent.run(telemetry)

        # Step 2: Draft Initial Energy Plan
        initial_plan: EnergyPlan = create_deterministic_energy_plan(
            telemetry, solar_analysis, grid_analysis, battery_health
        )

        # Step 3: Safety Guardrail Agent checks boundaries
        final_plan, was_replanned = self.safety_agent.validate_and_guard(
            initial_plan, telemetry, battery_health
        )

        return {
            "solar": solar_analysis,
            "battery": battery_health,
            "grid": grid_analysis,
            "plan": final_plan,
            "replanned": was_replanned
        }
