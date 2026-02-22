"""Paid.ai integration — LLM cost tracking and monetisation.

Uses OpenTelemetry + OpenInference instrumentors to automatically trace
all Anthropic and Google GenAI calls. Traces are exported via OTLP to
Paid.ai for cost attribution, margin analysis, and billing.

The paid-python SDK is used separately for business operations (signals,
customers, orders) to track monetisation events.

Usage:
    from app.integrations.paid_client import init_paid_tracing, trace_execution

    # At app startup (before any LLM client is created):
    init_paid_tracing()

    # Per-request attribution (wraps async fn in an OTel span):
    result = await trace_execution("customer_123", "chat", some_async_fn)
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, TypeVar

from app.config import settings

logger = logging.getLogger("agentflow.paid")

T = TypeVar("T")

_initialised = False
_tracer = None

# Paid.ai OTLP endpoint — configurable via env
PAID_OTLP_ENDPOINT = "https://telemetry.paid.ai"


def init_paid_tracing() -> bool:
    """Initialise OpenTelemetry tracing with Paid.ai export + AI SDK instrumentation.

    Must be called once at app startup, before any LLM client is instantiated.
    Returns True if successfully initialised, False if skipped or unavailable.
    """
    global _initialised, _tracer

    if not settings.paid_api_key:
        logger.info("PAID_API_KEY not set — cost tracking disabled.")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        # Configure OTLP exporter to send traces to Paid.ai
        exporter = OTLPSpanExporter(
            endpoint=f"{PAID_OTLP_ENDPOINT}/v1/traces",
            headers={"Authorization": f"Bearer {settings.paid_api_key}"},
        )

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("agentflow")

        # Instrument Anthropic SDK (auto-patches messages.create)
        try:
            from openinference.instrumentation.anthropic import AnthropicInstrumentor
            AnthropicInstrumentor().instrument(tracer_provider=provider)
            logger.info("Anthropic SDK instrumented for cost tracking.")
        except Exception:
            logger.warning("Failed to instrument Anthropic SDK", exc_info=True)

        # Instrument Google GenAI SDK (auto-patches generate_content)
        try:
            from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
            GoogleGenAIInstrumentor().instrument(tracer_provider=provider)
            logger.info("Google GenAI SDK instrumented for cost tracking.")
        except Exception:
            logger.warning("Failed to instrument Google GenAI SDK", exc_info=True)

        _initialised = True
        logger.info("Paid.ai tracing initialised — all LLM calls will be tracked.")
        return True

    except ImportError as e:
        logger.warning("Missing tracing dependency (%s) — run: pip install paid-python", e)
        return False
    except Exception:
        logger.exception("Failed to initialise Paid.ai tracing")
        return False


async def trace_execution(
    customer_id: str,
    product_id: str,
    fn: Callable[..., Coroutine[Any, Any, T]],
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run an async function inside a traced span for per-customer cost attribution.

    Adds customer_id and product_id as span attributes so Paid.ai can
    attribute LLM costs to specific customers and products.
    If tracing is not initialised, the function runs without a span.
    """
    if not _initialised or _tracer is None:
        return await fn(*args, **kwargs)

    with _tracer.start_as_current_span(
        "agentflow.execution",
        attributes={
            "paid.customer_id": customer_id,
            "paid.product_id": product_id,
        },
    ):
        return await fn(*args, **kwargs)


def emit_signal(
    event_name: str,
    customer_id: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Emit a custom billing signal to Paid.ai (e.g. 'pipeline_executed').

    Uses the Paid business SDK to record usage signals for billing.
    No-op if PAID_API_KEY is not set.
    """
    if not settings.paid_api_key:
        return

    try:
        from paid import Paid, Signal

        client = Paid(token=settings.paid_api_key)
        client.signals.record_bulk_v2(
            signals=[
                Signal(
                    event_name=event_name,
                    customer_id=customer_id,
                    data=data or {},
                )
            ]
        )
    except Exception:
        logger.debug("Failed to emit Paid signal: %s", event_name, exc_info=True)
