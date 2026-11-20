import grpc
from concurrent import futures
import hello_pb2
import hello_pb2_grpc

# 1. Implement our gRPC service
class GreeterService(hello_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        print("Received request from:", request.name)
        return hello_pb2.HelloReply(
            message=f"Hello {request.name}! Welcome to gRPC.")

# 2. Create and start the gRPC server
def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10))
    hello_pb2_grpc.add_GreeterServicer_to_server(  # Register our service with the server
        GreeterService(), server)
    server.add_insecure_port("127.0.0.1:50051") # Server listens on port 50051
    server.start()
    print("gRPC Server started on port 50051...")
    server.wait_for_termination() # Keep server running

if __name__ == "__main__":
    serve()
