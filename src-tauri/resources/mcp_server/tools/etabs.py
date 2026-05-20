"""
ETABS COM automation tools.

ETABS uses the same CSI OAPI interface as SAP2000 (same SapModel object),
so the patterns are nearly identical.

ProgID (version-agnostic): "CSI.ETABS.API.ETABSObject"
Version-specific examples:  "ETABSv20.ETABSObject", "ETABSv21.ETABSObject"

References:
  - CSI OAPI documentation shipped with ETABS
  - https://wiki.csiamerica.com/display/kb/COM+Automation
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

_etabs_model = None


def _mock(label: str, **kwargs) -> dict:
    detail = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return {"mock": True, "tool": label, "params": detail,
            "note": "Windows COM not available on this platform"}


def _check_ret(ret: int, action: str) -> None:
    if ret != 0:
        raise RuntimeError(f"ETABS API error {ret} during: {action}")


def register(mcp: "FastMCP", is_windows: bool) -> None:  # noqa: C901
    global _etabs_model

    @mcp.tool()
    def etabs_connect(model_path: str | None = None) -> str:
        """
        Connect to a running ETABS instance (or launch a new one) and optionally open a model.

        Returns:
            Status message.
        """
        global _etabs_model
        if not is_windows:
            _etabs_model = "MOCK"
            return "[MOCK] Connected to ETABS. Model: " + (model_path or "<none>")
        import win32com.client
        try:
            etabs_obj = win32com.client.GetActiveObject("CSI.ETABS.API.ETABSObject")
        except Exception:
            etabs_obj = win32com.client.Dispatch("CSI.ETABS.API.ETABSObject")
            etabs_obj.ApplicationStart()
        etabs_obj.Unhide()
        _etabs_model = etabs_obj.SapModel
        if model_path:
            ret = _etabs_model.File.OpenFile(model_path)
            _check_ret(ret, f"OpenFile({model_path})")
        return "Connected to ETABS" + (f"; opened {model_path}" if model_path else "")

    @mcp.tool()
    def etabs_open_model(model_path: str) -> str:
        """Open an ETABS .edb model file. Requires etabs_connect() first."""
        if not is_windows:
            return "[MOCK] Opened ETABS model: " + model_path
        if _etabs_model is None:
            raise RuntimeError("Call etabs_connect() first.")
        ret = _etabs_model.File.OpenFile(model_path)
        _check_ret(ret, f"OpenFile({model_path})")
        return f"Opened: {model_path}"

    @mcp.tool()
    def etabs_run_analysis() -> str:
        """Run the structural analysis on the current ETABS model."""
        if not is_windows:
            return "[MOCK] ETABS analysis complete. 0 errors."
        if _etabs_model is None:
            raise RuntimeError("No ETABS model open.")
        _etabs_model.SetModelIsLocked(False)
        ret = _etabs_model.Analyze.RunAnalysis()
        _check_ret(ret, "RunAnalysis")
        return "Analysis complete."

    @mcp.tool()
    def etabs_run_design_steel() -> str:
        """Run the steel frame design checks on the current ETABS model."""
        if not is_windows:
            return "[MOCK] Steel design complete. 12 members checked, 0 failures."
        if _etabs_model is None:
            raise RuntimeError("No ETABS model open.")
        ret = _etabs_model.DesignSteel.StartDesign()
        _check_ret(ret, "StartDesign (steel)")
        return "Steel design complete."

    @mcp.tool()
    def etabs_run_design_concrete() -> str:
        """Run the concrete frame design checks on the current ETABS model."""
        if not is_windows:
            return "[MOCK] Concrete design complete. 8 members checked, 0 failures."
        if _etabs_model is None:
            raise RuntimeError("No ETABS model open.")
        ret = _etabs_model.DesignConcrete.StartDesign()
        _check_ret(ret, "StartDesign (concrete)")
        return "Concrete design complete."

    @mcp.tool()
    def etabs_get_story_drifts(
        load_case: str,
        direction: str = "X",
    ) -> list[dict]:
        """
        Get story drifts for all stories.

        Args:
            load_case: Load case or combo name.
            direction: "X" or "Y".

        Returns:
            List of dicts: {story, drift_ratio, max_displacement}.
        """
        if not is_windows:
            stories = ["Base", "Floor 1", "Floor 2", "Roof"]
            return [{"story": s, "drift_ratio": round(0.002 + i * 0.0005, 4),
                     "max_displacement_mm": round(2.5 + i * 1.8, 2),
                     "direction": direction, "load_case": load_case, "mock": True}
                    for i, s in enumerate(stories)]
        if _etabs_model is None:
            raise RuntimeError("No ETABS model open.")
        _etabs_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        _etabs_model.Results.Setup.SetCaseSelectedForOutput(load_case)
        ret, n, *data = _etabs_model.Results.StoryDrifts()
        _check_ret(ret, "StoryDrifts")
        # data: [Story, LoadCase, StepType, StepNum, Direction, Drift, Label, X, Y, Z]
        dir_idx = {"X": 0, "Y": 1}.get(direction.upper(), 0)
        return [
            {"story": data[0][i], "drift_ratio": data[5][i],
             "max_displacement_mm": data[9][i], "direction": data[4][i]}
            for i in range(n) if data[4][i].upper() == direction.upper()
        ]

    @mcp.tool()
    def etabs_get_column_forces(
        column_name: str,
        load_case: str,
    ) -> list[dict]:
        """
        Get axial force (P), shear (V2, V3), torsion (T), and moments (M2, M3)
        along an ETABS column or beam element.

        Returns:
            List of station dicts.
        """
        if not is_windows:
            return [{"station": s, "P": -250.0 + s * 10, "V2": 18.5, "V3": 0.0,
                     "T": 0.0, "M2": 0.0, "M3": 55.0 * (1 - s),
                     "mock": True} for s in [0.0, 0.5, 1.0]]
        if _etabs_model is None:
            raise RuntimeError("No ETABS model open.")
        _etabs_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        _etabs_model.Results.Setup.SetCaseSelectedForOutput(load_case)
        ret, n, *data = _etabs_model.Results.FrameForce(column_name, 0)
        _check_ret(ret, f"FrameForce({column_name})")
        return [
            {"station": data[1][i], "P": data[5][i], "V2": data[6][i],
             "V3": data[7][i], "T": data[8][i], "M2": data[9][i], "M3": data[10][i]}
            for i in range(n)
        ]

    @mcp.tool()
    def etabs_close(save: bool = False) -> str:
        """Close the current ETABS model."""
        global _etabs_model
        if not is_windows:
            _etabs_model = None
            return "[MOCK] ETABS closed."
        if _etabs_model is None:
            return "No model open."
        if save:
            _etabs_model.File.Save()
        _etabs_model.ApplicationExit(False)
        _etabs_model = None
        return "ETABS closed."
