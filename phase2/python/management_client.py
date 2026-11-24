"""Management Client (CLI)"""
import sys
import grpc

import federated_learning_pb2 as pb
import federated_learning_pb2_grpc as pb_grpc

DEFAULT_ADDRESS = "127.0.0.1:50051"
TIMEOUT_SECONDS = 5.0


class CoordinatorClient:
    """gRPC wrapper for the CoordinatorService."""

    def __init__(self, address: str = DEFAULT_ADDRESS):
        self.address = address
        self._channel = grpc.insecure_channel(address)
        self._stub = pb_grpc.CoordinatorServiceStub(self._channel)

    def close(self) -> None:
        self._channel.close()

    def list_participants(self) -> list:
        request = pb.ListParticipantsRequest()
        reply = self._stub.ListParticipants(request, timeout=TIMEOUT_SECONDS)
        return list(reply.participants)


def handle_rpc_error(err: grpc.RpcError) -> None:
    print(f"[gRPC Error] {err.code().name}: {err.details()}")


def main() -> None:
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    client = CoordinatorClient(address)
    print(f"Connected to Coordinator at {address}")

    try:
        while True:
            print("\n=== Federated Learning Management CLI ===")
            print("1. List registered participants")
            print("0. Exit")
            choice = input("Select an option: ").strip()

            try:
                if choice == "1":
                    participants = client.list_participants()
                    if not participants:
                        print("No participants here :>")
                    else:
                        print(f"\nRegistered participants ({len(participants)}):")
                        for p in participants:
                            print(f"  - {p.participant_id}: {p.name}")
                elif choice == "0":
                    print("Bye!")
                    break
                else:
                    print("Invalid option. Try another bro.")
            except grpc.RpcError as err:
                handle_rpc_error(err)
    finally:
        client.close()


if __name__ == "__main__":
    main()
