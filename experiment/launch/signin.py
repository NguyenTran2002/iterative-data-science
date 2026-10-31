"""Pick the sign-in variable for the containers. The value is passed on, never shown."""
from collections.abc import Mapping

SIGNIN_VARS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")


def signin_env(environ: Mapping[str, str]) -> tuple[str, str]:
    for name in SIGNIN_VARS:
        if environ.get(name):
            return name, environ[name]
    raise SystemExit("Set CLAUDE_CODE_OAUTH_TOKEN (a plan token from `claude setup-token`) "
                     "or ANTHROPIC_API_KEY in this shell first.")
