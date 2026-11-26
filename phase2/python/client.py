#---GRPC---
import federated_learning_pb2 as fl_pb2
import federated_learning_pb2_grpc as fl_pb2_grpc
import grpc

#---GRPC serving---
from logging import basicConfig
#import threading
#import time
from concurrent import futures
from random import choice, uniform
from string import ascii_uppercase, digits
from socket import socket

#---Port association---
sock = socket()
sock.bind(('', 0))

#---Connection properties---
ADDRESS = f"127.0.0.1:{sock.getsockname()[1]}"
SERVER_ADDRESS = "127.0.0.1:50051"
NAME = "Client A" #''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))

class ParticipantServicer(fl_pb2_grpc.ParticipantServiceServicer) : 
    """
    Defines the interface through which the server sends training jobs to the client.
    """
    def __init__(self) : 
        current_job = None
        previous_job = []

    def SendTrainingTask(self, request, context) :        

        task = request.task
        print("____Task received____ : \n", task)

        new_weight = uniform(a=-20., b=20.)

        print("____Computed weight____ : ", new_weight)
        print("______________________________________")
        
        return fl_pb2.TrainingResult(
            job_id=task.job_id,
            participant_id=ADDRESS,
            round=task.round,
            local_weight=new_weight,
            num_samples=1
        )

def register(server_address : str = SERVER_ADDRESS) : 
    """
    Register to the given server using the CoordinatorService.
    """
    with grpc.insecure_channel(server_address) as channel:
        stub = fl_pb2_grpc.CoordinatorServiceStub(channel)

        registering_request = fl_pb2.RegisterParticipantRequest(
            participant_ip_addr=ADDRESS,
            name=NAME
        )
        reply = stub.RegisterParticipant(registering_request)
        print(reply)
        print(f"Succesfully connected to coordinator at address {server_address}")

def create_server(address: str = ADDRESS) -> grpc.Server:
    """
    Same function as in the coordinator : make a module from it? 
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    fl_pb2_grpc.add_ParticipantServiceServicer_to_server(ParticipantServicer(), server)
    server.add_insecure_port(address)
    return server

def serve() : 
    """
    Start the participant service
    """
    server = create_server()
    server.start()
    print(f"Client Service started on {ADDRESS} - waiting for requests (Ctrl+C to stop)")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Stopping")
        server.stop(grace=0)

if __name__ == "__main__":
    basicConfig()
    try : 
        register()
        serve()
    except Exception as e : 
        print("An error occured while trying to connect to server.")
        print("Error : ", e)

