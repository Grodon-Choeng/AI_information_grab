from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import typer

from app.container import get_container
from app.core.logging import configure_logging
from app.core.time import date_window_utc
from app.worker.runner import WorkerRunner


app = typer.Typer(help="AI information grab CLI")


def run_async(coro):
    return asyncio.run(coro)


@app.callback()
def main() -> None:
    configure_logging()


@app.command("config-check")
def config_check() -> None:
    container = get_container()
    typer.echo(f"timezone={container.source_config.timezone}")
    typer.echo(f"llm_enabled={container.source_config.llm.enabled}")
    typer.echo(f"sources={','.join(container.source_registry.enabled_sources())}")


@app.command("ingest")
def ingest(
    source: list[str] | None = typer.Option(None, "--source"),
    from_at: datetime | None = typer.Option(None, "--from"),
    to_at: datetime | None = typer.Option(None, "--to"),
) -> None:
    container = get_container()
    runner = WorkerRunner(container)
    result = run_async(
        runner.run_ingest(
            sources=source or None,
            from_at=from_at.astimezone(UTC) if from_at else None,
            to_at=to_at.astimezone(UTC) if to_at else None,
        )
    )
    typer.echo(
        f"run_id={result.run_id} status={result.status} stored_items={result.stored_items} sources={','.join(result.sources)}"
    )


@app.command("digest")
def digest(target_date: date = typer.Option(..., "--date")) -> None:
    container = get_container()
    runner = WorkerRunner(container)
    result = run_async(runner.run_digest(biz_date=target_date))
    typer.echo(
        f"run_id={result.run_id} biz_date={result.biz_date.isoformat()} cluster_count={result.cluster_count} llm_used={result.llm_used}"
    )


@app.command("backfill")
def backfill(
    days: int = typer.Option(1, "--days", min=1),
    source: list[str] | None = typer.Option(None, "--source"),
) -> None:
    container = get_container()
    runner = WorkerRunner(container)
    today = datetime.now(tz=ZoneInfo(container.source_config.timezone)).date()
    for offset in range(days):
        target_date = today - timedelta(days=offset)
        from_at, to_at = date_window_utc(target_date, container.source_config.timezone)
        ingest_result = run_async(runner.run_ingest(sources=source or None, from_at=from_at, to_at=to_at))
        digest_result = run_async(runner.run_digest(biz_date=target_date))
        typer.echo(
            f"date={target_date.isoformat()} ingest_run={ingest_result.run_id} digest_run={digest_result.run_id} clusters={digest_result.cluster_count}"
        )
