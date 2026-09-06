# Experiment Command and Per-Second Packet Counters

## Summary

`network_traffic_generator.py` adds an `exp` command for sequential flow batches and replaces experiment-wide packet-counter snapshots with one-second counter deltas. The traffic generation, distribution command, CPU recording, communicator behavior, and output directory structure remain unchanged.

## Experiment command

Run an experiment batch with:

```text
exp --config ./flow_setting/exp.json
```

The experiment file must be a JSON object containing a non-empty `flow_setting` array of JSON paths and a positive integer `exp_times`:

```json
{
  "flow_setting": [
    "./flow_setting/test.json",
    "./flow_setting/test2.json"
  ],
  "exp_times": 5
}
```

Paths are interpreted relative to the process working directory. Each array entry is passed to `_handle_flow_command` with `--num exp_times`. Therefore, the example runs `test.json` five times and, after all runs and existing cleanup delays finish, runs `test2.json` five times. Invalid experiment data or a failed flow configuration stops the remaining sequence.

## Packet-counter recording

- Configured NDTwin, SmartNIC, and P4 counters are sampled in a background thread.
- The first sample is the baseline. Later samples run on one-second monotonic deadlines until `ending_process` completes.
- Every HTTP request or P4 helper process has a 10 ms (`0.01` second) timeout and is not retried.
- Each CSV row is the difference from the last successful cumulative snapshot. Existing filenames, directories, and counter columns are preserved, and row order represents elapsed seconds.
- A timeout, malformed response, or other sampling failure writes `-1` to every counter field for that source and does not stop traffic generation.
- A failed sample does not replace the last successful baseline, so the next successful delta covers the entire interval since the last good sample.
- No counter file is created for an unconfigured source or when no completed one-second sample exists.

## Verification

- Validate `exp.json` schema, execution order, repetition count, and stop-on-failure behavior.
- Mock cumulative counter values to verify per-second differences, timeout rows, and recovery from the last successful snapshot.
- Confirm counter collection does not block the asyncio traffic loop and stops after active flows finish.
- Run Python syntax compilation and regression checks for `flow`, `dist`, `exp`, and `exit` command dispatch.
