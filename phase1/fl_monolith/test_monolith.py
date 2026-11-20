"""Automatic tests of the monolithic FL application.

Run from this folder:  python -m unittest -v
"""

import unittest

from models import TrainingConfig, TrainingTask, TrainingResult, JobStatus
from participant import Participant
from aggregator import Aggregator
from coordinator import Coordinator


class TestParticipant(unittest.TestCase):
    def test_local_training_returns_mean_of_data(self):
        participant = Participant("p1", "Participant A", [8, 10, 12])
        task = TrainingTask(job_id="job-1", round=1, global_weight=0.0, config=TrainingConfig())

        result = participant.train(task)

        self.assertEqual(result.local_weight, 10)
        self.assertEqual(result.num_samples, 3)
        self.assertEqual(result.participant_id, "p1")


class TestAggregator(unittest.TestCase):
    def test_equal_samples_gives_simple_average(self):
        results = [
            TrainingResult("job-1", "p1", 1, 10, 3),
            TrainingResult("job-1", "p2", 1, 20, 3),
            TrainingResult("job-1", "p3", 1, 30, 3),
        ]
        self.assertEqual(Aggregator().aggregate(results), 20)

    def test_more_samples_count_more(self):
        results = [
            TrainingResult("job-1", "p1", 1, 10, 3),
            TrainingResult("job-1", "p2", 1, 20, 3),
            TrainingResult("job-1", "p3", 1, 30, 6),
        ]
        self.assertEqual(Aggregator().aggregate(results), 22.5)

    def test_no_results_is_an_error(self):
        with self.assertRaises(ValueError):
            Aggregator().aggregate([])


class TestCoordinator(unittest.TestCase):
    def setUp(self):
        # runs before every test: a fresh coordinator with the example participants
        self.coordinator = Coordinator()
        self.coordinator.register_participant("Participant A", [8, 10, 12])
        self.coordinator.register_participant("Participant B", [18, 20, 22])
        self.coordinator.register_participant("Participant C", [28, 30, 32])

    def test_assignment_example_gives_20(self):
        job_id = self.coordinator.create_job(TrainingConfig(num_rounds=1))
        self.coordinator.start_job(job_id)

        job = self.coordinator.get_status(job_id)
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.global_weight, 20)
        self.assertEqual(len(job.results), 3)

    def test_new_job_is_created(self):
        job_id = self.coordinator.create_job(TrainingConfig())
        self.assertEqual(self.coordinator.get_status(job_id).status, JobStatus.CREATED)

    def test_job_cannot_start_twice(self):
        job_id = self.coordinator.create_job(TrainingConfig())
        self.coordinator.start_job(job_id)
        with self.assertRaises(ValueError):
            self.coordinator.start_job(job_id)

    def test_job_needs_participants(self):
        with self.assertRaises(ValueError):
            Coordinator().create_job(TrainingConfig())

    def test_unknown_job_is_an_error(self):
        with self.assertRaises(KeyError):
            self.coordinator.get_status("job-99")


if __name__ == "__main__":
    unittest.main()
