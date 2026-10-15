import os
import sys

# 1. Add wrappers/python to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "wrappers", "python"))

from client import ZeroWireEngine, ZeroWireUnknownOffsetException

# 2. Path to zerowire.dll
dll_location = os.path.join(PROJECT_ROOT, "bin", "x64", "Release_Community", "zerowire.dll")
print(f"Target DLL Path: {dll_location}")

# 3. Test ZeroWire Engine
with (
    ZeroWireEngine(dll_location, max_memory_mb=64) as sender,
    ZeroWireEngine(dll_location, max_memory_mb=64) as receiver,
):
    session_id = 10009401
    large_context = (
        b"CONFIDENTIAL FINANCIAL AUDIT REPORT (PDF CONTEXT ATTACHMENT)\n"
        * 1000
    )

    print(f"Raw Context Size: {len(large_context)} bytes")

    # Round 1: Initial Registration
    wire_r1 = sender.compress(session_id, large_context)
    decomp_r1 = receiver.decompress(session_id, wire_r1)
    print(f"Round 1 Wire Size: {len(wire_r1)} bytes")
    assert decomp_r1 == large_context, "Bit-exact match failed on Round 1"

    # Round 2: Stateful Deduplication
    wire_r2 = sender.compress(session_id, large_context)
    decomp_r2 = receiver.decompress(session_id, wire_r2)
    print(f"Round 2 Wire Size: {len(wire_r2)} bytes")
    assert decomp_r2 == large_context, "Bit-exact match failed on Round 2"

    savings = (1.0 - (len(wire_r2) / len(large_context))) * 100.0
    print(f"Wire Reduction: {savings:.2f}%")

    # Resync Test
    try:
        receiver.decompress(session_id=9999, wire_data=wire_r2)
    except ZeroWireUnknownOffsetException:
        print("Resync Protocol Test: PASS (Caught ZeroWireUnknownOffsetException successfully)")