# Prepared attack integration — not applied

These reviewable patches were prepared by the interrupted worker. They are
not applied to SOURCE in this checkpoint and have not been verified by their
new tests. Preserve the selected Game0000 turn10 attack and run the RED tests
first, then apply the production patch and verify the real event. Recheck patch
applicability against the current branch before applying.

The patch connects attack declaration to the already registered suspension
handlers and validates active fields rather than a specific stack tuple. Any
actual later BT11 Ulforce bounce remains an explicit missing interaction.
