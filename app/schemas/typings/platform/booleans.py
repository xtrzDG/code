"""Keep abc order.

Example:
    is_llm_content_traced: IsLlmContentTraced = False
"""

IsDemoDataSeedingEnabled = bool
IsEmbeddedWorkerEnabled = bool
IsFinalJobAttempt = bool
IsLlmContentTraced = bool
# LANGFUSE_RAW_TEXT: traced texts keep phone numbers and e-mail addresses
# (by default they are replaced with placeholders before they leave).
IsLlmRawTextTraced = bool
IsProcessLocalJob = bool
# Keep abc order for all non example types, if possible.
