import generatedFiles.client.protos.clientservices_pb2
import generatedFiles.client.protos.clientservices_pb2_grpc
import grpc
import logging


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