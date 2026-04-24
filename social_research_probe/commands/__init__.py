"""CLI command implementations."""

from enum import StrEnum


class Command(StrEnum):
    """Top-level CLI command names dispatched via handlers_factory.
    Each enum member maps to the exact command string accepted by the CLI.
    Example:
        Use command constants when registering handlers:
        ```python
        handlers = {
            Command.UPDATE_TOPICS: handle_update_topics,
            Command.SHOW_TOPICS: handle_show_topics,
        }
        ```
    """

    UPDATE_TOPICS = "update-topics"
    SHOW_TOPICS = "show-topics"
    UPDATE_PURPOSES = "update-purposes"
    SHOW_PURPOSES = "show-purposes"
    SUGGEST_TOPICS = "suggest-topics"
    SUGGEST_PURPOSES = "suggest-purposes"
    SHOW_PENDING = "show-pending"
    APPLY_PENDING = "apply-pending"
    DISCARD_PENDING = "discard-pending"
    STAGE_SUGGESTIONS = "stage-suggestions"
    RESEARCH = "research"
    CORROBORATE_CLAIMS = "corroborate-claims"
    RENDER = "render"
    INSTALL_SKILL = "install-skill"
    SETUP = "setup"
    REPORT = "report"
    SERVE_REPORT = "serve-report"
    CONFIG = "config"


class ConfigSubcommand(StrEnum):
    """Config subcommand names dispatched within config.run().
    These are not top-level commands; they are sub-actions under the CONFIG command.
    """

    SHOW = "show"
    PATH = "path"
    SET = "set"
    SET_SECRET = "set-secret"
    UNSET_SECRET = "unset-secret"
    CHECK_SECRETS = "check-secrets"


class SpecialCommand(StrEnum):
    """Argparse built-in commands handled outside handlers_factory.
    These are not dispatched to command modules; they are processed directly in main().
    """

    HELP = "help"
    VERSION = "version"
