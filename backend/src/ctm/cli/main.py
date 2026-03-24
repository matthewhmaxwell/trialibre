"""Trialibre CLI entry point."""

from __future__ import annotations

import click


@click.group()
@click.version_option()
def cli():
    """Trialibre - Clinical trial patient matching platform."""
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=8000, help="Server port (0 for auto)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """Start the Trialibre server."""
    import uvicorn
    uvicorn.run(
        "ctm.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.argument("patient_text")
@click.option("--max-trials", default=20, help="Maximum trials to evaluate")
def match(patient_text: str, max_trials: int):
    """Match a patient against clinical trials."""
    import asyncio
    from ctm.config import load_settings
    from ctm.models.patient import PatientNote
    from ctm.pipeline.orchestrator import PipelineOrchestrator
    from ctm.providers.registry import create_provider
    from ctm.sandbox.loader import load_sample_protocols

    async def run():
        settings = load_settings()
        llm = None
        if not settings.sandbox.enabled:
            try:
                llm = create_provider(settings.llm)
            except Exception:
                settings.sandbox.enabled = True

        patient = PatientNote(patient_id="cli-patient", raw_text=patient_text)
        trials = load_sample_protocols()
        orchestrator = PipelineOrchestrator(settings, llm)
        ranking = await orchestrator.match_patient(patient, trials, max_trials=max_trials)

        click.echo(f"\nFound {len(ranking.scores)} matches for patient:")
        for score in ranking.scores[:10]:
            icon = {"strong": "✓", "possible": "?", "unlikely": "✗"}[score.strength.value]
            click.echo(f"  {icon} [{score.strength.value.upper():8s}] {score.trial_title}")
            click.echo(f"    Score: {score.combined_score:.2f} | Criteria: {score.criteria_met}/{score.criteria_total} met")

    asyncio.run(run())


@cli.command()
def sandbox():
    """Show sandbox data summary."""
    from ctm.sandbox.loader import get_sandbox_summary
    summary = get_sandbox_summary()
    click.echo("Sandbox Data:")
    click.echo(f"  Patients: {summary['patients_count']}")
    click.echo(f"  Trials: {summary['trials_count']}")
    click.echo(f"  Ground truth pairs: {summary['ground_truth_pairs']}")
    click.echo(f"  Languages: {', '.join(summary['languages_available'])}")
    click.echo(f"  Conditions: {', '.join(summary['conditions_covered'][:5])}...")


if __name__ == "__main__":
    cli()
