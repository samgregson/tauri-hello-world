"""
Tekla Structural Designer (TSD) COM automation tools.

TSD exposes an API through its COM interface. The exact ProgID varies by
version; common ones are:

  "TSD.Application"    (older versions)
  "Tekla.Structural.Designer.Application"  (v20+, confirm for your version)

⚠️  NOTE: TSD's COM API surface is narrower than SAP2000/ETABS.
Many workflows are better handled via TSD's scripting interface or
its export/import of CSV and Industry Foundation Classes (IFC).

The tools here use the COM API where available and fall back to file-based
exchange (CSV export) for result extraction.

TODO: Confirm the exact ProgID for your TSD version by running in Python:
    import win32com.client
    tsd = win32com.client.Dispatch("Tekla.Structural.Designer.Application")
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from fastmcp import FastMCP

# COM ProgID — update if your TSD version differs
TSD_PROGID = "Tekla.Structural.Designer.Application"

_tsd_app = None


def _mock(label: str, **kwargs) -> dict:
    detail = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return {"mock": True, "tool": label, "params": detail,
            "note": "Windows COM not available on this platform"}


def register(mcp: "FastMCP", is_windows: bool) -> None:  # noqa: C901
    global _tsd_app

    @mcp.tool()
    def tsd_connect(model_path: str | None = None) -> str:
        """
        Connect to a running TSD instance or launch a new one.

        Args:
            model_path: Optional path to a .tsd file to open.

        Returns:
            Status message.
        """
        global _tsd_app
        if not is_windows:
            _tsd_app = "MOCK"
            return "[MOCK] Connected to TSD. Model: " + (model_path or "<none>")
        import win32com.client
        try:
            _tsd_app = win32com.client.GetActiveObject(TSD_PROGID)
        except Exception:
            _tsd_app = win32com.client.Dispatch(TSD_PROGID)
        if model_path:
            _tsd_app.OpenFile(model_path)
        return "Connected to Tekla Structural Designer" + (f"; opened {model_path}" if model_path else "")

    @mcp.tool()
    def tsd_open_model(model_path: str) -> str:
        """Open a TSD .tsd file. Requires tsd_connect() first."""
        if not is_windows:
            return "[MOCK] Opened TSD model: " + model_path
        if _tsd_app is None:
            raise RuntimeError("Call tsd_connect() first.")
        _tsd_app.OpenFile(model_path)
        return f"Opened: {model_path}"

    @mcp.tool()
    def tsd_run_analysis(analysis_type: str = "1st Order Linear") -> str:
        """
        Run a structural analysis in TSD.

        Args:
            analysis_type: One of "1st Order Linear", "2nd Order", "RSA", etc.
                           Refer to TSD API docs for available options.

        Returns:
            Status message.
        """
        if not is_windows:
            return f"[MOCK] TSD analysis '{analysis_type}' complete. 0 errors."
        if _tsd_app is None:
            raise RuntimeError("No TSD model open.")
        # TSD API: method name and enum may differ — confirm in TSD API browser
        _tsd_app.Analyse(analysis_type)
        return f"Analysis '{analysis_type}' complete."

    @mcp.tool()
    def tsd_run_design() -> str:
        """Run the member design checks in TSD (all materials)."""
        if not is_windows:
            return "[MOCK] TSD design complete. All members passed."
        if _tsd_app is None:
            raise RuntimeError("No TSD model open.")
        _tsd_app.Design()
        return "Design complete."

    @mcp.tool()
    def tsd_get_members() -> list[dict]:
        """
        List all structural members in the current TSD model.

        Returns:
            List of dicts: {name, type, material, section}.
        """
        if not is_windows:
            return [
                {"name": "B1", "type": "Beam", "material": "S275", "section": "UB305x165x40"},
                {"name": "C1", "type": "Column", "material": "S355", "section": "UC203x203x46"},
                {"name": "B2", "type": "Beam", "material": "S275", "section": "UB254x102x28"},
            ]
        if _tsd_app is None:
            raise RuntimeError("No TSD model open.")
        members = []
        model = _tsd_app.Model
        for i in range(model.Members.Count):
            m = model.Members.Item(i)
            members.append({
                "name": m.Name,
                "type": m.Type,
                "material": m.Material.Name if hasattr(m, "Material") else "?",
                "section": m.Section.Name if hasattr(m, "Section") else "?",
            })
        return members

    @mcp.tool()
    def tsd_export_results_csv(output_path: str) -> str:
        """
        Export design results to a CSV file using TSD's built-in export.

        This is often more reliable than COM result queries for TSD.

        Args:
            output_path: Destination path for the CSV file.

        Returns:
            Path to the written file.
        """
        if not is_windows:
            mock_csv = (
                "Member,Status,Utilization,CriticalCase\n"
                "B1,PASS,0.72,1.35DL+1.5LL\n"
                "C1,PASS,0.85,1.35DL+1.5LL\n"
                "B2,FAIL,1.03,1.35DL+1.5LL (wind governs)\n"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(mock_csv)
            return output_path
        if _tsd_app is None:
            raise RuntimeError("No TSD model open.")
        # TSD export — refer to TSD API docs for correct method signature
        _tsd_app.ExportDesignResults(output_path)
        return output_path

    @mcp.tool()
    def tsd_get_member_results(member_name: str) -> dict:
        """
        Get design utilization and status for a single member.

        Returns:
            Dict with keys: name, status, utilization, critical_case, governing_check.
        """
        if not is_windows:
            return {
                "name": member_name,
                "status": "PASS",
                "utilization": 0.78,
                "critical_case": "1.35DL+1.5LL",
                "governing_check": "Bending (EC3 6.2.5)",
                "mock": True,
            }
        if _tsd_app is None:
            raise RuntimeError("No TSD model open.")
        model = _tsd_app.Model
        member = model.Members.FindByName(member_name)
        if member is None:
            raise ValueError(f"Member '{member_name}' not found in model.")
        result = member.DesignResult
        return {
            "name": member_name,
            "status": "PASS" if result.Passed else "FAIL",
            "utilization": result.Utilization,
            "critical_case": result.CriticalCaseName,
            "governing_check": result.GoverningCheckDescription,
        }

    @mcp.tool()
    def tsd_close(save: bool = False) -> str:
        """Close TSD (optionally saving the model first)."""
        global _tsd_app
        if not is_windows:
            _tsd_app = None
            return "[MOCK] TSD closed."
        if _tsd_app is None:
            return "No TSD instance open."
        if save:
            _tsd_app.Save()
        _tsd_app.Close()
        _tsd_app = None
        return "Tekla Structural Designer closed."
