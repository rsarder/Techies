import os
import difflib
from pathlib import Path
from typing import List, Literal

from techies.predefined_tools.base_tool import BaseTool, BaseModel, Field
from Techies.Techies.techies.tools import register_tool

class LineEdit(BaseModel):
    """
    Represents a single line-level edit operation (add or delete), requiring the text to add or delete and the line number. Only supports addition or deletion of entire lines, not partial edits.
    """
    action: Literal["add", "delete"] = Field(
        description="'add' to insert a line, 'delete' to remove a line."
    )
    text: str = Field(
        description="Exact content of the line to insert or delete."
    )
    line_number: int = Field(
        description="1-based index of the line to insert before (add) or delete."
    )

class FileEditToolSchema(BaseModel):
    """
    Arguments schema for the File Edits Tool. Contains the file path and a list of line-level edits to apply.
    """
    file_path: str = Field(
        description="Path to the text file you want to edit."
    )
    edits: List[LineEdit] = Field(
        description="Ordered list of line-level edits to apply."
    )

class FileEditTool(BaseTool):
    """
    Applies precise, line-number-based edits to a text file.
    """
    name = "file_edit_tool"
    description = (
        "Apply precise, line-number-based edits to a text file.  "
        "`action` is 'add' or 'delete'; `text` is the line content; "
        "`line_number` (1-based) is required for both insertion and deletion.  "
        "The `file_path` is interpreted relative to the current working directory."
    )
    args_model = FileEditToolSchema

    def run(self, args: FileEditToolSchema) -> str:
        # resolve relative to the process's cwd
        cwd  = Path(os.getcwd())
        path = (cwd / args.file_path).resolve()

        original = path.read_text(encoding="utf-8").splitlines(keepends=True)
        updated  = original.copy()

        # split edits
        deletes = [e for e in args.edits if e.action == "delete"]
        adds    = [e for e in args.edits if e.action == "add"]

        # 1) deletions (highest line first)
        for edit in sorted(deletes, key=lambda e: e.line_number, reverse=True):
            idx = edit.line_number - 1
            if idx < 0 or idx >= len(updated):
                raise ValueError(f"Line {edit.line_number} out of range")
            if updated[idx].rstrip("\n") != edit.text:
                raise ValueError(
                    f"Content mismatch at line {edit.line_number!r}: "
                    f"expected {edit.text!r}, found {updated[idx].rstrip()!r}"
                )
            updated.pop(idx)

        # 2) additions (lowest line first)
        for edit in sorted(adds, key=lambda e: e.line_number):
            idx = edit.line_number - 1
            if idx < 0 or idx > len(updated):
                raise ValueError(f"Line {edit.line_number} out of range for insert")
            updated.insert(idx, edit.text.rstrip("\n") + "\n")

        # 3) write back and return unified diff
        path.write_text("".join(updated), encoding="utf-8")
        diff = "".join(difflib.unified_diff(
            original, updated,
            fromfile=str(path), tofile=str(path),
            lineterm=""
        ))
        return diff or "No changes applied."

register_tool(
    FileEditTool,
    name="File Edits Tool",
    description="Apply line-level edits to a file using explicit line numbers (paths relative to CWD)",
    args_schema=FileEditToolSchema
)
