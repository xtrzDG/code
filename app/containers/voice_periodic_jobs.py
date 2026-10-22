"""The worker's periodic jobs of the voice agents (`periodic_job_specs`)."""

from dependency_injector.providers import Factory

from app.containers.operators.operators_container import OperatorsContainer
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.gateways.worker.periodic.resync_voice_agents import resync_voice_agents_job


def voice_periodic_job_specs(
    operators: OperatorsContainer,
) -> list[Factory[PeriodicJobSpec]]:
    """Live voice agents of an older revision set up again, hourly (W20)."""

    return [
        Factory(
            resync_voice_agents_job,
            operator=operators.conversations.resync_voice_agents_operator,
        )
    ]
