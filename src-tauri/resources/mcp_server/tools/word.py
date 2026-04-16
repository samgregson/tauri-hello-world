"""Word COM automation tools."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _mock(label: str, **kwargs) -> dict:
    detail = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return {"mock": True, "tool": label, "params": detail,
            "note": "Windows COM not available on this platform"}


def register(mcp: "FastMCP", is_windows: bool) -> None:

    @mcp.tool()
    def word_get_text(document_path: str) -> str:
        """Extract all plain text from a Word document."""
        if not is_windows:
            return "[MOCK] Lorem ipsum dolor sit amet. This is the text of " + document_path
        import win32com.client
        wd = win32com.client.Dispatch("Word.Application")
        wd.Visible = False
        doc = wd.Documents.Open(document_path)
        text = doc.Content.Text
        doc.Close(SaveChanges=False)
        wd.Quit()
        return text

    @mcp.tool()
    def word_replace_text(
        document_path: str,
        find_text: str,
        replace_text: str,
        save: bool = True,
    ) -> str:
        """
        Find-and-replace text throughout a Word document.

        Args:
            document_path: Absolute path to the .docx file.
            find_text: The text to search for.
            replace_text: Replacement text.
            save: Whether to save the document after replacing.

        Returns:
            Number of replacements made.
        """
        if not is_windows:
            return str(_mock("word_replace_text", find=find_text, replace=replace_text))  # type: ignore[return-value]
        import win32com.client
        wdReplaceAll = 2
        wd = win32com.client.Dispatch("Word.Application")
        wd.Visible = False
        doc = wd.Documents.Open(document_path)
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(
            FindText=find_text,
            ReplaceWith=replace_text,
            Replace=wdReplaceAll,
        )
        count = find.Found  # True/False; Word doesn't expose replacement count directly
        if save:
            doc.Save()
        doc.Close(SaveChanges=False)
        wd.Quit()
        return f"Replacement complete (Found: {count})"

    @mcp.tool()
    def word_get_tables(document_path: str) -> list[dict]:
        """
        Extract all tables from a Word document.

        Returns:
            List of tables, each a dict with keys 'index' (1-based) and 'rows' (list of CSV strings).
        """
        if not is_windows:
            return [
                {"index": 1, "rows": ["Member,Section,Fy", "C1,W10x49,50 ksi"]},
                {"index": 2, "rows": ["Load Case,Dead,Live", "D+L,10,5"]},
            ]
        import win32com.client
        wd = win32com.client.Dispatch("Word.Application")
        wd.Visible = False
        doc = wd.Documents.Open(document_path)
        result = []
        for i, tbl in enumerate(doc.Tables, start=1):
            rows = []
            for row in range(1, tbl.Rows.Count + 1):
                cells = [tbl.Cell(row, col).Range.Text.rstrip('\r\x07')
                         for col in range(1, tbl.Columns.Count + 1)]
                rows.append(",".join(cells))
            result.append({"index": i, "rows": rows})
        doc.Close(SaveChanges=False)
        wd.Quit()
        return result

    @mcp.tool()
    def word_insert_text_at_bookmark(
        document_path: str,
        bookmark_name: str,
        text: str,
        save: bool = True,
    ) -> str:
        """
        Insert (overwrite) text at a named bookmark in a Word document.
        Useful for populating report templates.
        """
        if not is_windows:
            return str(_mock("word_insert_text_at_bookmark",  # type: ignore[return-value]
                             path=document_path, bookmark=bookmark_name))
        import win32com.client
        wd = win32com.client.Dispatch("Word.Application")
        wd.Visible = False
        doc = wd.Documents.Open(document_path)
        bm = doc.Bookmarks(bookmark_name)
        bm.Range.Text = text
        # Re-add the bookmark (inserting text deletes it)
        doc.Bookmarks.Add(bookmark_name, bm.Range)
        if save:
            doc.Save()
        doc.Close(SaveChanges=False)
        wd.Quit()
        return f"Inserted text at bookmark '{bookmark_name}'"
