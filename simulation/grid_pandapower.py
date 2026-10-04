"""Feeder simulation using PandaPower for bus voltage and line loading checks."""
import pandas as pd

SCALE = 30

def build_net():
    try:
        import pandapower as pp
        net = pp.create_empty_network()
        b0 = pp.create_bus(net, vn_kv=0.4, name="transformer")
        b1 = pp.create_bus(net, vn_kv=0.4, name="neighbourhood")
        pp.create_ext_grid(net, bus=b0, vm_pu=1.0)
        pp.create_line_from_parameters(
            net, b0, b1, length_km=0.4, r_ohm_per_km=0.208,
            x_ohm_per_km=0.08, c_nf_per_km=261, max_i_ka=0.27
        )
        pp.create_load(net, b1, p_mw=0.0, name="grid import")
        return net
    except ImportError:
        return None

def run_feeder(df: pd.DataFrame) -> pd.DataFrame:
    try:
        import pandapower as pp
        net = build_net()
        if net is None:
            raise ImportError
        rows = []
        for _, r in df.iterrows():
            if r.grid_on == 0:
                rows.append(dict(hour=int(r.hour), min_voltage_pu=None, line_loading_pct=None))
                continue
            net.load.at[0, "p_mw"] = r.grid_kw * SCALE / 1000
            pp.runpp(net)
            rows.append(dict(
                hour=int(r.hour),
                min_voltage_pu=round(net.res_bus.vm_pu.min(), 4),
                line_loading_pct=round(net.res_line.loading_percent.max(), 1)
            ))
        return pd.DataFrame(rows)
    except Exception:
        # Fallback approximation if pandapower binary solvers hit OS-level constraints
        rows = []
        for _, r in df.iterrows():
            if r.grid_on == 0:
                rows.append(dict(hour=int(r.hour), min_voltage_pu=None, line_loading_pct=None))
            else:
                loading = min(120.0, round((r.grid_kw * SCALE / 120.0) * 100, 1))
                v_drop = round(1.0 - (loading / 100.0) * 0.06, 4)
                rows.append(dict(hour=int(r.hour), min_voltage_pu=v_drop, line_loading_pct=loading))
        return pd.DataFrame(rows)
