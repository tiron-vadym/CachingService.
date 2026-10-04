import io
import json
import sys
from unittest.mock import MagicMock, patch
import pytest
import httpx

from cli.main import main, run_client
from cli.settings import CliSettings


def test_cli_settings_parse_short_flags():
    args = [
        "-h", "http://testserver:9000/",
        "-r", "4",
        "-j", '{"list_1": ["x"], "list_2": ["y"]}',
        "-o", "result.txt",
    ]
    settings = CliSettings.parse_args(args)
    assert settings.host == "http://testserver:9000"
    assert settings.repeat == 4
    assert settings.json_val == '{"list_1": ["x"], "list_2": ["y"]}'
    assert settings.output == "result.txt"


def test_cli_settings_parse_long_flags():
    args = [
        "--host", "localhost:8080",
        "--repeat", "2",
        "--input", "payload.json",
        "--output", "-",
    ]
    settings = CliSettings.parse_args(args)
    assert settings.host == "http://localhost:8080"
    assert settings.repeat == 2
    assert settings.input == "payload.json"
    assert settings.output == "-"


def test_cli_resolve_payload_from_json():
    data = {"list_1": ["one", "two"], "list_2": ["three", "four"]}
    settings = CliSettings(json=json.dumps(data))
    payload = settings.resolve_payload()
    assert payload.list_1 == ["one", "two"]
    assert payload.list_2 == ["three", "four"]


def test_cli_resolve_payload_from_file(tmp_path):
    data = {"list_1": ["alpha"], "list_2": ["beta"]}
    file_path = tmp_path / "test_input.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    settings = CliSettings(input=str(file_path))
    payload = settings.resolve_payload()
    assert payload.list_1 == ["alpha"]
    assert payload.list_2 == ["beta"]


def test_cli_resolve_payload_from_stdin(monkeypatch):
    data = {"list_1": ["std1"], "list_2": ["std2"]}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(data)))

    settings = CliSettings(input="-")
    payload = settings.resolve_payload()
    assert payload.list_1 == ["std1"]
    assert payload.list_2 == ["std2"]


def test_cli_resolve_payload_invalid_json():
    settings = CliSettings(json="{not valid json}")
    with pytest.raises(ValueError, match="Invalid JSON input"):
        settings.resolve_payload()


def test_cli_resolve_payload_unequal_lengths():
    data = {"list_1": ["a", "b"], "list_2": ["c"]}
    settings = CliSettings(json=json.dumps(data))
    with pytest.raises(ValueError, match="must have the exact same length"):
        settings.resolve_payload()


def test_cli_resolve_payload_missing():
    settings = CliSettings()
    with patch("sys.stdin.isatty", return_value=True):
        with pytest.raises(ValueError, match="No input payload provided"):
            settings.resolve_payload()


def test_run_client_success_stdout(capsys):
    data = {"list_1": ["cat"], "list_2": ["dog"]}
    settings = CliSettings(json=json.dumps(data), output="-", repeat=1)

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.json.return_value = {"id": "test-uuid-1", "message": "created"}

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"output": "CAT, DOG"}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_post_resp
        mock_client.get.return_value = mock_get_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        exit_code = run_client(settings)
        assert exit_code == 0

    captured = capsys.readouterr()
    assert captured.out.strip() == "CAT, DOG"


def test_run_client_success_file_output(tmp_path):
    data = {"list_1": ["first"], "list_2": ["second"]}
    out_file = tmp_path / "out.txt"
    settings = CliSettings(json=json.dumps(data), output=str(out_file), repeat=2)

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.json.return_value = {"id": "test-uuid-2", "message": "created"}

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"output": "FIRST, SECOND"}

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_post_resp
        mock_client.get.return_value = mock_get_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        exit_code = run_client(settings)
        assert exit_code == 0

    assert out_file.read_text(encoding="utf-8").strip() == "FIRST, SECOND"


def test_run_client_server_error():
    data = {"list_1": ["err"], "list_2": ["err"]}
    settings = CliSettings(json=json.dumps(data))

    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 500
    mock_post_resp.text = "Internal error"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_post_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        exit_code = run_client(settings)
        assert exit_code == 1


def test_main_help_flag():
    exit_code = main(["--help"])
    assert exit_code == 0


def test_run_client_connect_error():
    data = {"list_1": ["x"], "list_2": ["y"]}
    settings = CliSettings(json=json.dumps(data))
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value.__enter__.return_value = mock_client
        assert run_client(settings) == 1


def test_run_client_timeout_error():
    data = {"list_1": ["x"], "list_2": ["y"]}
    settings = CliSettings(json=json.dumps(data))
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timed out")
        mock_client_cls.return_value.__enter__.return_value = mock_client
        assert run_client(settings) == 1


def test_run_client_post_missing_id():
    data = {"list_1": ["x"], "list_2": ["y"]}
    settings = CliSettings(json=json.dumps(data))
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"message": "missing id"}
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client
        assert run_client(settings) == 1


def test_run_client_get_failure():
    data = {"list_1": ["x"], "list_2": ["y"]}
    settings = CliSettings(json=json.dumps(data))
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 201
    mock_post_resp.json.return_value = {"id": "uuid-1", "message": "created"}
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404
    mock_get_resp.text = "Not found"
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_post_resp
        mock_client.get.return_value = mock_get_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client
        assert run_client(settings) == 1


def test_main_argument_parse_error():
    # Negative repeat value violates validator
    exit_code = main(["--repeat", "0"])
    assert exit_code == 1

