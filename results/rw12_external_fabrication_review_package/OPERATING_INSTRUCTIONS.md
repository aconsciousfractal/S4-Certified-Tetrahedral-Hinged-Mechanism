# RW12 operating instructions

## What to fabricate first

Fabricate the four body pieces in `fabrication_files/body_pieces`.

Preferred pin strategy:

1. Prefer commercial/metal dowel pins near `2.5` mm if the fabricator can source and fit-check them.
2. If printing pins, start with `v02_loose_fdm_2p40` or `v03_nominal_rw10_2p50`.
3. Use `v04_tight_2p60` only after measuring printed hole diameters.

Nominal hole diameter encoded by the digital model: `3.1` mm.
Nominal RW10 pin diameter: `2.5` mm.

## Do not do this

- Do not print any internal assembly preview as one object.
- Do not treat generic PrusaSlicer G-code from earlier gates as machine-ready.
- Do not claim hingeability before physical insertion/rotation measurements exist.

## Required post-fabrication measurements

For each hinge axis:

- measured hole diameter on each knuckle/boss;
- measured pin diameter;
- insertion pass/fail;
- free rotation pass/fail;
- visible binding or cracking;
- support cleanup impact.
