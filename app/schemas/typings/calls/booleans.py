"""Keep abc order.

Example:
    is_enabled: IsCallSummaryEnabled = True
"""

# The call's summary reached the caller's customer memory.
IsCallRemembered = bool
# The owner turned the recording of the business's calls on (off by
# default).
IsCallRecordingEnabled = bool
# The voice platform's evaluation of a call read that the caller asked to
# be called back by a person.
IsCallbackRequested = bool
IsCallSummaryEnabled = bool
IsCallSummaryGenerated = bool
IsNewMissedCall = bool
# A carrier's webhook (Twilio's fallback or dial status) whose call and
# status were already handled: a signed request sent again.
IsRepeatedCarrierRequest = bool
IsSmsFallbackEnabled = bool
# The owner lets staff play the business's call recordings (off by
# default: owners only).
IsStaffRecordingPlaybackAllowed = bool
# The owner confirmed that the staff who take transferred calls were told,
# as Italian labour law asks of tools that can monitor staff, that the
# voice platform may process the call after the transfer.
IsStaffTransferConfirmed = bool
IsTextBackEnabled = bool
# A call's summary request asks for the caller's memory too.
WantsCallMemory = bool
# Keep abc order for all non example types, if possible.
