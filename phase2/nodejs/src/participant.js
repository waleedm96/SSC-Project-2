// The participant (push model):
//   1. start its own gRPC server (ParticipantService) on host:port
//   2. register that address with the coordinator (retry with backoff while it is down)
//   3. wait - the coordinator calls SendTrainingTask for every round
// The local data never leaves this program; only the result is returned.

const grpc = require("@grpc/grpc-js");
const { loadProto } = require("./coordinatorClient");

// errors that mean "the coordinator cannot be reached right now" -> wait and try again
const CONNECTION_ERRORS = new Set([grpc.status.UNAVAILABLE, grpc.status.DEADLINE_EXCEEDED]);

class Participant {
  /**
   * @param {object} options
   * @param {string} options.name             e.g. "Participant A"
   * @param {object} options.trainer          LocalTrainer (train / numSamples)
   * @param {object} options.coordinator      CoordinatorClient (register / address)
   * @param {object} options.logger           { info, warn, error }
   * @param {string} [options.host]           host the coordinator uses to reach us
   * @param {number} [options.port]           port of our service (0 = any free port)
   * @param {number} [options.retryDelayMs]   first wait after a failed registration
   * @param {number} [options.maxRetryDelayMs] longest wait between registration attempts
   */
  constructor({ name, trainer, coordinator, logger, host = "127.0.0.1", port = 0,
                retryDelayMs = 1000, maxRetryDelayMs = 10000, proto = loadProto() }) {
    this.name = name;
    this._trainer = trainer;
    this._coordinator = coordinator;
    this._log = logger;
    this._host = host;
    this._port = port;
    this._retryDelayMs = retryDelayMs;
    this._maxRetryDelayMs = maxRetryDelayMs;
    this._proto = proto;

    this.address = null;
    this.registered = false;
    this.roundsTrained = 0;
    this._server = null;
    this._stopping = false;
    this._timer = null;
    this._wake = null;
    this.stopped = new Promise((resolve) => { this._resolveStopped = resolve; });
  }

  /** Starts the service and registers. Resolves true once registered (false if stopped before). */
  async start() {
    await this.startServer();
    return this.register();
  }

  /** Starts the ParticipantService; returns our address (host:port). */
  async startServer() {
    this._server = new grpc.Server();
    this._server.addService(this._proto.ParticipantService.service, {
      SendTrainingTask: (call, callback) => this._onTrainingTask(call.request, callback),
    });
    const port = await new Promise((resolve, reject) =>
      this._server.bindAsync(`${this._host}:${this._port}`, grpc.ServerCredentials.createInsecure(),
        (err, boundPort) => (err ? reject(new Error(`Cannot listen on ${this._host}:${this._port}: ${err.message}`))
                                 : resolve(boundPort))));
    this.address = `${this._host}:${port}`;
    this._log.info(`ParticipantService listening on ${this.address}`);
    return this.address;
  }

  /** Registers with the coordinator, retrying with exponential backoff while it is not reachable. */
  async register() {
    let delay = this._retryDelayMs;
    while (!this._stopping) {
      try {
        await this._coordinator.register(this.name, this.address);
        this.registered = true;
        this._log.info(`registered with the coordinator at ${this._coordinator.address} - waiting for training tasks`);
        return true;
      } catch (err) {
        if (!CONNECTION_ERRORS.has(err.code)) {
          throw new Error(`Coordinator refused the registration: ${err.details || err.message}`);
        }
        this._log.warn(`coordinator at ${this._coordinator.address} not reachable - retrying in ${delay} ms`);
        await this._sleep(delay);
        delay = Math.min(delay * 2, this._maxRetryDelayMs);
      }
    }
    return false;
  }

  // Called by the coordinator (SendTrainingTask) for every round.
  _onTrainingTask(request, callback) {
    const task = request.task;
    if (!task || !task.job_id || task.round < 1) {
      return callback({ code: grpc.status.INVALID_ARGUMENT, details: "Task must have a job_id and a round >= 1" });
    }
    this._log.info(`received ${task.job_id} round ${task.round} (global weight = ${task.global_weight})`);
    const { localWeight, numSamples } = this._trainer.train(task);
    this.roundsTrained += 1;
    this._log.info(`trained on ${numSamples} samples -> local weight = ${localWeight}`);

    // only the result leaves the participant, never the data
    return callback(null, {
      job_id: task.job_id,
      participant_id: this.address,
      round: task.round,
      local_weight: localWeight,
      num_samples: numSamples,
    });
  }

  /** Stops registering and shuts the service down. */
  async stop() {
    if (this._stopping) return this.stopped;
    this._stopping = true;
    clearTimeout(this._timer);
    if (this._wake) this._wake();
    if (this._server) {
      await new Promise((resolve) => this._server.tryShutdown(() => resolve()));
      this._server = null;
    }
    this._log.info(`stopped after ${this.roundsTrained} round(s)`);
    this._resolveStopped();
    return this.stopped;
  }

  _sleep(ms) {
    return new Promise((resolve) => {
      this._wake = resolve;
      this._timer = setTimeout(resolve, ms);
    });
  }
}

module.exports = { Participant };
