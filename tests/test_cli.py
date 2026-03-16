from pipeline import cli


def test_cli_module_exposes_main():
    assert callable(cli.main)


def test_cli_supports_pipeline_stage_subcommands():
    parser = cli.build_parser()
    args = parser.parse_args(["source", "discover", "--deal", "imprivata"])

    assert args.command == "source"
    assert args.source_command == "discover"
    assert args.deal == ["imprivata"]


def test_cli_supports_raw_fetch_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["raw", "fetch", "--deal", "imprivata", "--workers", "4"])

    assert args.command == "raw"
    assert args.raw_command == "fetch"
    assert args.deal == ["imprivata"]
    assert args.workers == 4


def test_cli_supports_preprocess_source_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["preprocess", "source", "--deal", "zep", "--workers", "2"])

    assert args.command == "preprocess"
    assert args.preprocess_command == "source"
    assert args.deal == ["zep"]
    assert args.workers == 2


def test_cli_supports_validate_references_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["validate", "references"])

    assert args.command == "validate"
    assert args.validate_command == "references"
