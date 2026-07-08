## Summary

Draft PR for watcher-hk KERI v2/default compatibility test repairs.

This PR restores six watcher tests that were failing or semantically invalid after current KeriPy v2-default behavior (`keripy==2.0.0-dev6`, origin/main at `8a7bea0f`):

| Test | Issue | Fix |
|---|---|---|
| `test_http_query_parser_uses_inbound_keri10_version` | v2-default query mislabeled as v1 | Explicit `eventing.query(pvrsn=Vrsn_1_0, kind=Kinds.json)` |
| `test_http_post_maps_event_parser_errors_to_bad_request` | Invalid v2-default reply fixture | Valid v2 JSON reply via `eventing.reply(pre=..., pvrsn=Vrsn_2_0, kind=Kinds.json)` |
| `test_http_put_maps_parser_errors_to_bad_request` | Same invalid v2 reply fixture | Same valid v2 JSON reply pattern |
| `test_query_replies_are_normalized_to_fixed_v2_cesr` | v2-default reply used for v1 input | Explicit v2 CESR reply for the normalization path |
| `test_adding_watched` | v1 AID expectations under v2-default | Updated AIDs to v2 derivations; added required `pre=` to reply |
| `test_watcher_parser_accepts_keri10_inception_and_add_reply` | v2-default messages forced through v1 parser | Explicit v1 JSON Habs and reply; parser-level acceptance |

## What changed

- Replaced invalid/default-v2 fixtures with explicit v1 or v2 KeriPy constructors.
- Added pre-parse/pre-call version assertions where useful.
- Kept KERI 1.0 parser interoperability scoped to parser acceptance where route-handler side effects are not registered.

## Files changed

- `tests/watopnet/core/test_keri_v2_compat.py`
- `tests/watopnet/core/test_watching.py`

## Validation

```
test_keri_v2_compat.py: 25 passed
test_watching.py:       14 passed, 1 known unresolved failure
Ruff:                   all checks passed
```

## Known unresolved item

This PR intentionally excludes:

`tests/watopnet/core/test_watching.py::test_query_witness_state_parses_real_keri10_ksn_reply`

The investigation found that a KERI 1.0 KSN reply can be accepted without raising, but `knas`/`ksns` storage could not be restored with test-only fixture changes. The keripy v2-default parser dispatches v1 reply counter-signatures as `receipt` events to the Kevery rather than routing them to the Revery KSN handler.

Maintainer guidance is needed on whether KERI 1.0 KSN-storage interop is still required, should be handled upstream in KeriPy, or should be formally dropped.
