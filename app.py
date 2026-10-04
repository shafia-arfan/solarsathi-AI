
import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from config import DEMO_SCENARIOS
from tools.validation import validate_telemetry_dict
from tools.batch_tools import process_batch_telemetry
from agents.supervisor import SupervisorAgent
from utils.gemini_client import get_gemini_api_key, generate_natural_explanation
from utils.report_generator import generate_markdown_report

# Import new simulation components
from simulation.energy import summarize, detect_warnings
from simulation.checks import check_report
from simulation.grid_pandapower import run_feeder

# Page Setup
st.set_page_config(
    page_title="SolarSathi AI — Microgrid & Battery Doctor",
    page_icon="🌞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Strictly Amber/Green/Graphite - Anti-Blue Design)
st.markdown("""
<style>
    .kpi-card {
        background-color: #FAFAFA;
        border-radius: 8px;
        padding: 14px;
        border-left: 4px solid #EA580C;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if "supervisor" not in st.session_state:
    st.session_state.supervisor = SupervisorAgent()
if "gemini_explanation" not in st.session_state:
    st.session_state.gemini_explanation = None
if "last_scenario" not in st.session_state:
    st.session_state.last_scenario = "Sunny Day"

# ----------------- SIDEBAR CONTROLS -----------------
with st.sidebar:
    st.image("https://img.icons8.com/color/96/solar-panel.png", width=64)
    st.title("SolarSathi Controls")
    
    api_key_set = bool(get_gemini_api_key())
    if api_key_set:
        st.success("🟢 AI Engine: Gemini Connected")
    else:
        st.warning("🟡 AI Engine: Python Fallback Mode")
        st.caption("Add `GEMINI_API_KEY` to secrets for dynamic LLM reasoning.")

    st.subheader("⚡ Quick Scenarios")
    selected_scenario = st.selectbox(
        "Load Preconfigured State:",
        options=list(DEMO_SCENARIOS.keys()),
        index=0
    )
    
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

    with st.expander("🔋 Battery Health Doctor Parameters", expanded=False):
        age_input = st.number_input("Battery Age (Years)", min_value=0.0, max_value=15.0, value=float(default_vals["battery_age_years"]), step=0.5)
        temp_input = st.number_input("Temperature (°C)", min_value=-10.0, max_value=80.0, value=float(default_vals["battery_temp_c"]), step=1.0)
        ir_input = st.number_input("Internal Resistance (mΩ)", min_value=1.0, max_value=200.0, value=float(default_vals["battery_internal_res_mohm"]), step=1.0)
        rated_ah = st.number_input("Rated Capacity (Ah)", min_value=10.0, max_value=1000.0, value=float(default_vals["rated_capacity_ah"]), step=10.0)
        actual_ah = st.number_input("Actual Capacity (Ah)", min_value=5.0, max_value=1000.0, value=float(default_vals["actual_capacity_ah"]), step=10.0)

    with st.expander("🌐 Grid & Feeder Controls", expanded=False):
        grid_avail = st.toggle("Grid Available", value=bool(default_vals["grid_available"]))
        load_shed = st.toggle("Load-Shedding Active", value=bool(default_vals["load_shedding"]))
        ev_demand = st.number_input("EV Demand (kW)", min_value=0.0, max_value=22.0, value=float(default_vals["ev_demand_kw"]), step=0.5)
        tx_load = st.slider("Transformer Loading (%)", min_value=0.0, max_value=150.0, value=float(default_vals["transformer_loading_pct"]), step=5.0)

# Build & Validate input
telemetry_data = {
    "pv_generation_kw": pv_input, "load_demand_kw": load_input,
    "battery_soc": soc_input, "battery_capacity_kwh": batt_cap_input,
    "battery_age_years": age_input, "battery_temp_c": temp_input,
    "battery_internal_res_mohm": ir_input, "rated_capacity_ah": rated_ah,
    "actual_capacity_ah": actual_ah, "grid_available": grid_avail,
    "load_shedding": load_shed, "ev_demand_kw": ev_demand,
    "transformer_loading_pct": tx_load,
}

validated_telemetry, error_msg = validate_telemetry_dict(telemetry_data)
if error_msg:
    st.error(f"Input Validation Error: {error_msg}")
    st.stop()

# Coordinated Multi-Agent Execution
results = st.session_state.supervisor.coordinate(validated_telemetry)
solar_res = results["solar"]
battery_res = results["battery"]
grid_res = results["grid"]
plan_res = results["plan"]
was_replanned = results["replanned"]

# ----------------- MAIN APP TABS -----------------
st.title("🌞 SolarSathi AI")
st.markdown("##### *Agentic Solar + Battery Manager & Health Doctor*")

tab_live, tab_sim, tab_benchmark = st.tabs([
    "⚡ Real-Time Dispatch",
    "📈 24h Feeder & Time-Series",
    "🔬 Benchmark Scenarios & Tests"
])

# ----------------- TAB 1: REAL-TIME DISPATCH -----------------
with tab_live:
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("☀️ Solar PV", f"{validated_telemetry.pv_generation_kw:.1f} kW", delta=solar_res.status)
    k2.metric("🏠 Demand", f"{validated_telemetry.load_demand_kw:.1f} kW")
    k3.metric("🔋 Battery SOC", f"{validated_telemetry.battery_soc:.0f}%", delta=f"{plan_res.battery_action}")
    k4.metric("⚡ Grid State", "Online" if validated_telemetry.grid_available and not validated_telemetry.load_shedding else "Outage")
    soh_color = "normal" if battery_res.status == "Healthy" else "inverse"
    k5.metric("❤️ Battery SOH", f"{battery_res.health_score:.0f}/100", delta=battery_res.status, delta_color=soh_color)

    if was_replanned:
        st.warning("⚠️ **Safety Guardrail Active:** Intercepted boundary violation. Dispatched plan was autonomously replanned.")

    st.markdown("---")
    c_left, c_right = st.columns([3, 2])
    with c_left:
        st.subheader("⚡ Real-time Power Dispatch")
        flows = plan_res.power_flows
        flow_df = pd.DataFrame({
            "Path": ["Solar➔Load", "Solar➔Battery", "Battery➔Load", "Grid➔Load", "Solar➔Grid"],
            "Power (kW)": [flows["solar_to_load"], flows["solar_to_battery"], flows["battery_to_load"], flows["grid_to_load"], flows["solar_to_grid"]]
        })
        fig = go.Figure(data=[
            go.Bar(
                x=flow_df["Path"], y=flow_df["Power (kW)"],
                marker_color=["#10B981", "#F59E0B", "#EA580C", "#78716C", "#059669"],
                text=flow_df["Power (kW)"], textposition='auto',
            )
        ])
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=20), yaxis_title="Power (kW)")
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("🔋 Battery Health Status")
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=battery_res.health_score,
            title={'text': f"SOH: {battery_res.status}"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#10B981" if battery_res.status == "Healthy" else ("#F59E0B" if battery_res.status == "Warning" else "#DC2626")},
                'steps': [
                    {'range': [0, 50], 'color': "#FEE2E2"},
                    {'range': [50, 75], 'color': "#FEF3C7"},
                    {'range': [75, 100], 'color': "#D1FAE5"}
                ],
            }
        ))
        gauge_fig.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(gauge_fig, use_container_width=True)

    st.subheader("📋 Coordinated Agent Actions")
    a1, a2, a3, a4 = st.columns(4)
    a1.info(f"**Solar Agent**\n\n{plan_res.solar_action}")
    a2.info(f"**Battery Agent**\n\n{plan_res.battery_action}")
    a3.info(f"**Grid Agent**\n\n{plan_res.grid_action}")
    a4.info(f"**EV Fleet Agent**\n\n{plan_res.ev_action}")

    st.markdown("---")
    st.subheader("🤖 SolarSathi Reasoning & Grounding Verification")
    btn_col, q_col = st.columns([1, 2])
    with btn_col:
        ask_ai = st.button("🤖 Ask SolarSathi AI", use_container_width=True, type="primary")
    with q_col:
        custom_q = st.text_input("Consultation Query:", placeholder="e.g. Why was discharge throttled?")

    if ask_ai or st.session_state.gemini_explanation:
        if ask_ai:
            with st.spinner("Querying LLM Reasoning Engine..."):
                st.session_state.gemini_explanation = generate_natural_explanation(
                    telemetry_dict=telemetry_data,
                    plan_dict=plan_res.model_dump(),
                    battery_dict=battery_res.model_dump(),
                    user_query=custom_q if custom_q else None
                )
        st.markdown(st.session_state.gemini_explanation)
        
        # Anti-Hallucination Grounding Verification Check
        facts_dict = {
            "pv_kw": validated_telemetry.pv_generation_kw,
            "load_kw": validated_telemetry.load_demand_kw,
            "soc": validated_telemetry.battery_soc,
            "soh": battery_res.health_score,
            "temp": validated_telemetry.battery_temp_c,
            "tx_load": validated_telemetry.transformer_loading_pct
        }
        grounding_issues = check_report(st.session_state.gemini_explanation, facts_dict)
        if not grounding_issues:
            st.success("🛡️ **Anti-Hallucination Guardrail:** 100% of numerical facts confirmed grounded in simulation data.")
        else:
            st.caption(f"🔎 Grounding check notes: {'; '.join(grounding_issues[:2])}")

    st.markdown("---")
    report_md = generate_markdown_report(telemetry_data, plan_res.model_dump(), battery_res.model_dump())
    st.download_button(
        label="📥 Download Audit Report (.md)",
        data=report_md,
        file_name=f"SolarSathi_Audit_{selected_scenario}.md",
        mime="text/markdown"
    )

# ----------------- TAB 2: TIME-SERIES & PANDAPOWER FEEDER -----------------
with tab_sim:
    st.subheader("📈 24h Microgrid Physics & Distribution Feeder Simulation")
    
    csv_choice = st.selectbox(
        "Choose Telemetry Dataset:",
        ["data/scenarios/battery_warning.csv", "data/scenarios/load_shedding.csv", "data/scenarios/normal_day.csv"]
    )
    
    if os.path.exists(csv_choice):
        sim_df = pd.read_csv(csv_choice)
        
        # 1. Run Dispatch Simulation
        batch_df = process_batch_telemetry(csv_choice, st.session_state.supervisor)
        
        # 2. Run PandaPower Grid Feeder Simulation
        feeder_df = run_feeder(sim_df)
        
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Outage Hours", int((sim_df.grid_on == 0).sum()))
        s2.metric("Unserved Energy", f"{sim_df.unserved_kw.sum():.2f} kWh")
        s3.metric("Peak Battery Temp", f"{sim_df.battery_temp_c.max():.1f} °C")
        s4.metric("Worst Feeder Voltage", f"{feeder_df['min_voltage_pu'].dropna().min():.3f} p.u.")

        # Power balance chart
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=sim_df.hour, y=sim_df.load_kw, name="Load (kW)", line=dict(color="#DC2626", width=2)))
        fig_ts.add_trace(go.Scatter(x=sim_df.hour, y=sim_df.solar_kw, name="Solar (kW)", line=dict(color="#10B981", width=2)))
        fig_ts.add_trace(go.Scatter(x=sim_df.hour, y=sim_df.discharge_kw, name="Battery Discharge (kW)", line=dict(color="#EA580C", dash="dot")))
        fig_ts.add_trace(go.Scatter(x=sim_df.hour, y=sim_df.charge_kw, name="Battery Charge (kW)", line=dict(color="#F59E0B", dash="dash")))
        fig_ts.update_layout(title="24-Hour Energy Balance", xaxis_title="Hour of Day", yaxis_title="Power (kW)", height=340)
        st.plotly_chart(fig_ts, use_container_width=True)

        # PandaPower Voltage & Line Loading
        st.markdown("#### ⚡ PandaPower Distribution Feeder Analysis")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fig_v = go.Figure(go.Scatter(x=feeder_df.hour, y=feeder_df.min_voltage_pu, mode="lines+markers", line=dict(color="#D97706")))
            fig_v.add_hline(y=0.95, line_dash="dash", line_color="#DC2626", annotation_text="Grid Lower Limit (0.95 p.u.)")
            fig_v.update_layout(title="Bus Voltage Profile (p.u.)", xaxis_title="Hour", height=280)
            st.plotly_chart(fig_v, use_container_width=True)
        with col_f2:
            fig_l = go.Figure(go.Bar(x=feeder_df.hour, y=feeder_df.line_loading_pct, marker_color="#EA580C"))
            fig_l.add_hline(y=100.0, line_dash="dash", line_color="#DC2626", annotation_text="100% Thermal Rating")
            fig_l.update_layout(title="Distribution Line Loading (%)", xaxis_title="Hour", height=280)
            st.plotly_chart(fig_l, use_container_width=True)

        st.dataframe(sim_df, use_container_width=True)
    else:
        st.info("Run `python -m simulation.scenarios` to generate scenario CSVs.")

# ----------------- TAB 3: BENCHMARK SUITE & TESTS -----------------
with tab_benchmark:
    st.subheader("🔬 Benchmark Validation & Automated Tests")
    st.write("Run mathematical unit tests confirming energy conservation and anti-hallucination compliance.")

    if st.button("🧪 Execute Pytest Suite", type="primary"):
        import pytest
        class TestPlugin:
            def __init__(self):
                self.reports = []
            def pytest_runtest_logreport(self, report):
                if report.when == "call":
                    self.reports.append(report)

        plugin = TestPlugin()
        ret = pytest.main(["-q", "tests/"], plugins=[plugin])
        
        passed = sum(1 for r in plugin.reports if r.passed)
        failed = sum(1 for r in plugin.reports if r.failed)
        
        if failed == 0:
            st.success(f"✅ All {passed} Automated Tests Passed Successfully!")
        else:
            st.error(f"❌ Tests Finished with {failed} failures ({passed} passed).")
            
        for r in plugin.reports:
            status_icon = "✅" if r.passed else "❌"
            st.text(f"{status_icon} {r.nodeid.split('::')[-1]}")
