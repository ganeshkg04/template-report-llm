import pytest

from report_llm.template import TemplateError, load_template, parse_template


def test_example_template(tmp_path):
    t = load_template("examples/audit_summary.md")
    assert t.data_fields == ["report_title", "total_records", "exceptions"]
    assert [s.name for s in t.sections] == ["summary", "observations"]
    assert t.section("summary").instruction.startswith("Write a 3-sentence summary")


def test_instruction_skips_data_placeholder():
    t = parse_template("<!-- llm: be brief -->\n{{data:x}}\n{{section:s}}")
    assert t.section("s").instruction == "be brief"
    assert t.data_fields == ["x"]


def test_section_without_instruction():
    t = parse_template("{{section:s}}")
    assert t.section("s").instruction is None


def test_multiline_instruction_is_collapsed():
    t = parse_template("<!-- llm: line one\n   line two -->\n{{section:s}}")
    assert t.section("s").instruction == "line one line two"


def test_whitespace_inside_braces():
    t = parse_template("{{ data : a }} {{ section : b }}")
    assert t.data_fields == ["a"]
    assert t.sections[0].name == "b"


def test_repeated_data_field_listed_once():
    t = parse_template("{{data:a}} {{data:a}}")
    assert t.data_fields == ["a"]


def test_line_numbers():
    t = parse_template("# Title\n\n{{section:s}}")
    assert t.section("s").line == 3


def test_duplicate_section_rejected():
    with pytest.raises(TemplateError, match="duplicate section"):
        parse_template("{{section:a}}\n{{section:a}}")


def test_two_instructions_in_a_row_rejected():
    with pytest.raises(TemplateError, match="two llm instructions"):
        parse_template("<!-- llm: a -->\n<!-- llm: b -->\n{{section:s}}")


def test_trailing_instruction_rejected():
    with pytest.raises(TemplateError, match="end of template"):
        parse_template("{{section:s}}\n<!-- llm: orphan -->")


def test_unknown_section_lookup():
    t = parse_template("{{section:s}}")
    with pytest.raises(KeyError):
        t.section("missing")
