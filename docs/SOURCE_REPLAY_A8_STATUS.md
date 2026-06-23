# Source Replay A8 Status

Status: `passed_current_workspace_full_source_replay`; not a fresh-clone replay.

Date: 2026-06-23.

Command run from the S4 source root:

```powershell
python scripts/replay_s4_cl5_a8_package_gate.py --full
```

Observed result:

```text
A6 records emitted: 7
one-parameter symbolic B05 closed: 7/7
A7a records emitted: 2
shared-face residual formula positive: 2/2
A7b tree records emitted: 2
one-parameter pair records: 12
B03 route-clean pairs: 0
B03 Sturm obligations: 0
A7c selected-hinge records emitted: 6
A7c contact-side certificates: 6/6
A7d tree wrapper records emitted: 2
A7d wrappers closed: 2/2
A8 experiment ledger rows: 5
A8 claim ledger rows: 7
A8 red-team tests: 15
A8 red-team hard failures: 0
package scaffold ready: True
smoke_status=PASS
```

Scope and caveat:

- This closes the current-workspace full A8 source replay gate.
- It does not convert this package into a standalone source-replay bundle; the package remains a frozen snapshot with package-local replay.
- A fresh-clone replay from a public repository can still be required as final release hardening after the target public repository is created.
- This does not promote any physical hingeability, printed-prototype, or global 3-parameter claim.
