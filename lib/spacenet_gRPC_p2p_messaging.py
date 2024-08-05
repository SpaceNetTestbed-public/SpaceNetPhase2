# spacenet_gRPC_p2p_messaging.py

import grpc
from lib import p2p_messaging_pb2
from lib import p2p_messaging_pb2_grpc
import json # for dictionary serialization/deserialization to strings
from concurrent import futures # for threading gRPC server
import threading # for threading gRPC client

# Suggested values
gRPC_server_port_num = 50051
max_connections_from_peers = 10

#gRPC message structure
# message_dict[message_type] = [message1, message2, ...] (if message type supports more than one message in a single transmission)
# message_dict[message_type] = message (if message type only supports one message in a single transmission)
# Message types:
# 1: Neighbor discovery request (single)
# 2: Neighbor discovery response (single)
# 3: Neighbor routing table update (multiple)
# 4: Mininet add routes (multiple)
# 5: Mininet remove routes (multiple)
# 6: Mininet controller shutdown command (single)
# 99: Generic message (multiple)
NEIGH_DISCV_REQ = 1
NEIGH_DISCV_RESP = 2
NEIGH_ROUTING_TABLE_UPDATE = 3
MININET_ADD_ROUTES = 10
MININET_ADD_DFLT_ROUTE = 11
MININET_REMOVE_ROUTES = 12
MININET_CTRL_SHUTDOWN = 13
NODE_RESPONSE_READY = 20
NODE_RESPONSE_HALTED = 21
GENERIC_MESSAGE = 99

# gRPC peer-to-peer messaging
class P2PServicer(p2p_messaging_pb2_grpc.P2PServiceServicer):
    def __init__(self, callback, own_satnum=None, verbose=False):
        #global gRPC_verbose
        self.callback = callback
        self.own_satnum = own_satnum
        self.verbose = verbose
        self.verbose = verbose
    #    self.clients = {} # Create a dictionary to store client contexts and message queues
    def PeerMessage(self, request, context): # The PeerMessage method is called by the client to connect to the server - will disconnect if this function returns
            reply_message = self.callback(request, context, self.verbose)
            return p2p_messaging_pb2.PeerReply(message=reply_message)

class gRPCServerManager():
    def __init__(self, callback, own_satnum, port_num, max_connections = 10, verbose = False):
        self.callback = callback
        self.own_satnum = own_satnum
        self.port_num = port_num
        self.max_connections = max_connections
        self.verbose = verbose

        self.server = None
    
    def start_gRPC_server(self):
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_connections))
            #p2p_messaging_pb2_grpc.add_P2PServiceServicer_to_server(P2PServicer(callback=callback, own_satnum=own_satnum, verbose=verbose), server)
            p2p_messaging_pb2_grpc.add_P2PServiceServicer_to_server(P2PServicer(callback=self.callback, own_satnum=self.own_satnum, verbose=self.verbose), self.server)
            self.server.add_insecure_port('0.0.0.0:' + str(self.port_num)) # listen on specified port
            try:
                self.server.start()
            except Exception as exc:
                print(f"(spacenet_gRPC_p2p_messaging.gRPCServerManager.run_gRPC_server) Error starting server: {exc}")
                exit()
            if self.verbose:
                print("(spacenet_gRPC_p2p_messaging.gRPCServerManager.run_gRPC_server) gRPC Server started")
            #return self.server

    def stop_gRPC_server(self, blocking = False):
        if self.verbose:
            print(f"(spacenet_gRPC_p2p_messaging.gRPCServerManager.stop_gRPC_server) Stopping server. Blocking = {blocking}")
        self.server.stop(grace=None)
        if blocking:
            self.server.wait_for_termination()
        if self.verbose:
            print("(spacenet_gRPC_p2p_messaging.gRPCServerManager.stop_gRPC_server) gRPC Server stopped")

def run_gRPC_client(peer_socket_address, message, message_id=None, verbose = False, retry = True):
        channel = grpc.insecure_channel(peer_socket_address) # Create a gRPC channel to connect to the peer
        stub = p2p_messaging_pb2_grpc.P2PServiceStub(channel) # Create a gRPC stub to call the peer's methods
        if verbose:
            if message_id:
                print(f"> (spacenet_gRPC_p2p_messaging.run_gRPC_client) Sending message [ID: {message_id}] to peer: {message}")
            else:
                print(f"> (spacenet_gRPC_p2p_messaging.run_gRPC_client) Sending message to peer: {message}")
        try:
            response = stub.PeerMessage(p2p_messaging_pb2.PeerReply(message=message)) # Call the peer's PeerMessage method to send a message
        except Exception as exc:
            if message_id:
                print(f"(spacenet_gRPC_p2p_messaging.run_gRPC_client)  Error sending message [ID: {message_id}] to peer: {exc}")
            else:
                print(f"(spacenet_gRPC_p2p_messaging.run_gRPC_client)  Error sending message to peer: {exc}")
            if retry:
                print(f"(spacenet_gRPC_p2p_messaging.run_gRPC_client)  Retrying message to peer: {peer_socket_address}")
                run_gRPC_client(peer_socket_address, message, message_id, verbose, retry = False)
            return
        if verbose:
            if message_id:
                print(f"< (spacenet_gRPC_p2p_messaging.run_gRPC_client)  Response from peer {peer_socket_address} [ID: {message_id}]: " + response.message)
            else:
                print(f"< (spacenet_gRPC_p2p_messaging.run_gRPC_client)  Response from peer {peer_socket_address}: " + response.message)

def send_gRPC_message_to_peer(peer_socket_address, message, message_id=None, verbose = False):
    if verbose:
        if message_id:
            print(f"(spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer) Sending message [ID: {message_id}] to peer at {peer_socket_address}")
        else:
            print(f"(spacenet_gRPC_p2p_messaging.send_gRPC_message_to_peer) Sending message to peer at {peer_socket_address}")
    if type(message) is dict:
        #print("Converting dict message to JSON string")
        message = "" + json.dumps(message)
    client_thread = threading.Thread(target=run_gRPC_client, args=(peer_socket_address, message, message_id, verbose)) # Create a thread to run the run_client function to allow continued execution while waiting on peer's response
    client_thread.start()
    # will not wait for client_thread to finish

def decode_gRPC_message_code(message_code):
    if message_code == NEIGH_DISCV_REQ:
        return "Neighbor discovery request"
    elif message_code == NEIGH_DISCV_RESP:
        return "Neighbor discovery response"
    elif message_code == NEIGH_ROUTING_TABLE_UPDATE:
        return "Neighbor routing table update"
    elif message_code == MININET_ADD_ROUTES:
        return "Mininet add routes"
    elif message_code == MININET_REMOVE_ROUTES:
        return "Mininet remove routes"
    elif message_code == MININET_CTRL_SHUTDOWN:
        return "Mininet controller shutdown command"
    elif message_code == NODE_RESPONSE_READY:
        return "Node response ready"
    elif message_code == NODE_RESPONSE_HALTED:
        return "Node response halted"
    elif message_code == GENERIC_MESSAGE:
        return "Generic message"
    else:
        return "Unknown message code"