from models.schemas import TelemetryInput, SolarAnalysis
from tools.energy_tools import analyze_solar_balance

class SolarAgent:
    """Agent responsible for renewable PV generation assessment."""
    def __init__(self):
        self.name = "Solar Specialist Agent"

    def run(self, telemetry: TelemetryInput) -> SolarAnalysis:
        return analyze_solar_balance(telemetry)
