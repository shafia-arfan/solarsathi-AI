import streamlit as st
from config import DEFAULT_GEMINI_MODEL, FALLBACK_GEMINI_MODEL

def get_gemini_api_key() -> str:
    """Safely retrieves API key from streamlit secrets without logging it."""
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"].strip()
    return ""

def generate_natural_explanation(
    telemetry_dict: dict,
    plan_dict: dict,
    battery_dict: dict,
    user_query: str = None
) -> str:
    """
    Calls Gemini API using official google-genai library if key exists.
    Falls back gracefully to Python deterministic text if quota exceeded or offline.
    """
    api_key = get_gemini_api_key()
    model_name = st.secrets.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    # 1. Fallback Template Engine (Works offline or if API hits quota)
    fallback_text = (
        f"**Autonomous Dispatch Summary (SolarSathi Rule-Engine):**\n\n"
        f"• **Solar Action:** {plan_dict.get('solar_action')}\n"
        f"• **Battery Dispatch:** {plan_dict.get('battery_action')} (SOH: {battery_dict.get('health_score')}% - {battery_dict.get('status')})\n"
        f"• **Grid Management:** {plan_dict.get('grid_action')}\n"
        f"• **EV Fleet Status:** {plan_dict.get('ev_action')}\n\n"
        f"**Engineering Rationale:**\n"
        + "\n".join([f"- {r}" for r in plan_dict.get('reason_codes', [])])
    )

    if not api_key:
        return fallback_text + "\n\n*(Note: Running in deterministic Fallback Mode. Configure GEMINI_API_KEY in secrets for dynamic reasoning.)*"

    # 2. Attempt Google GenAI API Call
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        # Read short local knowledge snippet
        knowledge_context = ""
        try:
            with open("knowledge/microgrid_guidelines.txt", "r") as f:
                knowledge_context = f.read()[:800]
        except Exception:
            knowledge_context = "Observe standard microgrid reserve constraints."

        prompt = f"""You are SolarSathi AI, an expert Power Systems & Battery Diagnostic Engineer for distributed microgrids in Pakistan.
Explain the following system decisions concisely to the user in professional, reassuring engineering language.

TECHNICAL KNOWLEDGE REFERENCE:
{knowledge_context}

SYSTEM TELEMETRY:
- Solar Generation: {telemetry_dict.get('pv_generation_kw')} kW
- Total Load: {telemetry_dict.get('load_demand_kw')} kW
- Battery SOC: {telemetry_dict.get('battery_soc')}% | Temperature: {telemetry_dict.get('battery_temp_c')} C | SOH Score: {battery_dict.get('health_score')}% ({battery_dict.get('status')})
- Grid Available: {telemetry_dict.get('grid_available')} | Outage/Load-Shedding: {telemetry_dict.get('load_shedding')}
- Transformer Loading: {telemetry_dict.get('transformer_loading_pct')}%

SUPERVISOR DECISION:
- Solar: {plan_dict.get('solar_action')}
- Battery: {plan_dict.get('battery_action')}
- Grid: {plan_dict.get('grid_action')}
- EV: {plan_dict.get('ev_action')}
- Safety Warnings: {plan_dict.get('warning_alerts')}
- Technical Reasons: {plan_dict.get('reason_codes')}

USER QUESTION (If any):
{user_query if user_query else "Provide an operational breakdown and explain why this strategy was chosen."}

INSTRUCTIONS:
1. Provide a direct, structured 3-bullet explanation of the operational decision.
2. Highlight battery health preservation and grid safety.
3. Keep it under 180 words. Never invent numbers."""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text

    except Exception as e:
        # Fallback to secondary model if primary fails
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=FALLBACK_GEMINI_MODEL,
                contents=prompt,
            )
            return response.text
        except Exception:
            # Complete graceful failure recovery
            return (
                fallback_text
                + f"\n\n*(Notice: Cloud LLM unavailable due to free-tier rate limits [{str(e)[:50]}...]. Fallback engine seamlessly engaged.)*"
            )
