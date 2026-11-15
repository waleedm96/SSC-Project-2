
import grpc

import hello_pb2
import hello_pb2_grpc


def run():

    # Step 1: Connect to the gRPC server
    channel = grpc.insecure_channel("127.0.0.1:50051")

    # Step 2: Create a client stub
    stub = hello_pb2_grpc.GreeterStub(channel)

    # Step 3: Create a request
    request = hello_pb2.HelloRequest(name="Waleed Mahmood")

    # Step 4: Call the server function remotely
    response = stub.SayHello(request)

    # Step 5: Print the response
    print("Server response:", response.message)

    # Step 6: Close the connection
    channel.close()


if __name__ == "__main__":
    run()
