// Interactive setup: asks the user for the participant's name, local data and coordinator address,
// then returns the same config object as the command-line options would.

const readline = require("node:readline/promises");
const { loadConfig, parseDataList, readDataFile, ConfigError, DEFAULTS } = require("./config");

/** Asks the same question until validate() accepts the answer. */
async function askUntilValid(ask, out, question, validate) {
  for (;;) {
    const answer = (await ask(question)).trim();
    try {
      return validate(answer);
    } catch (err) {
      if (!(err instanceof ConfigError)) throw err;
      out(`  ${err.message} - please try again.`);
    }
  }
}

/**
 * Runs the setup interview.
 * @param {object}   io
 * @param {Function} io.ask   (question) => Promise<string answer>
 * @param {Function} io.out   (line) => void
 * @param {object}   [io.env] environment variables (for the default address)
 * @param {string}   [io.cwd] folder that data file paths are relative to
 * @returns {Promise<object|null>} the config, or null if the user cancelled
 */
async function interview({ ask, out, env = process.env, cwd = process.cwd() }) {
  const defaultAddress = env.COORDINATOR_ADDRESS || DEFAULTS.address;

  out("");
  out("===== Federated Learning - Participant setup (Node.js) =====");
  out("Your data stays on this machine. Only the training result is sent to the coordinator.");
  out("Press Enter to accept the value in [brackets].");
  out("");

  const name = await askUntilValid(ask, out, `Participant name [${DEFAULTS.name}]: `,
    (answer) => answer || DEFAULTS.name);

  const dataArgs = await askUntilValid(ask, out,
    `Local data - numbers separated by commas (e.g. 8,10,12) or a .json file [${DEFAULTS.dataFile}]: `,
    (input) => {
      const answer = input || DEFAULTS.dataFile;
      if (answer.toLowerCase().endsWith(".json")) {
        readDataFile(answer, cwd); // validate now, so a mistake is caught here
        return ["--data-file", answer];
      }
      parseDataList(answer);
      return ["--data", answer];
    });

  const address = await askUntilValid(ask, out, `Coordinator address [${defaultAddress}]: `, (answer) => {
    const value = answer || defaultAddress;
    if (!/^[^\s:]+:\d+$/.test(value)) throw new ConfigError(`"${value}" is not a host:port address`);
    return value;
  });

  const config = loadConfig(["--name", name, ...dataArgs, "--address", address], env, cwd);

  out("");
  out("Summary:");
  out(`  Name:        ${config.name}`);
  out(`  Local data:  ${config.localData.join(", ")}  (${config.localData.length} samples)`);
  out(`  Coordinator: ${config.address}`);
  const confirm = (await ask("Register with the coordinator now? [Y/n]: ")).trim().toLowerCase();
  if (confirm === "n" || confirm === "no") return null;
  out("");
  return config;
}

/** Runs the interview on the terminal (stdin/stdout). */
async function interviewInTerminal() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  rl.on("SIGINT", () => {
    rl.close();
    console.log("\nSetup cancelled");
    process.exit(130);
  });
  try {
    return await interview({ ask: (q) => rl.question(q), out: (line) => console.log(line) });
  } finally {
    rl.close();
  }
}

module.exports = { interview, interviewInTerminal };
