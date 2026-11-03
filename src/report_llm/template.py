"""Parse report templates into data placeholders and LLM-filled sections.

Template syntax:
    {{data:name}}        filled directly from the data source
    {{section:name}}     written by the LLM
    <!-- llm: ... -->    instruction for the section placeholder that follows it
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{\s*(data|section)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
INSTRUCTION_RE = re.compile(r"<!--\s*llm:\s*(.*?)\s*-->", re.DOTALL)


class TemplateError(ValueError):
    """Raised when a template is malformed."""


@dataclass
class Section:
    name: str
    instruction: str | None
    line: int


@dataclass
class Template:
    text: str
    data_fields: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)

    def section(self, name: str) -> Section:
        for s in self.sections:
            if s.name == name:
                return s
        raise KeyError(name)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def parse_template(text: str) -> Template:
    """Parse template text into data fields and sections.

    An `<!-- llm: ... -->` comment applies to the next section placeholder.
    A data placeholder in between does not consume it.
    """
    template = Template(text=text)
    seen_sections: set[str] = set()

    # Merge instructions and placeholders into one ordered stream.
    events: list[tuple[int, str, str]] = []
    for m in INSTRUCTION_RE.finditer(text):
        events.append((m.start(), "instruction", " ".join(m.group(1).split())))
    for m in PLACEHOLDER_RE.finditer(text):
        events.append((m.start(), m.group(1), m.group(2)))
    events.sort(key=lambda e: e[0])

    pending: str | None = None
    for pos, kind, value in events:
        if kind == "instruction":
            if pending is not None:
                raise TemplateError(
                    f"line {_line_of(text, pos)}: two llm instructions in a row "
                    "with no section placeholder between them"
                )
            pending = value
        elif kind == "data":
            if value not in template.data_fields:
                template.data_fields.append(value)
        else:  # section
            if value in seen_sections:
                raise TemplateError(f"line {_line_of(text, pos)}: duplicate section '{value}'")
            seen_sections.add(value)
            template.sections.append(Section(value, pending, _line_of(text, pos)))
            pending = None

    if pending is not None:
        raise TemplateError("llm instruction at end of template has no section placeholder")

    return template


def load_template(path: str | Path) -> Template:
    return parse_template(Path(path).read_text(encoding="utf-8"))
