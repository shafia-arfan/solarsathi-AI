import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import DEMO_SCENARIOS, DEFAULT_GEMINI_MODEL
from tools.validation import validate_telemetry_dict
from agents.supervisor import SupervisorAgent
from utils.gemini_client import get_gemini_api_key, generate_natural_explanation
from utils.report_generator import generate_markdown_report

# Page Configuration
st.set_page_config(
    page_title="SolarSathi AI — Microgrid Manager",
    page_icon="🌞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Hackathon Aesthetic
st.markdown("""
<style>
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border-left: 5px solid #ff9800;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
    }
    .status-badge {
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE & INITIALIZATION -----------------
if "supervisor" not in st.session_state:
    st.session_state.supervisor = SupervisorAgent()

if "gemini_explanation" not in st.session_state:
    st.session_state.gemini_explanation = None

if "last_scenario" not in st.session_state:
    st.session_state.last_scenario = "Sunny Day"

# ----------------- SIDEBAR: CONFIG & INPUTS -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/solar-panel.png", width=64)
    st.title("SolarSathi Controls")
    
    # Engine Connectivity Status
    api_key_set = bool(get_gemini_api_key())
    if api_key_set:
        st.success("🟢 AI Engine: Gemini Connected")
    else:
        st.warning("🟡 AI Engine: Python Fallback Mode")
        st.caption("Add `GEMINI_API_KEY` to secrets for dynamic LLM reasoning.")

    st.subheader("⚡ Demo Scenarios")
    selected_scenario = st.selectbox(
        "Load Preconfigured State:",
        options=list(DEMO_SCENARIOS.keys()),
        index=0
    )
    
    # Reset explanation if scenario changes
    if selected_scenario != st.session_state.last_scenario:
        st.session_state.last_scenario = selected_scenario
        st.session_state.gemini_explanation = None

    default_vals = DEMO_SCENARIOS[selected_scenario]

    st.markdown("---")
    st.subheader("📊 Live Telemetry Inputs")
    
    pv_input = st.number_input("Solar PV Generation (kW)", min_value=0.0, max_value=50.0, value=float(default_vals["pv_generation_kw"]), step=0.2)
    load_input = st.number_input("Load Demand (kW)", min_value=0.1, max_value=50.0, value=float(default_vals["load_demand_kw"]), step=0.2)
    soc_input = st.slider("Battery SOC (%)", min_value=0.0, max_value=100.0, value=float(default_vals["battery_soc"]), step=1.0)
    batt_cap_input = st.number_input("Battery Capacity (kWh)", min_value=1.0, max_value=100.0, value=float(default_vals["battery_capacity_kwh"]), step=1.0)
    
    with st.expander("🔋 Battery Diagnostic Telemetry", expanded=False):
        age_input = st.number_input("Battery Age (Years)", min_value=0.0, max_value=15.0, value=float(default_vals["battery_age_years"]), step=0.5)
        temp_input = st.number_input("Temperature (°C)", min_value=-10.0, max_value=80.0, value=float(default_vals["battery_temp_c"]), step=1.0)
        ir_input = st.number_input("Internal Resistance (mΩ)", min_value=1.0, max_value=200.0, value=float(default_vals["battery_internal_res_mohm"]), step=1.0)
        rated_ah = st.number_input("Rated Capacity (Ah)", min_value=10.0, max_value=1000.0, value=float(default_vals["rated_capacity_ah"]), step=10.0)
        actual_ah = st.number_input("Actual Capacity (Ah)", min_value=5.0, max_value=1000.0, value=float(default_vals["actual_capacity_ah"]), step=10.0)

    with st.expander("🌐 Grid & EV Telemetry", expanded=False):
        grid_avail = st.toggle("Grid Available", value=bool(default_vals["grid_available"]))
        load_shed = st.toggle("Load-Shedding Active", value=bool(default_vals["load_shedding"]))
        ev_demand = st.number_input("EV Charging Demand (kW)", min_value=0.0, max_value=22.0, value=float(default_vals["ev_demand_kw"]), step=0.5)
        tx_load = st.slider("Transformer Loading (%)", min_value=0.0, max_value=150.0, value=float(default_vals["transformer_loading_pct"]), step=5.0)

# Build telemetry dict
telemetry_data = {
    "pv_generation_kw": pv_input,
    "load_demand_kw": load_input,
    "battery_soc": soc_input,
    "battery_capacity_kwh": batt_cap_input,
    "battery_age_years": age_input,
    "battery_temp_c": temp_input,
    "battery_internal_res_mohm": ir_input,
    "rated_capacity_ah": rated_ah,
    "actual_capacity_ah": actual_ah,
    "grid_available": grid_avail,
    "load_shedding": load_shed,
    "ev_demand_kw": ev_demand,
    "transformer_loading_pct": tx_load,
}

# ----------------- EXECUTE DETERMINISTIC MULTI-AGENT WORKFLOW -----------------
validated_telemetry, error_msg = validate_telemetry_dict(telemetry_data)

if error_msg:
    st.error(f"Input Validation Error: {error_msg}")
    st.stop()

# Run Supervisor Agent (Instant Python Multi-Agent Coordination)
results = st.session_state.supervisor.coordinate(validated_telemetry)
solar_res = results["solar"]
battery_res = results["battery"]
grid_res = results["grid"]
plan_res = results["plan"]
was_replanned = results["replanned"]

# ----------------- MAIN UI DASHBOARD -----------------
st.title("🌞 SolarSathi AI")
st.markdown("##### *Agentic Solar + Battery Manager & Health Doctor*")

# Top KPI Metric Cards
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("☀️ Solar PV", f"{validated_telemetry.pv_generation_kw:.1f} kW", delta=solar_res.status)
kpi2.metric("🏠 Demand", f"{validated_telemetry.load_demand_kw:.1f} kW")
kpi3.metric("🔋 Battery SOC", f"{validated_telemetry.battery_soc:.0f}%", delta=f"{plan_res.battery_action}")
kpi4.metric("⚡ Grid State", "Online" if validated_telemetry.grid_available and not validated_telemetry.load_shedding else "Outage")
soh_color = "normal" if battery_res.status == "Healthy" else "inverse"
kpi5.metric("❤️ Battery SOH", f"{battery_res.health_score:.0f}/100", delta=battery_res.status, delta_color=soh_color)

# Safety Guardrail Notification Banner
if was_replanned:
    st.warning("⚠️ **Safety Guardrail Interception:** Supervisor re-routed power flows to prevent overload or thermal damage.")

st.markdown("---")

# Section 1: Visual Energy Flows & Balances
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("⚡ Real-time Power Dispatch")
    
    # Power Flow Sankey/Bar Representation
    flows = plan_res.power_flows
    flow_df = pd.DataFrame({
        "Flow Path": ["Solar ➔ Load", "Solar ➔ Battery", "Battery ➔ Load", "Grid ➔ Load", "Solar ➔ Grid"],
        "Power (kW)": [flows["solar_to_load"], flows["solar_to_battery"], flows["battery_to_load"], flows["grid_to_load"], flows["solar_to_grid"]]
    })
    
    fig = go.Figure(data=[
        go.Bar(
            x=flow_df["Flow Path"],
            y=flow_df["Power (kW)"],
            marker_color=["#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#00BCD4"],
            text=flow_df["Power (kW)"],
            textposition='auto',
        )
    ])
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis_title="Dispatched Power (kW)",
        xaxis_title=""
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("🔋 Battery Health Doctor")
    
    # Battery Gauge Chart
    gauge_fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = battery_res.health_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': f"Status: {battery_res.status}"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "#2E7D32" if battery_res.status == "Healthy" else ("#F57C00" if battery_res.status == "Warning" else "#D32F2F")},
            'steps': [
                {'range': [0, 50], 'color': "#FFCDD2"},
                {'range': [50, 75], 'color': "#FFE0B2"},
                {'range': [75, 100], 'color': "#C8E6C9"}
            ],
        }
    ))
    gauge_fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(gauge_fig, use_container_width=True)
    st.caption(f"**Operating Rule:** {battery_res.recommended_operating_behavior}")

# Section 2: Agent Dispatched Actions
st.subheader("📋 Coordinated Agent Dispatch Decisions")
c1, c2, c3, c4 = st.columns(4)
c1.info(f"**Solar Agent**\n\n{plan_res.solar_action}")
c2.info(f"**Battery Agent**\n\n{plan_res.battery_action}")
c3.info(f"**Grid Agent**\n\n{plan_res.grid_action}")
c4.info(f"**EV Fleet Agent**\n\n{plan_res.ev_action}")

# Section 3: AI Reasoning & Explanation (Explicit User Button for Free-Tier Quota Protection)
st.markdown("---")
st.subheader("🤖 SolarSathi Reasoning & Consultation")

call_col, help_col = st.columns([2, 3])
with call_col:
    st.write("Request full engineering justification from Gemini:")
    ask_ai_btn = st.button("🤖 Ask SolarSathi AI", use_container_width=True, type="primary")

with help_col:
    user_query_input = st.text_input("Custom question (optional):", placeholder="e.g., Why did you delay EV charging?")

if ask_ai_btn or st.session_state.gemini_explanation:
    if ask_ai_btn:
        with st.spinner("Multi-Agent Supervisor querying Gemini Reasoning Engine..."):
            explanation = generate_natural_explanation(
                telemetry_dict=telemetry_data,
                plan_dict=plan_res.model_dump(),
                battery_dict=battery_res.model_dump(),
                user_query=user_query_input if user_query_input else None
            )
            st.session_state.gemini_explanation = explanation

    st.markdown("#### 💡 AI Engineering Explanation")
    st.write(st.session_state.gemini_explanation)

# Section 4: Diagnostics, Warnings & Report Generation
st.markdown("---")
tab1, tab2 = st.tabs(["🚨 System Alerts & Diagnostics", "📄 Audit Report"])

with tab1:
    if plan_res.warning_alerts:
        for alert in plan_res.warning_alerts:
            st.error(f"⚠️ {alert}")
    else:
        st.success("✅ All network buses, transformers, and battery cells operating safely within nominal boundaries.")
        
    st.write("**Root-Cause Findings:**")
    for cause in battery_res.possible_causes:
        st.write(f"- {cause}")

with tab2:
    st.write("Generate and download a comprehensive engineering dossier for utility or technician records.")
    report_md = generate_markdown_report(telemetry_data, plan_res.model_dump(), battery_res.model_dump())
    
    st.download_button(
        label="📥 Download Energy Management Report (.md)",
        data=report_md,
        file_name=f"SolarSathi_Audit_{selected_scenario.replace(' ', '_')}.md",
        mime="text/markdown",
        use_container_width=True
    )
    with st.expander("Preview Audit Report", expanded=False):
        st.markdown(report_md)
