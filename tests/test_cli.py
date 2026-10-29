import pytest

from stemwise import cli


def test_bare_flags_mean_serve(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli, "cmd_serve", lambda args: seen.update(port=args.port, no_open=args.no_open) or 0)
    monkeypatch.setattr(cli.sys, "argv", ["stemwise", "--port", "9100", "--no-open"])
    assert cli.main() == 0
    assert seen == {"port": 9100, "no_open": True}


def test_serve_refuses_to_bind_every_interface(capsys):
    assert cli.main(["serve", "--host", "0.0.0.0"]) == 2
    assert "Bind to one address" in capsys.readouterr().err


def test_version_flag_is_not_rewritten(capsys):
    with pytest.raises(SystemExit) as stop:
        cli.main(["--version"])
    assert stop.value.code == 0
