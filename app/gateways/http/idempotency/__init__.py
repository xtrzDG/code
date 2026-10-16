"""
Idempotency-Key on creating requests (docs/api-versioning.md): a dependency
claims the key before a route runs, a middleware keeps the route's answer
(or releases the key) after, and a retry gets the kept answer back.
"""
