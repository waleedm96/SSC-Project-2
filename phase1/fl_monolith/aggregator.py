"""Aggregator: combines local results into one global weight (FedAvg)."""

from models import TrainingResult


class Aggregator:
    def aggregate(self, results: list[TrainingResult]) -> float:
        if not results:
            raise ValueError("No results to aggregate")

        total_samples = sum(r.num_samples for r in results)
        weighted_sum = sum(r.local_weight * r.num_samples for r in results)
        global_weight = weighted_sum / total_samples

        values = " + ".join(str(r.local_weight) for r in results)
        print(f"  [Aggregator] ({values}) / {len(results)} -> global weight = {global_weight}")
        return global_weight
