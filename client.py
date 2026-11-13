import serverservices_pb2_grpc
import serverservices_pb2
import grpc
import logging


def startTraining(stub):
    trainingAnswer = stub.startTraining("bde")
    print ("Here's the training answer : ", trainingAnswer)


def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = serverservices_pb2_grpc.TrainingServiceStub(channel)
        print("-------------- GetFeature --------------")
        startTraining(stub)


if __name__ == "__main__":
    logging.basicConfig()
    run()