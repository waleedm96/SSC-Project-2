import federated_learning_pb2 as fl_pb2
import federated_learning_pb2_grpc as fl_pb2_grpc
import grpc
import logging

class ParticipantService (fl_pb2_grpc.ParticipantServiceServicer) : 

    def __init__() : 
        current_job = None
        previous_job = []

    def SendTrainingTask(self, request, context) :
        
        

        return fl_pb2.TrainingResult(
            job_id=...,
            participant_id=...,
            round=...,
            local_weight=...,
            num_samples=...
        )

def register(server_address) : 
    

def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = fl_pb2_grpc.CoordinatorServiceStub(channel)
        print("-------------- GetFeature --------------")
        (stub)


if __name__ == "__main__":
    logging.basicConfig()
    run()