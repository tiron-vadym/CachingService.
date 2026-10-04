import argparse
import json
import sys
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, CliSettingsSource

from app.models import PayloadCreateRequest


class CliSettings(BaseSettings):
    """Command-line settings parsed and sanitized using Pydantic Settings."""

    host: str = Field(
        default="http://localhost:8000",
        description="points to the server",
    )
    repeat: int = Field(
        default=1,
        ge=1,
        description="indicates number of iterations",
    )
    input: Optional[str] = Field(
        default=None,
        description="indicates the input file ('-' for stdin)",
    )
    json_val: Optional[str] = Field(
        default=None,
        alias="json",
        description="indicates an input argument in json form (properly escaped)",
    )
    output: str = Field(
        default="-",
        description="indicates the output file ('-' for stdout)",
    )

    @field_validator("host", mode="after")
    @classmethod
    def sanitize_host(cls, v: str) -> str:
        url = v.strip().rstrip("/")
        if not (url.startswith("http://") or url.startswith("https://")):
            url = f"http://{url}"
        return url

    @field_validator("repeat", mode="after")
    @classmethod
    def validate_repeat(cls, v: int) -> int:
        if v < 1:
            raise ValueError("repeat must be an integer >= 1")
        return v

    def resolve_payload(self) -> PayloadCreateRequest:
        """Resolve and validate the payload from json_val, input file, or stdin."""
        raw_text: Optional[str] = None

        if self.json_val:
            raw_text = self.json_val
        elif self.input:
            if self.input == "-":
                raw_text = sys.stdin.read()
            else:
                try:
                    with open(self.input, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                except Exception as e:
                    raise ValueError(f"Failed to read input file '{self.input}': {e}") from e
        else:
            # Check if stdin is piped
            if not sys.stdin.isatty():
                raw_text = sys.stdin.read()

        if not raw_text or not raw_text.strip():
            raise ValueError(
                "No input payload provided. Specify input via --json, --input FILE, or '-' (stdin)."
            )

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON input: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Input JSON must be an object with 'list_1' and 'list_2' arrays.")

        return PayloadCreateRequest.model_validate(parsed)

    @classmethod
    def parse_args(cls, args: Optional[List[str]] = None) -> "CliSettings":
        """Parse command-line arguments using Pydantic Settings CliSettingsSource."""
        cli_args = sys.argv[1:] if args is None else list(args)

        # Handle help explicitly
        if "--help" in cli_args or "-help" in cli_args:
            print_help_and_exit()

        parser = argparse.ArgumentParser(
            prog="cache-cli",
            description="CLI tool to test Caching Microservice programmatically.",
            add_help=False,
        )
        parser.add_argument("--help", action="store_true", help="Show this help message and exit")

        cli_source = CliSettingsSource(
            cls,
            root_parser=parser,
            cli_parse_args=cli_args,
            cli_shortcuts={
                "host": "h",
                "repeat": "r",
                "input": "i",
                "json": "j",
                "output": "o",
            },
            cli_exit_on_error=True,
        )

        values = cli_source()
        return cls(**values)


def print_help_and_exit() -> None:
    """Print standard help message and exit."""
    help_text = """cache-cli [-h|--host URL] [-r|--repeat N] [-i|--input FILE|-] [-j|--json JSON] [-o|--output FILE|-] [--help]

Where:
  -h, --host URL        points to the server (default: http://localhost:8000)
  -r, --repeat N        indicates number of iterations (default: 1)
  -i, --input FILE|-    indicates the input file ('-' for stdin)
  -j, --json JSON       indicates an input argument in json form (properly escaped)
  -o, --output FILE|-   indicates the output file ('-' for stdout, default: -)
  --help                shows this help message and exits
"""
    print(help_text)
    sys.exit(0)
