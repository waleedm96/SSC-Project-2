# Phase 1 – Monolithic Design

In this phase we design a federated learning application that runs as **one single Python program**.
In Phase 2 we split it into separate gRPC services.


## 1. What the application does

- Register participants
- Create and start a training job
- Send the training configuration to each participant
- Each participant trains on its own local data
- Collect the local results
- Aggregate them into one global result
- Show the job status and the final result

## 2. Components

| Component | What it does |
|-----------|--------------|
| CLI | Menu for the administrator. Passes commands to the coordinator. |
| Coordinator | Main controller. Starts jobs, sends tasks to participants, collects results. |
| ParticipantRegistry | Keeps the list of registered participants. |
| JobManager | Creates jobs and tracks their status. |
| Aggregator | Calculates the average of the local results. |
| Participant | Keeps its own data and trains on it. The data never leaves the participant. |

Everything runs in one process, using normal function calls.

## 3. Data classes

| Class | Fields | Used for |
|-------|--------|----------|
| `TrainingConfig` | num_rounds, initial_weight | settings of a job |
| `TrainingTask` | job_id, round, global_weight, config | sent from coordinator to participant |
| `TrainingResult` | job_id, participant_id, round, local_weight, num_samples | sent back from participant |
| `TrainingJob` | job_id, config, participant_ids, status, current_round, global_weight, results | state of one experiment |
| `JobStatus` (enum) | CREATED, RUNNING, COMPLETED, FAILED | job state |

These data classes will become Protobuf messages in Phase 2.

## 4. Example

Local training simply returns the average of the participant's data.

| Participant | Local data | Local result |
|-------------|-----------|--------------|
| A | [8, 10, 12] | 10 |
| B | [18, 20, 22] | 20 |
| C | [28, 30, 32] | 30 |

```
global result = (10 + 20 + 30) / 3 = 20
```
