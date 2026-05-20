"""
Excel COM automation tools.

Real implementation uses win32com.client (Windows only).
On Linux/macOS the tools return clearly-labelled mock data so the full
MCP protocol can be exercised during development.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock(label: str, **kwargs) -> dict:
    detail = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return {"mock": True, "tool": label, "params": detail,
            "note": "Windows COM not available on this platform"}


def _csv_to_nested(data: str) -> list[list[str]]:
    return [row.split(",") for row in data.strip().splitlines()]


# ── Registration ──────────────────────────────────────────────────────────────

def register(mcp: "FastMCP", is_windows: bool) -> None:  # noqa: C901

    @mcp.tool()
    def excel_list_sheets(workbook_path: str) -> list[str]:
        """Return the names of all sheets in an Excel workbook."""
        if not is_windows:
            return ["Sheet1", "Sheet2", "Data (mock)"]
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        wb = xl.Workbooks.Open(workbook_path)
        names = [ws.Name for ws in wb.Sheets]
        wb.Close(SaveChanges=False)
        xl.Quit()
        return names

    @mcp.tool()
    def excel_get_range(
        workbook_path: str,
        sheet: str,
        range_address: str,
    ) -> str:
        """
        Read values from an Excel range and return them as CSV text.

        Args:
            workbook_path: Absolute path to the .xlsx / .xlsm file.
            sheet: Sheet name (e.g. "Sheet1").
            range_address: Excel range (e.g. "A1:D10" or "A1").

        Returns:
            CSV text, one row per line.
        """
        if not is_windows:
            return _mock(  # type: ignore[return-value]
                "excel_get_range",
                path=workbook_path, sheet=sheet, range=range_address,
            )
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        wb = xl.Workbooks.Open(workbook_path)
        ws = wb.Sheets(sheet)
        values = ws.Range(range_address).Value
        wb.Close(SaveChanges=False)
        xl.Quit()
        if isinstance(values, tuple):
            return "\n".join(
                ",".join("" if c is None else str(c) for c in row)
                for row in values
            )
        return "" if values is None else str(values)

    @mcp.tool()
    def excel_set_range(
        workbook_path: str,
        sheet: str,
        start_cell: str,
        csv_data: str,
    ) -> str:
        """
        Write CSV text data into an Excel range (top-left anchored at *start_cell*).

        Args:
            workbook_path: Absolute path to the workbook.
            sheet: Sheet name.
            start_cell: Top-left cell address (e.g. "B3").
            csv_data: Multi-line CSV string.  Each line → one row.

        Returns:
            Confirmation string.
        """
        if not is_windows:
            rows = _csv_to_nested(csv_data)
            return str(_mock("excel_set_range",  # type: ignore[return-value]
                             path=workbook_path, sheet=sheet,
                             start=start_cell, rows=len(rows)))
        import win32com.client
        rows = _csv_to_nested(csv_data)
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        wb = xl.Workbooks.Open(workbook_path)
        ws = wb.Sheets(sheet)
        anchor = ws.Range(start_cell)
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                ws.Cells(anchor.Row + r, anchor.Column + c).Value = val
        wb.Save()
        wb.Close()
        xl.Quit()
        return f"Written {len(rows)} rows × {len(rows[0])} cols to {sheet}!{start_cell}"

    @mcp.tool()
    def excel_get_named_range(workbook_path: str, name: str) -> str:
        """
        Read a named range from an Excel workbook (e.g. a table of section properties).

        Returns:
            CSV text of the named range values.
        """
        if not is_windows:
            return str(_mock("excel_get_named_range", path=workbook_path, name=name))  # type: ignore[return-value]
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        wb = xl.Workbooks.Open(workbook_path)
        rng = wb.Names(name).RefersToRange
        values = rng.Value
        wb.Close(SaveChanges=False)
        xl.Quit()
        if isinstance(values, tuple):
            return "\n".join(",".join("" if c is None else str(c) for c in row) for row in values)
        return "" if values is None else str(values)

    @mcp.tool()
    def excel_run_macro(
        workbook_path: str,
        macro_name: str,
        args: list[str] | None = None,
    ) -> str:
        """
        Run a VBA macro inside an Excel workbook.

        Args:
            workbook_path: Absolute path to an .xlsm / .xlam file.
            macro_name: Macro name, e.g. "Module1.RunDesign".
            args: Optional list of string arguments passed to the macro.

        Returns:
            String representation of the macro's return value (if any).
        """
        if not is_windows:
            return str(_mock("excel_run_macro",  # type: ignore[return-value]
                             path=workbook_path, macro=macro_name, args=args))
        import win32com.client
        xl = win32com.client.Dispatch("Excel.Application")
        xl.Visible = False
        wb = xl.Workbooks.Open(workbook_path)
        result = xl.Run(macro_name, *(args or []))
        wb.Save()
        wb.Close()
        xl.Quit()
        return str(result)
