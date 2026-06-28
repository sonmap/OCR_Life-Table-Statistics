# Parallel Processing Design

This document explains how to improve the premium calculation workflow.

The target flow is:

1. Read reference data once.
2. Build local memory cache.
3. Precompute commutation values.
4. Group duplicate premium calculation keys.
5. Split input into chunks.
6. Calculate chunks on worker nodes.
7. Save chunk results.
8. Load final results to DB in batch.

Redis should be used for job status and queue management, not for row-by-row calculation lookup.
