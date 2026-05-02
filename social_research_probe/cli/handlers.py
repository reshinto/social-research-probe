"""Command handlers for topics, purposes, suggestions, config, and skill commands."""

from __future__ import annotations

import argparse


def _handle_update_topics(args: argparse.Namespace) -> int:
    from social_research_probe.commands import update_topics

    return update_topics.run(args)


def _handle_show_topics(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_topics

    return show_topics.run(args)


def _handle_update_purposes(args: argparse.Namespace) -> int:
    from social_research_probe.commands import update_purposes

    return update_purposes.run(args)


def _handle_show_purposes(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_purposes

    return show_purposes.run(args)


def _handle_suggest_topics(args: argparse.Namespace) -> int:
    from social_research_probe.commands import suggest_topics

    return suggest_topics.run(args)


def _handle_suggest_purposes(args: argparse.Namespace) -> int:
    from social_research_probe.commands import suggest_purposes

    return suggest_purposes.run(args)


def _handle_show_pending(args: argparse.Namespace) -> int:
    from social_research_probe.commands import show_pending

    return show_pending.run(args)


def _handle_apply_pending(args: argparse.Namespace) -> int:
    from social_research_probe.commands import apply_pending

    return apply_pending.run(args)


def _handle_discard_pending(args: argparse.Namespace) -> int:
    from social_research_probe.commands import discard_pending

    return discard_pending.run(args)


def _handle_stage_suggestions(args: argparse.Namespace) -> int:
    from social_research_probe.commands import stage_suggestions

    return stage_suggestions.run(args)


def _handle_corroborate_claims(args: argparse.Namespace) -> int:
    from social_research_probe.commands import corroborate_claims

    return corroborate_claims.run(
        args.input,
        [p.strip() for p in args.providers.split(",") if p.strip()],
        output_path=args.output,
    )


def _handle_render(args: argparse.Namespace) -> int:
    from social_research_probe.commands import render

    return render.run(args.packet, output_dir=args.output_dir)


def _handle_research(args: argparse.Namespace) -> int:
    from social_research_probe.commands import research

    return research.run(args)


def _handle_install_skill(args: argparse.Namespace) -> int:
    from social_research_probe.commands import install_skill

    return install_skill.run(args.target)


def _handle_setup(args: argparse.Namespace) -> int:
    from social_research_probe.commands import setup

    return setup.run()


def _handle_report(args: argparse.Namespace) -> int:
    from social_research_probe.commands import report

    return report.run(
        args.packet,
        compiled_synthesis_path=args.compiled_synthesis_path,
        opportunity_analysis_path=args.opportunity_analysis_path,
        final_summary_path=args.final_summary_path,
        out_path=args.out,
    )


def _handle_serve_report(args: argparse.Namespace) -> int:
    from social_research_probe.commands import serve_report

    return serve_report.run(
        args.report,
        host=args.host,
        port=args.port,
        voicebox_base=args.voicebox_base,
    )


def _handle_demo_report(args: argparse.Namespace) -> int:
    from social_research_probe.commands import demo

    return demo.run(args)


def _dispatch_config(args: argparse.Namespace) -> int:
    from social_research_probe.commands import config

    return config.run(args)


def handlers_factory() -> dict[str, callable]:
    """Return the mapping of command names to handler functions."""
    from social_research_probe.commands import Command

    return {
        Command.UPDATE_TOPICS: _handle_update_topics,
        Command.SHOW_TOPICS: _handle_show_topics,
        Command.UPDATE_PURPOSES: _handle_update_purposes,
        Command.SHOW_PURPOSES: _handle_show_purposes,
        Command.SUGGEST_TOPICS: _handle_suggest_topics,
        Command.SUGGEST_PURPOSES: _handle_suggest_purposes,
        Command.SHOW_PENDING: _handle_show_pending,
        Command.APPLY_PENDING: _handle_apply_pending,
        Command.DISCARD_PENDING: _handle_discard_pending,
        Command.STAGE_SUGGESTIONS: _handle_stage_suggestions,
        Command.RESEARCH: _handle_research,
        Command.CORROBORATE_CLAIMS: _handle_corroborate_claims,
        Command.RENDER: _handle_render,
        Command.INSTALL_SKILL: _handle_install_skill,
        Command.SETUP: _handle_setup,
        Command.REPORT: _handle_report,
        Command.SERVE_REPORT: _handle_serve_report,
        Command.DEMO_REPORT: _handle_demo_report,
        Command.CONFIG: _dispatch_config,
    }
