from models.schemas import TelemetryInput, BatteryHealthReport
from tools.battery_tools import calculate_battery_health

class BatteryHealthAgent:
    """Agent monitoring SOH, cell temperature, and internal impedance."""
    def __init__(self):
        self.name = "Battery Health Doctor"

    def run(self, telemetry: TelemetryInput) -> BatteryHealthReport:
        return calculate_battery_health(telemetry)
