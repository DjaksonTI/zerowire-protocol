import argparse
import logging
import os
import sys
import time
from concurrent import futures

SYS_DIR = os.path.dirname(os.path.abspath(__file__))               # tests/distributed_swarm/server
SWARM_DIR = os.path.dirname(SYS_DIR)                                # tests/distributed_swarm
TESTS_DIR = os.path.dirname(SWARM_DIR)                               # tests
PROJECT_ROOT = os.path.dirname(TESTS_DIR)                           # zerowire-protocol

WRAPPERS_PYTHON = os.path.join(PROJECT_ROOT, "wrappers", "python")

for path in [WRAPPERS_PYTHON, SWARM_DIR, os.path.join(SWARM_DIR, "proto"), PROJECT_ROOT]:
    if path not in sys.path:
        sys.path.insert(0, path)

import agent_payload_pb2
import agent_payload_pb2_grpc
import grpc
from client import ZeroWireEngine, ZeroWireUnknownOffsetException
from config import DLL_PATH
from gemini_node import GeminiNode

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("AgentService")


class AgentServiceServicer(agent_payload_pb2_grpc.AgentTransportServiceServicer):

    def __init__(self, agent_id: str, port: int):
        self.agent_id = agent_id
        self.port = port

        self.engine = ZeroWireEngine(DLL_PATH, max_memory_mb=64, session_ttl_seconds=3600)
        self.gemini = GeminiNode()
        logger.info(
            f"🟢 [Node: {self.agent_id}] Process listening on TCP Port {self.port}"
        )

    def ExecuteAgentTask(self, request, context):
        session_id = request.session_id
        start_time = time.perf_counter()

        logger.info(
            f"📥 [{self.agent_id} | Port {self.port}] Received gRPC payload for Session {session_id} (Turn {request.sequence_number})"
        )

        try:
            sys_prompt = self.engine.decompress(
                session_id, request.system_prompt
            ).decode("utf-8")
            pdf_bytes = self.engine.decompress(
                session_id, request.pdf_context.content_bytes
            )
            user_task = self.engine.decompress(
                session_id, request.user_task
            ).decode("utf-8")
        except ZeroWireUnknownOffsetException:
            logger.warning(
                f"⚠️ [{self.agent_id}] Handle mismatch! Requesting sender resync..."
            )
            return agent_payload_pb2.TransportResponse(
                success=False,
                status_code=404,
                error_message="ZEROWIRE_ERR_UNKNOWN_OFFSET",
            )

        pdf_summary = pdf_bytes.decode("utf-8", errors="ignore")[:500]
        llm_text = self.gemini.generate_agent_response(
            sys_prompt, user_task, pdf_summary
        )

        compressed_response = self.engine.compress(
            session_id, llm_text.encode("utf-8")
        )

        resp_payload = agent_payload_pb2.AgentTransactionPayload()
        resp_payload.CopyFrom(request)
        resp_payload.target_agent_id = self.agent_id
        resp_payload.llm_response = compressed_response

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        logger.info(
            f"✅ [{self.agent_id}] Finished Gemini task & gRPC pack in {elapsed_ms:.2f}ms"
        )

        return agent_payload_pb2.TransportResponse(
            success=True, status_code=200, payload=resp_payload
        )


def serve(agent_id: str, port: int):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    agent_payload_pb2_grpc.add_AgentTransportServiceServicer_to_server(
        AgentServiceServicer(agent_id, port), server
    )
    
    # Explicitly bind to 127.0.0.1 for local IPC
    bound_port = server.add_insecure_port(f"127.0.0.1:{port}")
    if bound_port == 0:
        logger.error(f"❌ Could not bind to TCP port 127.0.0.1:{port} - port may be in use or blocked!")
        sys.exit(1)

    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True, help="Agent Node ID")
    parser.add_argument(
        "--port", required=True, type=int, help="TCP Port to listen on"
    )
    args = parser.parse_args()

    serve(args.id, args.port)