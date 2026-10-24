"""Keep abc order."""

# The legal texts were reviewed by a lawyer and filled in (LEGAL_TEXTS_FINAL).
AreLegalTextsFinal = bool
# The text is a draft that is not yet in force as written (a template, or
# LEGAL_TEXTS_FINAL is off): the public page says so.
IsLegalTextDraft = bool
# The visitor's demo conversation made a booking (sandbox: nothing is real).
IsDemoBookingMade = bool
# The demo assistant passed the conversation to a person (sandbox).
IsDemoHandoffMade = bool
# The demo assistant took down a request (sandbox).
IsDemoRequestMade = bool
# Keep abc order for all non example types, if possible.
