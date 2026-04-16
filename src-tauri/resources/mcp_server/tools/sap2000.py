"""
SAP2000 COM automation tools.

SAP2000 exposes its full API via COM using the ProgID  "CSI.SAP2000.API.SapObject"
(version-agnostic) or the version-specific form, e.g. "SAP2000v22.SapObject".
Most API calls return an integer error code (0 = success).

References:
  - CSI OAPI documentation shipped with SAP2000
  - https://wiki.csiamerica.com/display/kb/COM+Automation

Typical workflow:
  1. sap2000_connect()          — attach to a running instance or launch one
  2. sap2000_open_model(path)   — open a .sdb file
  3. sap2000_run_analysis()     — run the analysis
  4. sap2000_get_*()            — extract results
  5. sap2000_close()            — unlock / close
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# Module-level handle so tools share the same COM instance within a session
_sap_model = None


def _mock(label: str, **kwargs) -> dict:
    detail = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return {"mock": True, "tool": label, "params": detail,
            "note": "Windows COM not available on this platform"}


def _check_ret(ret: int, action: str) -> None:
    if ret != 0:
        raise RuntimeError(f"SAP2000 API error {ret} during: {action}")


def register(mcp: "FastMCP", is_windows: bool) -> None:  # noqa: C901
    global _sap_model

    @mcp.tool()
    def sap2000_connect(model_path: str | None = None) -> str:
        """
        Connect to a running SAP2000 instance, or launch a new one and optionally
        open *model_path*.

        Returns:
            Status message.
        """
        global _sap_model
        if not is_windows:
            _sap_model = "MOCK"
            return "[MOCK] Connected to SAP2000. Model: " + (model_path or "<none>")
        import win32com.client
        try:
            # Try to attach to an already-running instance first
            sap_obj = win32com.client.GetActiveObject("CSI.SAP2000.API.SapObject")
        except Exception:
            sap_obj = win32com.client.Dispatch("CSI.SAP2000.API.SapObject")
            sap_obj.ApplicationStart()
        sap_obj.Unhide()
        _sap_model = sap_obj.SapModel
        if model_path:
            ret = _sap_model.File.OpenFile(model_path)
            _check_ret(ret, f"OpenFile({model_path})")
        return "Connected to SAP2000" + (f"; opened {model_path}" if model_path else "")

    @mcp.tool()
    def sap2000_open_model(model_path: str) -> str:
        """Open a SAP2000 .sdb model file. Requires sap2000_connect() first."""
        if not is_windows:
            return "[MOCK] Opened model: " + model_path
        if _sap_model is None:
            raise RuntimeError("Call sap2000_connect() before opening a model.")
        ret = _sap_model.File.OpenFile(model_path)
        _check_ret(ret, f"OpenFile({model_path})")
        return f"Opened: {model_path}"

    @mcp.tool()
    def sap2000_run_analysis() -> str:
        """Run the full analysis on the currently open SAP2000 model."""
        if not is_windows:
            return "[MOCK] Analysis complete. 5 load cases, 0 warnings."
        if _sap_model is None:
            raise RuntimeError("No SAP2000 model open. Call sap2000_connect() first.")
        _sap_model.SetModelIsLocked(False)
        ret = _sap_model.Analyze.RunAnalysis()
        _check_ret(ret, "RunAnalysis")
        return "Analysis complete."

    @mcp.tool()
    def sap2000_get_joint_displacements(
        joint_name: str,
        load_case: str,
    ) -> dict:
        """
        Get joint displacements (U1, U2, U3, R1, R2, R3) for a named joint and load case.

        Returns:
            Dict with keys: U1, U2, U3 (translations, mm or in), R1, R2, R3 (rotations, rad).
        """
        if not is_windows:
            return {"U1": 0.12, "U2": 0.00, "U3": -3.45, "R1": 0.0, "R2": 0.001, "R3": 0.0,
                    "mock": True, "joint": joint_name, "case": load_case}
        if _sap_model is None:
            raise RuntimeError("No model open.")
        _sap_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        _sap_model.Results.Setup.SetCaseSelectedForOutput(load_case)
        ret, *vals = _sap_model.Results.JointDispl(joint_name, 0)  # 0 = single step
        # vals: [NumberResults, Obj, ObjSt, StepType, StepNum, U1, U2, U3, R1, R2, R3]
        if ret != 0 or not vals[0]:
            raise RuntimeError(f"No displacement results for joint '{joint_name}' / case '{load_case}'")
        return {"U1": vals[5][0], "U2": vals[6][0], "U3": vals[7][0],
                "R1": vals[8][0], "R2": vals[9][0], "R3": vals[10][0]}

    @mcp.tool()
    def sap2000_get_frame_forces(
        frame_name: str,
        load_case: str,
        num_stations: int = 3,
    ) -> list[dict]:
        """
        Get frame element forces (P, V2, V3, T, M2, M3) along a member.

        Args:
            frame_name: Frame label in the model.
            load_case: Load case or combo name.
            num_stations: Number of stations along the member (min 2).

        Returns:
            List of station dicts, each with keys: station, P, V2, V3, T, M2, M3.
        """
        if not is_windows:
            stations = [0.0, 0.5, 1.0] if num_stations == 3 else [i / (num_stations - 1) for i in range(num_stations)]
            return [{"station": s, "P": -120.5, "V2": 15.2, "V3": 0.0,
                     "T": 0.0, "M2": 0.0, "M3": 45.3 * (1 - abs(s - 0.5) * 2),
                     "mock": True} for s in stations]
        if _sap_model is None:
            raise RuntimeError("No model open.")
        _sap_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        _sap_model.Results.Setup.SetCaseSelectedForOutput(load_case)
        ret, n, *data = _sap_model.Results.FrameForce(frame_name, 0)
        _check_ret(ret, f"FrameForce({frame_name})")
        # data: [Obj, ObjSta, ElmSta, StpTp, StpNm, P, V2, V3, T, M2, M3]
        return [
            {"station": data[1][i], "P": data[5][i], "V2": data[6][i],
             "V3": data[7][i], "T": data[8][i], "M2": data[9][i], "M3": data[10][i]}
            for i in range(n)
        ]

    @mcp.tool()
    def sap2000_get_reactions(load_case: str) -> list[dict]:
        """
        Get support reactions for all restrained joints for a given load case.

        Returns:
            List of dicts with keys: joint, F1, F2, F3, M1, M2, M3.
        """
        if not is_windows:
            return [
                {"joint": "1", "F1": 0.0, "F2": 0.0, "F3": 85.2, "M1": 0.0, "M2": 0.0, "M3": 0.0, "mock": True},
                {"joint": "2", "F1": 0.0, "F2": 0.0, "F3": 92.4, "M1": 0.0, "M2": 0.0, "M3": 0.0, "mock": True},
            ]
        if _sap_model is None:
            raise RuntimeError("No model open.")
        _sap_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        _sap_model.Results.Setup.SetCaseSelectedForOutput(load_case)
        ret, n, *data = _sap_model.Results.JointReact("", 0)  # "" = all joints
        _check_ret(ret, "JointReact")
        return [
            {"joint": data[0][i], "F1": data[5][i], "F2": data[6][i], "F3": data[7][i],
             "M1": data[8][i], "M2": data[9][i], "M3": data[10][i]}
            for i in range(n)
        ]

    @mcp.tool()
    def sap2000_close(save: bool = False) -> str:
        """Close the current SAP2000 model (and optionally save)."""
        global _sap_model
        if not is_windows:
            _sap_model = None
            return "[MOCK] SAP2000 closed."
        if _sap_model is None:
            return "No model open."
        _sap_model.File.Save() if save else None
        _sap_model.ApplicationExit(False)
        _sap_model = None
        return "SAP2000 closed."
