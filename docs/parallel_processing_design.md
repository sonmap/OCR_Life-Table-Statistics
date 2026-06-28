# Parallel Processing Design

This document explains how to improve the premium calculation workflow.

The current inefficient pattern is usually:

```text
input row
  -> reference lookup
  -> first transformation
  -> second transformation
  -> third transformation
  -> premium calculation
  -> result comparison or write
```

This is similar to an inline Excel-to-Java implementation. It is easy to verify but expensive when the same reference data and the same intermediate values are recalculated many times.

## Target architecture

```text
Job start
  -> bulk load reference data once
  -> build local memory cache
  -> precompute D/N/M commutation values
  -> group duplicate premium calculation keys
  -> split unique keys into chunks
  -> calculate chunks in parallel
  -> map unique results back to original rows
  -> write result file
  -> DB batch insert in a separate output step
```

## Important principle

Do not call DB, Redis, or a remote cache inside the row calculation loop.

Good:

```text
DB or Redis bulk load once
  -> local memory cache
  -> row calculation uses memory only
```

Bad:

```text
for each of 2,000,000 rows:
    read risk rate from DB or Redis
    recalculate D/N/M
    save one result row
```

## Parallelization model

The recommended first model is chunk-level parallelism.

```text
Worker 1 = chunk 1 full calculation
Worker 2 = chunk 2 full calculation
Worker 3 = chunk 3 full calculation
```

This is better than splitting servers by calculation stage at the beginning.

Stage-level separation is possible later, but it creates more network and intermediate data movement.

## What was added to the sample project

`backend/app/batch/run_premium_batch.py` now supports three modes:

```text
inline   : original row-by-row calculation
 grouped : calculate duplicate premium keys once and map back
parallel : grouped calculation with process parallelism
```

Example local commands:

```bash
cd backend
python -m app.batch.run_premium_batch \
  --life-table app/sample_data/life_table.csv \
  --policies app/sample_data/policies.csv \
  --output ../outputs/result_inline.csv \
  --mode inline

python -m app.batch.run_premium_batch \
  --life-table app/sample_data/life_table.csv \
  --policies app/sample_data/policies.csv \
  --output ../outputs/result_grouped.csv \
  --mode grouped

python -m app.batch.run_premium_batch \
  --life-table app/sample_data/life_table.csv \
  --policies app/sample_data/policies.csv \
  --output ../outputs/result_parallel.csv \
  --mode parallel \
  --chunk-size 50000 \
  --workers 12
```

## Redis usage

Redis is useful for:

```text
job status
progress
chunk queue
distributed lock
retry state
```

Redis is not recommended for:

```text
row-by-row risk rate lookup
row-by-row D/N/M lookup
large result storage
```

## Multi-server design

```text
AP or Job Manager
  -> create job
  -> create chunk metadata
  -> push chunk ids to Redis queue

Worker server
  -> pop chunk id
  -> load local reference cache
  -> calculate full chunk
  -> write chunk result file
  -> update chunk status

Output loader
  -> merge chunk files
  -> perform DB batch insert
```

Recommended storage:

```text
input chunks  : shared storage, NAS, NFS, MinIO, S3 compatible storage
output chunks : shared storage
job metadata  : DB
queue/status  : Redis
final result  : DB batch insert
```

## Tuning start values

For a 16-core server:

```text
workers    : 10 to 12
chunk size : 50,000 to 100,000
DB batch   : 5,000 to 20,000 rows
```

Leave some cores for OS, DB writer, Tomcat or FastAPI, and monitoring.

## Validation

Compare these modes with the same input file:

```text
inline vs grouped
inline vs parallel
Excel result vs parallel result
Java result vs parallel result
```

The first goal is not only speed. The first goal is to prove that the grouped and parallel calculation results are identical to the original inline calculation within the allowed rounding tolerance.
