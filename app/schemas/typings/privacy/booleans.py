"""Keep abc order.

Example:
    is_suppressed: IsMessagingSuppressed = True
"""

# The customer asked for no messages they did not ask for (STOP), on their
# contact or on the business's suppression list.
IsMessagingSuppressed = bool

# The business lets the nightly judge score a sample of its real
# conversations (Settings -> Privacy).
IsQualitySamplingAllowed = bool

# Keep abc order for all non example types, if possible.
