"""
The Prometheus text of one scrape: this process's series, or with
PROMETHEUS_MULTIPROC_DIR those of every process of the instance (several
uvicorn workers), plus series read at scrape time (the job queue's depth).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest
from prometheus_client.metrics_core import Metric
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.platform_collector import PlatformCollector
from prometheus_client.process_collector import ProcessCollector
from prometheus_client.registry import Collector

from app.schemas.typings.platform.strings import LocalDirectoryPath


@dataclass(frozen=True)
class MetricsPage:
    """One scrape's answer: the exposition text and its content type."""

    body: bytes
    content_type: str = CONTENT_TYPE_LATEST


class RegistryView(Collector):
    """The series of a registry, offered to another one at scrape time."""

    def __init__(self, registry: CollectorRegistry) -> None:
        self._registry: CollectorRegistry = registry

    def collect(self) -> Iterable[Metric]:
        return self._registry.collect()


def build_metrics_registry(
    multiproc_directory: LocalDirectoryPath | None,
) -> CollectorRegistry:
    """
    The registry of one application container's series. Alone in its
    process (no PROMETHEUS_MULTIPROC_DIR), it also reports the process's
    CPU, memory and Python runtime; in multiprocess mode those cannot be
    added up across processes and are left out.
    """

    registry = CollectorRegistry(auto_describe=True)
    if multiproc_directory is None:
        ProcessCollector(registry=registry)
        PlatformCollector(registry=registry)

    return registry


def render_metrics(
    registry: CollectorRegistry,
    multiproc_directory: LocalDirectoryPath | None,
    scrape_collectors: Sequence[Collector] = (),
) -> MetricsPage:
    """The exposition text of one scrape (see the module)."""

    scrape = CollectorRegistry(auto_describe=False)
    if multiproc_directory is None:
        scrape.register(RegistryView(registry))
    else:
        # prometheus_client leaves this constructor unannotated.
        MultiProcessCollector(scrape, path=str(multiproc_directory))  # type: ignore[no-untyped-call]

    for collector in scrape_collectors:
        scrape.register(collector)

    return MetricsPage(body=generate_latest(scrape))
