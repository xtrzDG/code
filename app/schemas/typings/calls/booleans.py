"""Keep abc order.

Example:
    is_enabled: IsCallSummaryEnabled = True
"""

# The call's summary reached the caller's customer memory.
IsCallRemembered = bool
IsCallSummaryEnabled = bool
IsCallSummaryGenerated = bool
IsNewMissedCall = bool
IsSmsFallbackEnabled = bool
IsTextBackEnabled = bool
# A call's summary request asks for the caller's memory too.
WantsCallMemory = bool
# Keep abc order for all non example types, if possible.
