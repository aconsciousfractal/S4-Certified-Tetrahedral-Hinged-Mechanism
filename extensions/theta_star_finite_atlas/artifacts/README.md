# Theta-star imported artifacts

Status: curated artifact subset for branch `theta-star-addendum-review`.

These files are copied from the local development workspace and are intended to
support external mathematical review of the theta-star finite-atlas extension.
They are not a full dump of exploratory logs.

Imported JSON artifacts:

```text
s4_theta_star_source_map_visibility_audit.json
s4_theta_star_t6b_theorem_prose_audit.json
s4_theta_star_108_tree_theorem_proof_package_gate.json
s4_theta_star_positive_jam_max_over_8_certificate.json
```

Imported support documents are under `../docs/`.

`../EXTENSION_MANIFEST.json` records package scope, expected counts, and hashes
for the curated review inputs.  `SHA256SUMS.txt` mirrors the file hashes.
`scripts/check_theta_star_extension.py` verifies those hashes and checks the
expected status/count fields.
