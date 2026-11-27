// Small logger: every line starts with the time and the participant name.

function timestamp() {
  return new Date().toTimeString().slice(0, 8);
}

function createLogger(name, { out = console.log, err = console.error } = {}) {
  const line = (level, message) => `[${timestamp()}] [${name}] ${level === "INFO" ? "" : level + ": "}${message}`;
  return {
    info: (message) => out(line("INFO", message)),
    warn: (message) => err(line("WARN", message)),
    error: (message) => err(line("ERROR", message)),
  };
}

module.exports = { createLogger };
