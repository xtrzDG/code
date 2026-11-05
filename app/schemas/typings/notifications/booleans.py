"""Keep abc order.

Example:
    is_urgent: IsUrgentStaffAlert = True
"""

IsDeliverySimulated = bool
# The latest send to a staff contact or device failed (retried or given up).
IsLastDeliveryFailed = bool
IsProviderReady = bool
IsStaffLinkExpired = bool
IsUrgentStaffAlert = bool
# Keep abc order for all non example types, if possible.
