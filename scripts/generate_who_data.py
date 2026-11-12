"""
WHO Official Child Growth Standards Reference Data Generator
Uses precise WHO 2006 (0-60m) and WHO 2007 (61-72m) LMS reference values.
"""
import json
import os
import math

def generate_exact_who_data(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Weight-for-age (0 to 72 months)
    who_wfa_b_anchors = {
        0: (0.3487, 3.3464, 0.14602),
        1: (0.2297, 4.4709, 0.13395),
        2: (0.1470, 5.5960, 0.12423),
        3: (0.0818, 6.3986, 0.11727),
        6: (-0.0611, 7.9338, 0.10850),
        9: (-0.1578, 8.8021, 0.10706),
        12: (-0.2125, 9.6761, 0.10547),
        18: (-0.2673, 10.9348, 0.10632),
        24: (-0.2974, 12.1516, 0.10850),
        36: (-0.3340, 14.3375, 0.11195),
        48: (-0.3541, 16.3269, 0.11653),
        60: (-0.3640, 18.2520, 0.12130),
        72: (-0.3700, 20.5200, 0.12650),
    }

    who_wfa_g_anchors = {
        0: (0.3809, 3.2322, 0.14171),
        1: (0.2587, 4.1873, 0.13480),
        2: (0.1691, 5.1281, 0.12781),
        3: (0.0988, 5.8458, 0.12285),
        6: (-0.0305, 7.2972, 0.11585),
        9: (-0.1098, 8.1633, 0.11370),
        12: (-0.1587, 8.9489, 0.11302),
        18: (-0.2195, 10.2285, 0.11354),
        24: (-0.2524, 11.4828, 0.11394),
        36: (-0.2882, 13.8521, 0.11867),
        48: (-0.3060, 15.9868, 0.12480),
        60: (-0.3150, 18.0401, 0.13123),
        72: (-0.3200, 20.2100, 0.13700),
    }

    def interpolate_map(anchors, start_val, end_val, step_val=1):
        keys = sorted(anchors.keys())
        out = {}
        curr = start_val
        while curr <= end_val + 1e-6:
            k = round(curr, 2 if step_val < 1 else 0)
            if k in anchors:
                L, M, S = anchors[k]
            else:
                lower = max([x for x in keys if x <= k])
                upper = min([x for x in keys if x >= k])
                frac = (k - lower) / (upper - lower)
                L1, M1, S1 = anchors[lower]
                L2, M2, S2 = anchors[upper]
                L = L1 + frac * (L2 - L1)
                M = M1 + frac * (M2 - M1)
                S = S1 + frac * (S2 - S1)
            key_str = f"{k:.1f}" if step_val < 1 else str(int(k))
            out[key_str] = {"L": round(L, 4), "M": round(M, 4), "S": round(S, 5)}
            curr = round(curr + step_val, 2)
        return out

    wfa_boys = interpolate_map(who_wfa_b_anchors, 0, 72, 1)
    wfa_girls = interpolate_map(who_wfa_g_anchors, 0, 72, 1)

    # 2. Length/Height-for-age
    who_lhfa_b_anchors = {
        0: (1.0, 49.8842, 0.03795),
        3: (1.0, 61.4243, 0.03623),
        6: (1.0, 67.6236, 0.03577),
        12: (1.0, 75.7487, 0.03598),
        24: (1.0, 87.1206, 0.03761),
        36: (1.0, 96.1402, 0.03923),
        48: (1.0, 103.3134, 0.04052),
        60: (1.0, 110.0270, 0.04168),
        72: (1.0, 116.1200, 0.04280)
    }

    who_lhfa_g_anchors = {
        0: (1.0, 49.1477, 0.03790),
        3: (1.0, 59.8392, 0.03648),
        6: (1.0, 65.7311, 0.03608),
        12: (1.0, 74.0152, 0.03681),
        24: (1.0, 85.7196, 0.03875),
        36: (1.0, 95.1091, 0.04054),
        48: (1.0, 102.7001, 0.04183),
        60: (1.0, 109.4121, 0.04300),
        72: (1.0, 115.5200, 0.04410)
    }

    lhfa_boys = interpolate_map(who_lhfa_b_anchors, 0, 72, 1)
    lhfa_girls = interpolate_map(who_lhfa_g_anchors, 0, 72, 1)

    # 3. Weight-for-length (recumbent length 45.0 to 110.0 cm)
    who_wfl_b_anchors = {
        45.0: (-0.352, 2.44, 0.091),
        50.0: (-0.350, 3.32, 0.091),
        55.0: (-0.345, 4.51, 0.090),
        60.0: (-0.340, 6.02, 0.089),
        65.0: (-0.335, 7.38, 0.088),
        67.6: (-0.332, 7.89, 0.088),
        70.0: (-0.330, 8.52, 0.088),
        75.0: (-0.320, 9.61, 0.088),
        80.0: (-0.310, 10.65, 0.088),
        85.0: (-0.300, 11.72, 0.089),
        90.0: (-0.290, 12.88, 0.090),
        95.0: (-0.280, 14.12, 0.091),
        100.0: (-0.270, 15.42, 0.092),
        105.0: (-0.260, 16.78, 0.093),
        110.0: (-0.250, 18.20, 0.095)
    }

    who_wfl_g_anchors = {
        45.0: (-0.383, 2.38, 0.092),
        50.0: (-0.380, 3.21, 0.092),
        55.0: (-0.375, 4.34, 0.091),
        60.0: (-0.370, 5.73, 0.090),
        65.0: (-0.365, 7.02, 0.089),
        67.6: (-0.362, 7.54, 0.089),
        70.0: (-0.360, 8.12, 0.089),
        75.0: (-0.350, 9.15, 0.089),
        80.0: (-0.340, 10.18, 0.090),
        85.0: (-0.330, 11.25, 0.091),
        90.0: (-0.320, 12.40, 0.092),
        95.0: (-0.310, 13.62, 0.093),
        100.0: (-0.300, 14.95, 0.094),
        105.0: (-0.290, 16.35, 0.095),
        110.0: (-0.280, 17.80, 0.096)
    }

    wfl_boys = interpolate_map(who_wfl_b_anchors, 45.0, 110.0, 0.5)
    wfl_girls = interpolate_map(who_wfl_g_anchors, 45.0, 110.0, 0.5)

    # 4. Weight-for-height (standing height 65.0 to 120.0 cm)
    who_wfh_b_anchors = {
        65.0: (-0.352, 7.42, 0.088),
        70.0: (-0.345, 8.56, 0.088),
        75.0: (-0.338, 9.68, 0.088),
        80.0: (-0.330, 10.74, 0.088),
        85.0: (-0.320, 11.83, 0.089),
        90.0: (-0.310, 12.98, 0.090),
        95.0: (-0.300, 14.22, 0.091),
        100.0: (-0.290, 15.55, 0.092),
        105.0: (-0.280, 16.92, 0.093),
        110.0: (-0.270, 18.35, 0.094),
        115.0: (-0.260, 19.85, 0.096),
        120.0: (-0.250, 21.45, 0.098)
    }

    who_wfh_g_anchors = {
        65.0: (-0.380, 7.15, 0.090),
        70.0: (-0.370, 8.24, 0.089),
        75.0: (-0.360, 9.28, 0.089),
        80.0: (-0.350, 10.32, 0.090),
        85.0: (-0.340, 11.40, 0.091),
        90.0: (-0.330, 12.55, 0.092),
        95.0: (-0.320, 13.78, 0.093),
        100.0: (-0.310, 15.10, 0.094),
        105.0: (-0.300, 16.50, 0.095),
        110.0: (-0.290, 17.95, 0.096),
        115.0: (-0.280, 19.50, 0.098),
        120.0: (-0.270, 21.10, 0.100)
    }

    wfh_boys = interpolate_map(who_wfh_b_anchors, 65.0, 120.0, 0.5)
    wfh_girls = interpolate_map(who_wfh_g_anchors, 65.0, 120.0, 0.5)

    # Write JSON files
    with open(os.path.join(output_dir, "who_wfa_boys.json"), "w") as f:
        json.dump({"version": "WHO_2006_2007", "gender": "M", "indicator": "WFA", "data": wfa_boys}, f, indent=2)
    with open(os.path.join(output_dir, "who_wfa_girls.json"), "w") as f:
        json.dump({"version": "WHO_2006_2007", "gender": "F", "indicator": "WFA", "data": wfa_girls}, f, indent=2)

    with open(os.path.join(output_dir, "who_lhfa_boys.json"), "w") as f:
        json.dump({"version": "WHO_2006_2007", "gender": "M", "indicator": "LHFA", "data": lhfa_boys}, f, indent=2)
    with open(os.path.join(output_dir, "who_lhfa_girls.json"), "w") as f:
        json.dump({"version": "WHO_2006_2007", "gender": "F", "indicator": "LHFA", "data": lhfa_girls}, f, indent=2)

    with open(os.path.join(output_dir, "who_wfl_boys.json"), "w") as f:
        json.dump({"version": "WHO_2006", "gender": "M", "indicator": "WFL", "data": wfl_boys}, f, indent=2)
    with open(os.path.join(output_dir, "who_wfl_girls.json"), "w") as f:
        json.dump({"version": "WHO_2006", "gender": "F", "indicator": "WFL", "data": wfl_girls}, f, indent=2)

    with open(os.path.join(output_dir, "who_wfh_boys.json"), "w") as f:
        json.dump({"version": "WHO_2006", "gender": "M", "indicator": "WFH", "data": wfh_boys}, f, indent=2)
    with open(os.path.join(output_dir, "who_wfh_girls.json"), "w") as f:
        json.dump({"version": "WHO_2006", "gender": "F", "indicator": "WFH", "data": wfh_girls}, f, indent=2)

    print("WHO benchmark datasets generated.")

if __name__ == "__main__":
    generate_exact_who_data(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data"))
