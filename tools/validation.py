from typing import Tuple, Optional
from models.schemas import TelemetryInput

def validate_telemetry_dict(data: dict) -> Tuple[Optional[TelemetryInput], Optional[str]]:
    """Strictly validates input dictionary and returns clean TelemetryInput or error message."""
    try:
        # Enforce logical consistency
        if data.get("actual_capacity_ah", 0) > data.get("rated_capacity_ah", 1) * 1.25:
            return None, "Actual Ah cannot exceed rated Ah by more than 25%."
        
        telemetry = TelemetryInput(**data)
        return telemetry, None
    except Exception as e:
        return None, f"Input validation error: {str(e)}"
