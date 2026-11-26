# Testing only
import sys
import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

ADDRESS = "127.0.0.1:50051"


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "UIA"
    with grpc.insecure_channel(ADDRESS) as channel:
        stub = pb_grpc.CoordinatorServiceStub(channel)
        reply = stub.RegisterParticipant(pb.RegisterParticipantRequest(name=name), timeout=5.0)
        print(f"[{name}] Registered with ID: {reply.participant_id}")


if __name__ == "__main__":
    main()
