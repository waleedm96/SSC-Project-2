"""Tests of the Coordinator Service through real gRPC calls.

A test server is started on another port, and the tests play the role of the
management client and of two participants.

Run:  python -m unittest test_coordinator -v
"""

import unittest

import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc
from coordinator_server import create_server

TEST_ADDRESS = "127.0.0.1:50061"


def fake_train(stub, participant_id, local_data):
    """What a participant does: ask for a task, train locally, submit the result."""
    reply = stub.GetTrainingTask(pb.TrainingTaskRequest(participant_id=participant_id))
    if not reply.has_task:
        return None
    local_weight = sum(local_data) / len(local_data)          # local training (the data stays here)
    result = pb.TrainingResult(job_id=reply.task.job_id, participant_id=participant_id,
                               round=reply.task.round, local_weight=local_weight,
                               num_samples=len(local_data))
    return stub.SubmitTrainingResult(result)


class TestCoordinatorService(unittest.TestCase):
    def setUp(self):
        self.server = create_server(TEST_ADDRESS)
        self.server.start()
        self.channel = grpc.insecure_channel(TEST_ADDRESS)
        self.stub = pb_grpc.CoordinatorServiceStub(self.channel)

    def tearDown(self):
        self.channel.close()
        self.server.stop(grace=None)

    def register_two(self):
        a = self.stub.RegisterParticipant(pb.RegisterParticipantRequest(name="Participant A")).participant_id
        b = self.stub.RegisterParticipant(pb.RegisterParticipantRequest(name="Participant B")).participant_id
        return a, b

    def test_demo_scenario_two_participants(self):
        a, b = self.register_two()
        self.assertEqual((a, b), ("p1", "p2"))
        self.assertEqual(len(self.stub.ListParticipants(pb.ListParticipantsRequest()).participants), 2)

        job_id = self.stub.CreateJob(pb.CreateJobRequest(config=pb.TrainingConfig(num_rounds=1))).job_id
        self.assertTrue(self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id)).started)

        self.assertTrue(fake_train(self.stub, a, [8, 10, 12]).accepted)
        self.assertTrue(fake_train(self.stub, b, [18, 20, 22]).accepted)

        job = self.stub.GetTrainingStatus(pb.TrainingStatusRequest(job_id=job_id))
        self.assertEqual(job.status, pb.COMPLETED)
        self.assertEqual(job.global_weight, 15.0)            # (10 + 20) / 2
        self.assertEqual(len(job.results), 2)

    def test_no_task_before_start(self):
        a, _ = self.register_two()
        self.stub.CreateJob(pb.CreateJobRequest())
        self.assertIsNone(fake_train(self.stub, a, [8, 10, 12]))

    def test_job_waits_for_all_participants(self):
        a, _ = self.register_two()
        job_id = self.stub.CreateJob(pb.CreateJobRequest()).job_id
        self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id))
        fake_train(self.stub, a, [8, 10, 12])                 # only A answers
        job = self.stub.GetTrainingStatus(pb.TrainingStatusRequest(job_id=job_id))
        self.assertEqual(job.status, pb.RUNNING)

    def test_multiple_rounds(self):
        a, b = self.register_two()
        job_id = self.stub.CreateJob(pb.CreateJobRequest(config=pb.TrainingConfig(num_rounds=2))).job_id
        self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id))
        for _ in range(2):
            fake_train(self.stub, a, [8, 10, 12])
            fake_train(self.stub, b, [18, 20, 22])
        job = self.stub.GetTrainingStatus(pb.TrainingStatusRequest(job_id=job_id))
        self.assertEqual(job.status, pb.COMPLETED)
        self.assertEqual(job.current_round, 2)
        self.assertEqual(len(job.results), 4)

    def test_duplicate_result_is_rejected(self):
        a, _ = self.register_two()
        job_id = self.stub.CreateJob(pb.CreateJobRequest()).job_id
        self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id))
        result = pb.TrainingResult(job_id=job_id, participant_id=a, round=1, local_weight=10, num_samples=3)
        self.assertTrue(self.stub.SubmitTrainingResult(result).accepted)
        self.assertFalse(self.stub.SubmitTrainingResult(result).accepted)

    def test_unknown_job_gives_not_found(self):
        with self.assertRaises(grpc.RpcError) as error:
            self.stub.GetTrainingStatus(pb.TrainingStatusRequest(job_id="job-99"))
        self.assertEqual(error.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_start_twice_is_refused(self):
        self.register_two()
        job_id = self.stub.CreateJob(pb.CreateJobRequest()).job_id
        self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id))
        with self.assertRaises(grpc.RpcError) as error:
            self.stub.StartTraining(pb.StartTrainingRequest(job_id=job_id))
        self.assertEqual(error.exception.code(), grpc.StatusCode.FAILED_PRECONDITION)

    def test_job_needs_participants(self):
        with self.assertRaises(grpc.RpcError) as error:
            self.stub.CreateJob(pb.CreateJobRequest())
        self.assertEqual(error.exception.code(), grpc.StatusCode.FAILED_PRECONDITION)


if __name__ == "__main__":
    unittest.main()
