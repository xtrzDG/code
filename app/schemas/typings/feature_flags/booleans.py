"""Keep abc order."""

# A feature flag is switched on at all (its rollout and lists then decide
# which businesses get it); off, no business gets it.
IsFeatureFlagEnabled = bool
# A feature flag holds for one business at request time.
IsFeatureFlagOn = bool
