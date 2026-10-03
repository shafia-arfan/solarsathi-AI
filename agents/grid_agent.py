from models.schemas import TelemetryInput, GridLoadAnalysis
from tools.energy_tools import analyze_grid_and_load

class GridAgent:
    """Agent monitoring utility connection, load shedding, and feeder limits."""
    def __init__(self):
        self.name = "Grid & Distribution Agent"

    def run(self, telemetry: TelemetryInput) -> GridLoadAnalysis:
        return analyze_grid_and_load(telemetry)
