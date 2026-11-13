import serverservices_pb2_grpc
import serverservices_pb2
import grpc
from concurrent import futures


class ServerServicer(serverservices_pb2_grpc.TrainingService):

    def startTraining(self, request, context) : 
        print(request)
        return serverservices_pb2.TrainingAnswer(request="aa") 
        #return reply

def serve():
    print("Server started listening on http://localhost:50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    serverservices_pb2_grpc.add_TrainingServiceServicer_to_server(ServerServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__" : 
    serve()