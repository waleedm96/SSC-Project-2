// Local training. The data is kept inside this object and never sent anywhere.

class LocalTrainer {
  constructor(localData) {
    if (!Array.isArray(localData) || localData.length === 0) {
      throw new Error("LocalTrainer needs a non-empty list of numbers");
    }
    this._data = [...localData];
  }

  get numSamples() {
    return this._data.length;
  }

  /**
   * Simulated training (same as Phase 1): the local model is the mean of the local data.
   * The task (job, round, global weight) is received so a real model could start from global_weight.
   */
  train(_task) {
    const sum = this._data.reduce((a, b) => a + b, 0);
    return { localWeight: sum / this._data.length, numSamples: this._data.length };
  }
}

module.exports = { LocalTrainer };
