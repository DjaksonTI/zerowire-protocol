import json
import logging
import os
import sys
import time
from typing import Dict, List

import grpc

SYS_DIR = os.path.dirname(os.path.abspath(__file__))               # tests/distributed_swarm/client
SWARM_DIR = os.path.dirname(SYS_DIR)                                # tests/distributed_swarm
TESTS_DIR = os.path.dirname(SWARM_DIR)                               # tests
ROOT_DIR = os.path.dirname(TESTS_DIR)                               # zerowire-protocol
WRAPPERS_PYTHON = os.path.join(ROOT_DIR, "wrappers", "python")

sys.path.insert(0, WRAPPERS_PYTHON)
sys.path.insert(0, SWARM_DIR)
sys.path.insert(0, os.path.join(SWARM_DIR, "proto"))
sys.path.insert(0, ROOT_DIR)

import agent_payload_pb2
import agent_payload_pb2_grpc
from client import ZeroWireEngine
from config import DLL_PATH


class SwarmOrchestrator:

    def __init__(self, node_map: Dict[str, int]):
        self.node_map = node_map
        self.engine = ZeroWireEngine(DLL_PATH, max_memory_mb=64)
        self.telemetry = []

        self.heavy_pdf_bytes = (
            "CONFIDENTIAL FINANCIAL AUDIT REPORT (PDF CONTEXT ATTACHMENT)\n"
            + "=" * 65
            + "\n"
            + (
                "Record Entry: Asset allocation delta = +0.0042% | Node status: VERIFIED | Security: LOCAL_ONLY\n"
                * 350
            )
        ).encode("utf-8")

        self.system_prompt_bytes = (
            "You are an enterprise AI sub-agent operating in the secure RAGU-PRO cluster. "
            "Analyze contexts and user tasks strictly without leaking memory boundaries."
        ).encode("utf-8")

    def execute_swarm_task(
        self, agent_id: str, session_id: int, turn: int, user_task_str: str
    ):
        port = self.node_map[agent_id]
        channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        stub = agent_payload_pb2_grpc.AgentTransportServiceStub(channel)

        user_task_bytes = user_task_str.encode("utf-8")

        raw_size = (
            len(self.system_prompt_bytes)
            + len(self.heavy_pdf_bytes)
            + len(user_task_bytes)
        )

        start_time = time.perf_counter()

        def build_request(force_sync=False):
            req = agent_payload_pb2.AgentTransactionPayload()
            req.session_id = session_id
            req.sequence_number = turn
            req.sender_agent_id = "Orchestrator"
            req.target_agent_id = agent_id

            req.system_prompt = self.engine.compress(
                session_id, self.system_prompt_bytes, force_resync=force_sync
            )
            req.pdf_context.doc_id = "DOC_AUDIT_2026"
            req.pdf_context.filename = "audit_report.pdf"
            req.pdf_context.content_bytes = self.engine.compress(
                session_id, self.heavy_pdf_bytes, force_resync=force_sync
            )
            req.user_task = self.engine.compress(
                session_id, user_task_bytes, force_resync=force_sync
            )
            return req

        request = build_request(force_sync=False)
        wire_size = request.ByteSize()

        resync_occurred = False
        response = stub.ExecuteAgentTask(request)

        # Handle Resync Handshake if receiver state was cleared
        if not response.success and response.status_code == 404:
            resync_occurred = True
            print(
                f"   [Resync Triggered] Node {agent_id} requested full dictionary state."
            )
            request = build_request(force_sync=True)
            wire_size = request.ByteSize()
            response = stub.ExecuteAgentTask(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if response.success:
            llm_reply = self.engine.decompress(
                session_id, response.payload.llm_response
            ).decode("utf-8")

            reduction = (1.0 - (wire_size / raw_size)) * 100.0

            telemetry_entry = {
                "agent_id": agent_id,
                "session_id": session_id,
                "turn": turn,
                "raw_bytes": raw_size,
                "wire_bytes": wire_size,
                "reduction_pct": round(reduction, 2),
                "latency_ms": round(elapsed_ms, 2),
                "resync_triggered": resync_occurred,
                "gemini_reply_snippet": llm_reply[:100].replace("\n", " "),
            }
            self.telemetry.append(telemetry_entry)

            # Explicit direct stdout reporting
            print(
                f"  [Node: {agent_id:15s} | Turn {turn:02d}] "
                f"Raw: {raw_size/1024:5.1f}KB | Wire: {wire_size:5d} bytes | "
                f"Reduction: {reduction:6.2f}% | Latency: {elapsed_ms:7.1f}ms"
            )
            clean_reply = llm_reply[:80].replace("\n", " ")
            print(f"    Gemini Response: \"{clean_reply}...\"")
        else:
            print(
                f"   [Node: {agent_id}] Task Execution Failed: {response.error_message}"
            )

        channel.close()