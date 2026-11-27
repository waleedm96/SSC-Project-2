// Reads the participant's settings from the command line (and environment variables).

const fs = require("node:fs");
const path = require("node:path");
const { parseArgs } = require("node:util");

const DEFAULTS = Object.freeze({
  name: "Participant A",                  // this Node.js program is Participant A
  dataFile: "data/participant-a.json",
  address: "127.0.0.1:50051",             // the coordinator
  host: "127.0.0.1",                      // where the coordinator can reach this participant
  port: 0,                                // 0 = any free port
  rpcTimeoutMs: 5000,
  maxRetryDelayMs: 10000,
});

const USAGE = `Usage:
  node src/index.js                      (no options: interactive setup)
  node src/index.js --name <name> (--data <n,n,...> | --data-file <file.json>) [options]

Options:
  -n, --name <name>          participant name, e.g. "Participant A"   (required)
  -d, --data <list>          local data as comma-separated numbers, e.g. 8,10,12
  -f, --data-file <file>     local data as a JSON array file, e.g. data/participant-a.json
  -a, --address <host:port>  coordinator address (default ${DEFAULTS.address}, env COORDINATOR_ADDRESS)
      --host <host>          host the coordinator uses to reach this participant (default ${DEFAULTS.host})
  -p, --port <port>          port of this participant's service (default 0 = any free port)
  -h, --help                 show this help`;

class ConfigError extends Error {}

function validateData(values, source) {
  if (!Array.isArray(values) || values.length === 0) {
    throw new ConfigError(`Local data from ${source} must be a non-empty list of numbers`);
  }
  const numbers = values.map(Number);
  const bad = values.find((v, i) => typeof v === "boolean" || v === "" || v === null || !Number.isFinite(numbers[i]));
  if (bad !== undefined) {
    throw new ConfigError(`Local data from ${source} contains a value that is not a number: ${JSON.stringify(bad)}`);
  }
  return numbers;
}

function parseDataList(text) {
  return validateData(text.split(",").map((s) => s.trim()), "--data");
}

function readDataFile(file, cwd) {
  const fullPath = path.resolve(cwd, file);
  let content;
  try {
    content = fs.readFileSync(fullPath, "utf8");
  } catch (err) {
    throw new ConfigError(`Cannot read data file ${fullPath}: ${err.message}`);
  }
  let parsed;
  try {
    parsed = JSON.parse(content);
  } catch (err) {
    throw new ConfigError(`Data file ${fullPath} is not valid JSON: ${err.message}`);
  }
  return validateData(parsed, fullPath);
}

function parsePort(text) {
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0 || value > 65535) {
    throw new ConfigError(`--port must be a whole number between 0 and 65535, got "${text}"`);
  }
  return value;
}

function loadConfig(argv = process.argv.slice(2), env = process.env, cwd = process.cwd()) {
  let values;
  try {
    ({ values } = parseArgs({
      args: argv,
      options: {
        name: { type: "string", short: "n" },
        data: { type: "string", short: "d" },
        "data-file": { type: "string", short: "f" },
        address: { type: "string", short: "a" },
        host: { type: "string" },
        port: { type: "string", short: "p" },
        help: { type: "boolean", short: "h" },
      },
      strict: true,
    }));
  } catch (err) {
    throw new ConfigError(err.message);
  }

  if (values.help) return { help: true };

  const name = (values.name || "").trim();
  if (!name) throw new ConfigError("--name is required");

  if (values.data && values["data-file"]) {
    throw new ConfigError("Use either --data or --data-file, not both");
  }
  let localData;
  if (values.data) localData = parseDataList(values.data);
  else if (values["data-file"]) localData = readDataFile(values["data-file"], cwd);
  else throw new ConfigError("Local data is required (--data or --data-file)");

  return Object.freeze({
    help: false,
    name,
    localData: Object.freeze(localData),
    address: values.address || env.COORDINATOR_ADDRESS || DEFAULTS.address,
    host: values.host || DEFAULTS.host,
    port: values.port !== undefined ? parsePort(values.port) : DEFAULTS.port,
    rpcTimeoutMs: DEFAULTS.rpcTimeoutMs,
    maxRetryDelayMs: DEFAULTS.maxRetryDelayMs,
  });
}

module.exports = { loadConfig, parseDataList, readDataFile, ConfigError, USAGE, DEFAULTS };
