"""Keep abc order.

Example:
    is_quality_dropping: IsQualityDropping = False
"""

IsQualityDropping = bool

# The nightly quality sample of real conversations is judged by the
# assistant's own model provider, never by the other provider's judge.
IsQualityJudgeSameProvider = bool
# Keep abc order for all non example types, if possible.
