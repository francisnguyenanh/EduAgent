"""Cloud Trace instrumentation -- one real span per graph node.

Rationale: one complete trace span is the strongest single piece of
"proof of action" available for the demo video. Wired at the lowest common point
(a decorator each node applies to itself) rather than trying to instrument
the ADK Workflow internals, so it works whether a node runs inside the
Tier 1 graph, a standalone script, or a unit test (where it's a no-op if
tracing was never configured).
"""

from __future__ import annotations

import functools
import logging
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from eduagent.config import FIRESTORE

_logger = logging.getLogger(__name__)
_configured = False


def configure_tracing(project_id: str | None = None) -> None:
    """Idempotent: safe to call multiple times (e.g. once per Cloud Run
    instance startup). Falls back to a no-op tracer (spans created but never
    exported) if the exporter can't initialize -- tracing must never be why
    the actual pipeline fails."""
    global _configured
    if _configured:
        return

    project_id = project_id or FIRESTORE.project_id
    try:
        # Opentelemetry-exporter-gcp-trace 1.15+ marks
        # CloudTraceSpanExporter deprecated in favor of routing through an
        # OTLP collector, but that requires standing up and operating a
        # collector -- new infra outside this hackathon's scope, and
        # Already verified this exporter produces real, complete
        # spans in Cloud Trace. Silence exactly this one known, upstream
        # deprecation message (not DeprecationWarning wholesale, which would
        # also hide warnings about eduagent's OWN code) rather than taking on
        # that infra just to clear test output.
        warnings.filterwarnings(
            "ignore",
            message=r"CloudTraceSpanExporter is deprecated\..*",
            category=DeprecationWarning,
        )
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

        provider = TracerProvider(resource=Resource.create({"service.name": "eduagent"}))
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=project_id)))
        trace.set_tracer_provider(provider)
    except Exception:
        _logger.exception("Cloud Trace exporter failed to initialize; spans will not be exported.")
    finally:
        _configured = True


_tracer = trace.get_tracer("eduagent")


def traced_node(name: str) -> Callable:
    """Decorator for graph node functions: wraps the call in a real span
    named `eduagent.node.{name}`, tagging essay_id/student_id from ctx.state
    when available so a trace can be found from a specific essay in logs."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            with _tracer.start_as_current_span(f"eduagent.node.{name}") as span:
                span.set_attribute("eduagent.node", name)
                essay_id = ctx.state.get("essay_id")
                student_id = ctx.state.get("student_id")
                if essay_id:
                    span.set_attribute("eduagent.essay_id", essay_id)
                if student_id:
                    span.set_attribute("eduagent.student_id", student_id)
                try:
                    result = await func(ctx, *args, **kwargs)
                    span.set_attribute("eduagent.status", "ok")
                    return result
                except Exception as exc:
                    span.set_attribute("eduagent.status", "error")
                    span.record_exception(exc)
                    raise

        return wrapper

    return decorator


@contextmanager
def traced_step(name: str, *, essay_id: str | None = None, student_id: str | None = None) -> Iterator[None]:
    """Synchronous counterpart to `traced_node` for call sites that aren't
    graph nodes with a `ctx` (e.g. the interactive HTTP API in api.py, which
    calls node logic directly rather than through the ADK Workflow). Nest
    these inside `traced_pipeline()` so a single HTTP request produces the
    same kind of parent/child waterfall Cloud Trace shows for the batch
    graph, instead of the orphaned single spans that shipped before."""
    with _tracer.start_as_current_span(f"eduagent.node.{name}") as span:
        span.set_attribute("eduagent.node", name)
        if essay_id:
            span.set_attribute("eduagent.essay_id", essay_id)
        if student_id:
            span.set_attribute("eduagent.student_id", student_id)
        try:
            yield
            span.set_attribute("eduagent.status", "ok")
        except Exception as exc:
            span.set_attribute("eduagent.status", "error")
            span.record_exception(exc)
            raise


@contextmanager
def traced_pipeline(name: str, *, student_id: str | None = None) -> Iterator[None]:
    """Root span for one HTTP request through the interactive debate API --
    ensures configure_tracing() has run (idempotent) and opens the parent
    span that `traced_step()` calls nest under."""
    configure_tracing()
    with _tracer.start_as_current_span(name) as span:
        if student_id:
            span.set_attribute("eduagent.student_id", student_id)
        yield
