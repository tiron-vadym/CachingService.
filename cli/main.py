import sys
import time
from typing import List, Optional
import httpx

from cli.settings import CliSettings


def run_client(settings: CliSettings) -> int:
    """Execute the CLI requests against the caching microservice."""
    try:
        payload_request = settings.resolve_payload()
    except Exception as exc:
        sys.stderr.write(f"Error validating input payload: {exc}\n")
        return 1

    payload_dict = payload_request.model_dump()
    last_output: Optional[str] = None

    try:
        with httpx.Client(timeout=30.0) as client:
            for iteration in range(1, settings.repeat + 1):
                start_time = time.perf_counter()

                # Step 1: Create or fetch existing payload
                post_url = f"{settings.host}/payload"
                post_resp = client.post(post_url, json=payload_dict)

                if post_resp.status_code not in (200, 201):
                    sys.stderr.write(
                        f"POST {post_url} failed with status {post_resp.status_code}: {post_resp.text}\n"
                    )
                    return 1

                post_data = post_resp.json()
                payload_id = post_data.get("id")
                message = post_data.get("message", "")

                if not payload_id:
                    sys.stderr.write(f"Missing 'id' in response: {post_data}\n")
                    return 1

                # Step 2: Read payload content
                get_url = f"{settings.host}/payload/{payload_id}"
                get_resp = client.get(get_url)

                if get_resp.status_code != 200:
                    sys.stderr.write(
                        f"GET {get_url} failed with status {get_resp.status_code}: {get_resp.text}\n"
                    )
                    return 1

                get_data = get_resp.json()
                last_output = get_data.get("output", "")

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                if settings.repeat > 1:
                    sys.stderr.write(
                        f"[Iteration {iteration}/{settings.repeat}] "
                        f"ID: {payload_id} | Elapsed: {elapsed_ms:.2f}ms | {message}\n"
                    )

    except httpx.ConnectError:
        sys.stderr.write(f"Connection error: could not connect to server at {settings.host}\n")
        return 1
    except httpx.TimeoutException:
        sys.stderr.write(f"Timeout error: request to {settings.host} timed out\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"Unexpected error: {exc}\n")
        return 1

    # Write output to stdout or file
    if last_output is not None:
        if settings.output == "-":
            sys.stdout.write(last_output + "\n")
            sys.stdout.flush()
        else:
            try:
                with open(settings.output, "w", encoding="utf-8") as f:
                    f.write(last_output + "\n")
                if settings.repeat > 1:
                    sys.stderr.write(f"Output successfully written to '{settings.output}'\n")
            except Exception as exc:
                sys.stderr.write(f"Failed to write output file '{settings.output}': {exc}\n")
                return 1

    return 0


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    try:
        settings = CliSettings.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 0
    except Exception as exc:
        sys.stderr.write(f"Argument parsing error: {exc}\n")
        return 1

    return run_client(settings)


if __name__ == "__main__":
    sys.exit(main())
