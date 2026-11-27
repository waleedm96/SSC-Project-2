// gRPC client for the Coordinator Service (the participant only needs RegisterParticipant).
// Wraps the generated stub so the rest of the code can use async/await instead of callbacks.

const path = require("node:path");
const grpc = require("@grpc/grpc-js");
const protoLoader = require("@grpc/proto-loader");

// Same .proto file the Python coordinator uses - this is the contract between the languages.
const PROTO_PATH = path.join(__dirname, "..", "..", "proto", "federated_learning.proto");

function loadProto(protoPath = PROTO_PATH) {
  const packageDefinition = protoLoader.loadSync(protoPath, {
    keepCase: true, // keep field names as in the .proto (participant_ip_addr, not participantIpAddr)
    defaults: true, // missing fields get default values
    enums: String,  // enums as names ("RUNNING") instead of numbers
  });
  return grpc.loadPackageDefinition(packageDefinition).sscfederated;
}

class CoordinatorClient {
  constructor(address, { rpcTimeoutMs = 5000, proto = loadProto() } = {}) {
    this.address = address;
    this._rpcTimeoutMs = rpcTimeoutMs;
    this._stub = new proto.CoordinatorService(address, grpc.credentials.createInsecure());
  }

  // Turns one callback-style gRPC call into a Promise, with a deadline so it never hangs forever.
  _call(method, request) {
    return new Promise((resolve, reject) => {
      const deadline = new Date(Date.now() + this._rpcTimeoutMs);
      this._stub[method](request, { deadline }, (err, reply) => (err ? reject(err) : resolve(reply)));
    });
  }

  /** Tells the coordinator where this participant's ParticipantService can be reached. */
  async register(name, participantAddress) {
    const reply = await this._call("RegisterParticipant", { name, participant_ip_addr: participantAddress });
    return reply.participant_ip_addr;
  }

  close() {
    this._stub.close();
  }
}

module.exports = { CoordinatorClient, loadProto, PROTO_PATH };
