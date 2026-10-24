"""The job that answers an Instagram comment that named an owner's keyword."""

from app.schemas.typings.platform.constrained_strings import JobName

# An inbox event COMMENT_TRIGGER: its private reply queued in the outbox.
PROCESS_COMMENT_TRIGGER_JOB: JobName = JobName("process_comment_trigger")
