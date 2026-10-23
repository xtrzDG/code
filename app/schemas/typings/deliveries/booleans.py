"""Keep abc order.

Example:
    is_payload_discarded: IsInboundPayloadDiscarded = False
"""

# The processed event's payload is cleared, not kept until the inbox purge.
IsInboundPayloadDiscarded = bool
