"""CLI smoke tests."""

from rag_injection_lab.cli import build_parser, main


def test_parser_has_expected_commands():
    p = build_parser()
    # ensure subparsers exist
    assert p.parse_args(["list-rules"]).command == "list-rules"


def test_list_rules_exit_zero():
    assert main(["list-rules"]) == 0
