
import grpc
import threading
from concurrent import futures

import hello_pb2
import hello_pb2_grpc


class ChatService(hello_pb2_grpc.ChatServiceServicer):

    def Chat(self, request_iterator, context):

        # Receive messages from the client in a separate thread
        def receive_messages():

            for request in request_iterator:
                print(f"\n{request.sender}: {request.message}")

        receiver = threading.Thread(
            target=receive_messages,
            daemon=True
        )

        receiver.start()

        print("Chat connection established!")
        print("Type your messages below. Press Ctrl+C to stop.")

        # Send messages from the server to the client
        while context.is_active():

            message = input("Server: ")

            if message.strip():
                yield hello_pb2.ChatMessage(
                    sender="Server",
                    message=message
                )


def serve():

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    hello_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatService(), server
    )

    server.add_insecure_port("127.0.0.1:50051")

    server.start()

    print("Chat server is running on port 50051...")

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
