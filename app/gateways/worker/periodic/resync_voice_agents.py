"""
The re-sync of the businesses' voice agents as a periodic job of the
background worker (`ResyncVoiceAgentsUseCase`), every hour across workers:
an agent set up before the platform's current revision is set up again
from its live version (a deploy that changes how agents are built reaches
every live agent within hours, a bounded number per run).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

RESYNC_VOICE_AGENTS_JOB: JobName = JobName("resync_voice_agents")
RESYNC_VOICE_AGENTS_INTERVAL: JobIntervalSeconds = JobIntervalSeconds(60 * 60)


def resync_voice_agents_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=RESYNC_VOICE_AGENTS_JOB,
        interval_seconds=RESYNC_VOICE_AGENTS_INTERVAL,
        operator=operator,
    )
