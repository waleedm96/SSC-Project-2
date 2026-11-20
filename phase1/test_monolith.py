"""
Step 7 - Automatic tests.  Run with:  python -m unittest -v
"""

import contextlib
import io
import unittest

from aggregator import Aggregator
from coordinator import Coordinator
from job_manager import JobManager
from models import JobStatus, TrainingConfig, TrainingResult, TrainingTask
from participant import Participant
from registry import ParticipantRegistry


def quiet():
    """Hide the [Coordinator]/[A]/... logs so the test output stays clean."""
    return contextlib.redirect_stdout(io.StringIO())


class TestParticipant(unittest.TestCase):
    def setUp(self):
        self.a = Participant("p1", "A", [8, 10, 12])
        self.task = TrainingTask("job-1", 1, 0.0)

    def test_train_returns_mean(self):
        with quiet():
            result = self.a.train(self.task)
        self.assertEqual(result.weight, 10.0)
        self.assertEqual(result.num_samples, 3)

    def test_result_contains_no_raw_data(self):
        with quiet():
            result = self.a.train(self.task)
        self.assertFalse(hasattr(result, "data"))
        self.assertNotIn([8, 10, 12], vars(result).values())


class TestAggregator(unittest.TestCase):
    def setUp(self):
        self.aggregator = Aggregator()

    def test_example_10_20_30_gives_20(self):
        results = [TrainingResult(f"p{i}", "job-1", 1, w, 3)
                   for i, w in enumerate([10.0, 20.0, 30.0], start=1)]
        with quiet():
            self.assertEqual(self.aggregator.aggregate(results), 20.0)

    def test_weighted_average_unequal_samples(self):
        results = [TrainingResult("p1", "job-1", 1, 10.0, 1),
                   TrainingResult("p2", "job-1", 1, 30.0, 3)]
        with quiet():
            self.assertEqual(self.aggregator.aggregate(results), 25.0)

    def test_empty_results_rejected(self):
        with self.assertRaises(ValueError):
            self.aggregator.aggregate([])


class TestStorage(unittest.TestCase):
    def test_duplicate_participant_rejected(self):
        registry = ParticipantRegistry()
        registry.add(Participant("p1", "A", [1]))
        with self.assertRaises(ValueError):
            registry.add(Participant("p1", "B", [2]))

    def test_unknown_ids_raise_keyerror(self):
        with self.assertRaises(KeyError):
            ParticipantRegistry().get("p9")
        with self.assertRaises(KeyError):
            JobManager().get("job-9")


class TestCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = Coordinator()
        with quiet():
            for name, data in [("A", [8, 10, 12]), ("B", [18, 20, 22]), ("C", [28, 30, 32])]:
                self.coordinator.register_participant(name, data)
            self.job_id = self.coordinator.create_job(TrainingConfig(num_rounds=1))

    def test_status_created_then_completed(self):
        self.assertEqual(self.coordinator.get_status(self.job_id)["status"],
                         JobStatus.CREATED.value)
        with quiet():
            self.coordinator.start_job(self.job_id)
        self.assertEqual(self.coordinator.get_status(self.job_id)["status"],
                         JobStatus.COMPLETED.value)

    def test_full_example_gives_global_20(self):
        with quiet():
            global_weight = self.coordinator.start_job(self.job_id)
        self.assertEqual(global_weight, 20.0)
        status = self.coordinator.get_status(self.job_id)
        self.assertEqual(status["local_results"], {"p1": 10.0, "p2": 20.0, "p3": 30.0})


if __name__ == "__main__":
    unittest.main()
