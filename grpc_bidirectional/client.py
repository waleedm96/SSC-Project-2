
import grpc

import hello_pb2
import hello_pb2_grpc


def send_messages():

    while True:

        message = input("Client: ")

        if message.strip():

            yield hello_pb2.ChatMessage(
                sender="Client",
                message=message
            )


def run():

    with grpc.insecure_channel("127.0.0.1:50051") as channel:

        stub = hello_pb2_grpc.ChatServiceStub(channel)

        print("Connected to chat server!")
        print("Type messages to chat. Press Ctrl+C to exit.\n")

        try:

            responses = stub.Chat(send_messages())

            for response in responses:

                print(f"\n{response.sender}: {response.message}")

        except KeyboardInterrupt:

            print("\nChat stopped.")

        except grpc.RpcError as error:

            print("Connection error:", error.details())


if __name__ == "__main__":
    run()
