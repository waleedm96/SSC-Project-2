"""
Step 3 - Aggregator (FedAvg).

Combines the participants' local results into one global weight using a
weighted average: participants with more samples count more.

    global = sum(weight_i * num_samples_i) / sum(num_samples_i)
"""

from models import TrainingResult


class Aggregator:
    def aggregate(self, results: list[TrainingResult]) -> float:
        # 3.1 - Guard: nothing to aggregate
        if not results:
            raise ValueError("Cannot aggregate an empty list of results")

        # 3.2 - Total number of samples across all participants
        total_samples = sum(r.num_samples for r in results)
        if total_samples == 0:
            raise ValueError("Total number of samples is 0")

        # 3.3 - Weighted sum: each weight counts as many times as its samples
        weighted_sum = sum(r.weight * r.num_samples for r in results)

        # 3.4 - FedAvg result
        global_weight = weighted_sum / total_samples

        weights = " + ".join(str(r.weight) for r in results)
        print(f"[Aggregator] FedAvg of ({weights}) -> global weight = {global_weight}")
        return global_weight
