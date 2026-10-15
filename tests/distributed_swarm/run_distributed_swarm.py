import json
import os
import socket
import subprocess
import sys
import time

SYS_DIR = os.path.dirname(os.path.abspath(__file__))                 # tests/distributed_swarm
TESTS_DIR = os.path.dirname(SYS_DIR)                                 # tests
PROJECT_ROOT = os.path.dirname(TESTS_DIR)                           # zerowire-protocol

sys.path.insert(0, SYS_DIR)
sys.path.insert(0, os.path.join(SYS_DIR, "client"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "wrappers", "python"))
sys.path.insert(0, PROJECT_ROOT)

from config import BASE_PORT
from swarm_orchestrator import SwarmOrchestrator


def wait_for_port(port: int, timeout_sec: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.2)
    return False


def run_swarm_benchmark(num_agents: int = 10, turns_per_agent: int = 5):
    print("=" * 85)
    print("   DISTRIBUTED SWARM BENCHMARK (REAL SOCKETS + REAL GEMINI API)")
    print("=" * 85)

    agent_names = [
        "Supervisor",
        "Auditor_Alpha",
        "Auditor_Beta",
        "DB_Router_1",
        "DB_Router_2",
        "Doc_Parser_1",
        "Doc_Parser_2",
        "Security_Node",
        "Compliance_Node",
        "Analytics_Node",
    ][:num_agents]

    node_map = {}
    processes = []

    server_script = os.path.join(SYS_DIR, "server", "agent_service.py")

    child_env = os.environ.copy()
    existing_pythonpath = child_env.get("PYTHONPATH", "")
    wrappers_python = os.path.join(PROJECT_ROOT, "wrappers", "python")
    
    additional_paths = os.path.pathsep.join(
        [PROJECT_ROOT, SYS_DIR, os.path.join(SYS_DIR, "proto"), wrappers_python]
    )
    child_env["PYTHONPATH"] = (
        f"{additional_paths}{os.path.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else additional_paths
    )

    print(
        f"\n Launching {num_agents} standalone OS processes on TCP Ports {BASE_PORT} to {BASE_PORT + num_agents - 1}..."
    )

    for i, name in enumerate(agent_names):
        port = BASE_PORT + i
        node_map[name] = port

        proc = subprocess.Popen(
            [sys.executable, "-u", server_script, "--id", name, "--port", str(port)],
            env=child_env,
        )
        processes.append(proc)

    print(" Verifying TCP socket bindings across all background processes...\n")

    for name, port in node_map.items():
        ready = wait_for_port(port, timeout_sec=10.0)
        if not ready:
            print(
                f" ERROR: Node '{name}' failed to respond on 127.0.0.1:{port}!"
            )
            for p in processes:
                p.terminate()
            return
        print(f"   Node '{name:15s}' active on 127.0.0.1:{port}")

    try:
        orchestrator = SwarmOrchestrator(node_map)

        print("\n Executing Distributed Swarm Workflows across gRPC Sockets...\n")

        for turn in range(1, turns_per_agent + 1):
            print(f"---------------------------------------------------------------------------------")
            print(f" SWARM CONVERSATION ROUND TRIP #{turn}")
            print(f"---------------------------------------------------------------------------------")
            for idx, name in enumerate(agent_names):
                session_id = 2000 + idx
                task_prompt = f"Perform audit analysis turn #{turn}. Verify item ledger delta."

                orchestrator.execute_swarm_task(
                    agent_id=name,
                    session_id=session_id,
                    turn=turn,
                    user_task_str=task_prompt,
                )
                time.sleep(1.0)  # Pacing delay to avoid API quota limits
            print()

        print("\n" + "=" * 85)
        print("  DISTRIBUTED SWARM BENCHMARK SUMMARY")
        print("=" * 85)

        records = orchestrator.telemetry
        if records:
            total_raw = sum(r["raw_bytes"] for r in records) / 1024.0
            total_wire = sum(r["wire_bytes"] for r in records) / 1024.0
            overall_savings = (1.0 - (total_wire / total_raw)) * 100.0
            avg_latency = sum(r["latency_ms"] for r in records) / len(records)

            print(f"  Total Network Transactions:   {len(records)}")
            print(f"  Active OS Processes:          {num_agents} Nodes")
            print(
                f"  Transport Protocol:           gRPC (HTTP/2 Sockets + Protobuf)"
            )
            print(f"  LLM Provider:                 Google Gemini API")
            print(f"  Average Roundtrip Latency:    {avg_latency:.2f} ms")
            print(
                f"  Total Uncompressed Data:      {total_raw:.2f} KB"
            )
            print(
                f"  Total Wire Transmitted Data:  {total_wire:.2f} KB"
            )
            print(f"  NET BANDWIDTH REDUCTION:      {overall_savings:.2f}%")
            print("=" * 85)

            out_file = os.path.join(SYS_DIR, "distributed_telemetry.json")
            with open(out_file, "w") as f:
                json.dump(records, f, indent=2)
            print(f"\n Audit log written to: {out_file}\n")

    finally:
        print("\n Shutting down agent background processes...")
        for p in processes:
            p.terminate()
            p.wait()


if __name__ == "__main__":
    run_swarm_benchmark(num_agents=10, turns_per_agent=5)