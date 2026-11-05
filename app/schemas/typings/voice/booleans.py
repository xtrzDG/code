"""Keep abc order.

Example:
    are_enabled: AreVoiceChecksEnabled = True
"""

# The autotests of a version with voice include simulated calls
# (VOICE_CHECKS_ENABLED; on unless turned off).
AreVoiceChecksEnabled = bool
# Keep abc order for all non example types, if possible.
