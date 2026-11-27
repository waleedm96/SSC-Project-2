# Participant A (Node.js)

**Participant A** of the federated learning system. Each participant is written in a different language,
to show that gRPC connects them all:

| Participant | Language | Example data |
|-------------|----------|--------------|
| **A** | **Node.js (this folder)** | 8, 10, 12 |
| B | Python (`../python/participant.py`) | 18, 20, 22 |
| C | Java | 28, 30, 32 |

It talks to the Python Coordinator Service over gRPC,
using the shared contract in [`../proto/federated_learning.proto`](../proto/federated_learning.proto).

The participant keeps its data local. Only the result (`local_weight`, `num_samples`) is sent to the coordinator.

## Setup

Requires Node.js 18.11 or newer.

```
npm install
```

## Run

Start the coordinator first (`python coordinator_server.py` in `../python`).

**Interactive.** The participant asks for its name, local data and coordinator address, then registers itself.
Press Enter to accept the defaults (Participant A, data 8, 10, 12):

```
npm start
```

**Quick start** with no questions:

```
npm run quick
```

You can also pass your own settings:

```
node src/index.js --name "Participant A" --data 1,2,3,4
node src/index.js --name "Participant A" --data-file my-data.json --address 192.168.1.10:50051
node src/index.js --help
```

The coordinator address can also be set with the `COORDINATOR_ADDRESS` environment variable.
Press Ctrl+C to stop a participant cleanly.

## Test

```
npm test
```

The tests run against a fake coordinator written in Node.js, so Python is not needed.

## Structure

| File | Responsibility |
|------|----------------|
| `src/index.js` | Entry point: reads the config, connects the parts, handles Ctrl+C |
| `src/config.js` | Command-line options, data loading and validation |
| `src/interactive.js` | Interactive setup questions (used when no options are given) |
| `src/coordinatorClient.js` | gRPC client: loads the `.proto` file and calls `RegisterParticipant` (async, with a deadline) |
| `src/participant.js` | Runs the `ParticipantService` gRPC server, registers its address and answers `SendTrainingTask` |
| `src/trainer.js` | Local training (mean of the local data), the same as Phase 1 |
| `src/logger.js` | Log lines with the time and participant name |
| `data/participant-a.json` | Participant A's example local data |
| `test/*.test.js` | Unit and gRPC tests (`node:test`) |

## How it works (push model)

1. The participant starts its own gRPC server (`ParticipantService`) on `--host`/`--port`. By default it uses any free port on 127.0.0.1.
2. It registers that address and its name with the coordinator (`RegisterParticipant`).
3. It waits. For every round of a job, the coordinator calls `SendTrainingTask`. The participant trains on its local data and returns `local_weight` and `num_samples`.

## Behaviour

- **Coordinator down:** registration keeps retrying with exponential backoff (1s, 2s, 4s … up to 10s).
- **Registration refused** (for example an empty name): the participant stops with an error instead of retrying forever.
- **Invalid task** (no job id): the participant answers `INVALID_ARGUMENT`.
- **Ctrl+C:** the participant shuts its service down cleanly.
