#!/usr/bin/env node
// Entry point of Participant A (Node.js): reads the config, wires the parts together and runs it.
//
//   node src/index.js                      -> interactive setup (asks for name, data, address)
//   node src/index.js --name "Participant A" --data 8,10,12
//   node src/index.js --name "Participant A" --data-file data/participant-a.json

const { loadConfig, ConfigError, USAGE } = require("./config");
const { interviewInTerminal } = require("./interactive");
const { createLogger } = require("./logger");
const { CoordinatorClient } = require("./coordinatorClient");
const { LocalTrainer } = require("./trainer");
const { Participant } = require("./participant");

async function main() {
  let config;
  try {
    if (process.argv.length <= 2 && process.stdin.isTTY) {
      config = await interviewInTerminal(); // no options given -> ask the user
      if (!config) {
        console.log("Not registered. Bye!");
        return;
      }
    } else {
      config = loadConfig();
    }
  } catch (err) {
    if (err instanceof ConfigError) {
      console.error(`Error: ${err.message}\n\n${USAGE}`);
      process.exitCode = 2;
      return;
    }
    throw err;
  }
  if (config.help) {
    console.log(USAGE);
    return;
  }

  const logger = createLogger(config.name);
  const coordinator = new CoordinatorClient(config.address, { rpcTimeoutMs: config.rpcTimeoutMs });
  const participant = new Participant({
    name: config.name,
    trainer: new LocalTrainer(config.localData),
    coordinator,
    logger,
    host: config.host,
    port: config.port,
    maxRetryDelayMs: config.maxRetryDelayMs,
  });

  // Ctrl+C (SIGINT) or a kill (SIGTERM) -> finish cleanly instead of dying mid-request
  const shutdown = (signal) => {
    logger.info(`${signal} received - shutting down`);
    participant.stop();
  };
  process.once("SIGINT", shutdown);
  process.once("SIGTERM", shutdown);

  try {
    logger.info(`starting with ${config.localData.length} samples`);
    await participant.start();   // start the service + register
    await participant.stopped;   // then serve training tasks until Ctrl+C
  } catch (err) {
    logger.error(err.message);
    await participant.stop();
    process.exitCode = 1;
  } finally {
    coordinator.close();
  }
}

main().catch((err) => {
  console.error(`Fatal error: ${err.stack || err}`);
  process.exitCode = 1;
});
