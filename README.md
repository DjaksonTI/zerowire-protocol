<div align="center">

# ZeroWire Protocol
### High-Performance Radix-Trie Transport Engine for Distributed Agent Swarms

[![License: Dual-Tier](https://img.shields.io/badge/License-Dual--Tier-blue.svg)](LICENSE)
[![Platform: Win64 / Linux](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)](bin/)
[![Languages: C++ / Python / C#](https://img.shields.io/badge/Language-C++17%20%7C%20Python%20%7C%20C%23-orange.svg)]()
[![Bandwidth Reduction](https://img.shields.io/badge/Bandwidth%20Reduction-~99.99%25-success.svg)]()

*Stateful semantic deduplication engine engineered to eliminate redundant payload transmission across distributed multi-agent LLM systems.*

</div>

---

## Executive Overview

Modern distributed agent swarms—orchestrating dozens of concurrent LLM nodes, RAG pipelines, and tool-use microservices—suffer from catastrophic payload bloat. Large system prompts, extensive context windows, and repetitive ledger documents are redundantly transmitted over network sockets on every conversational turn.

**ZeroWire** solves this at the transport layer. By utilizing an in-memory **Radix-Trie deduplication engine** wrapped with a lean C-ABI, ZeroWire identifies and abstracts recurring data blocks into lightweight 5-byte tracking handles. The result is a **99.9%+ bandwidth reduction** on subsequent roundtrips, bringing enterprise multi-agent synchronization down to microsecond-tier wire footprints without modifying upstream application logic.

---

## Core Architecture

```
 [ Agent Client (C# / Python) ] 
         │ (Raw Payload: 61 KB)
         ▼
 ┌───────────────────────────────────────────────┐
 │          ZeroWire Transport Engine            │
 │  ┌─────────────────────────────────────────┐  │
 │  │      Radix-Trie Index & Deduplicator    │  │
 │  └─────────────────────────────────────────┘  │
 │          │ Match Found?                       │
 │    ┌─────┴─────┐                              │
 │   Yes          No                             │
 │    ▼           ▼                              │
 │ [ 5-Byte     [ Full Stream +                │
 │   Handle ]     Trie Insert ]                  │
 └──────┬────────────────────────────────────────┘
        ▼ (Wire Payload: 5 Bytes | 99.99% Reduction)
 [ Network Socket / gRPC / HTTP/2 ]
```

* **C++ Core Engine (`zerowire_engine.cpp`)**: High-performance core featuring stateful window tracking, memory bounds enforcement, and zero-copy C-ABI export headers.
* **Radix-Trie Transport Layer**: Deterministic prefix-tree indexing maps chunk references dynamically per session ID, ensuring strict isolation and bit-exact recovery.
* **Multi-Language SDK Wrappers**: Native P/Invoke bindings for C# (`ZeroWire.Client`) and `ctypes` bindings for Python (`zerowire-client`), mapping internal error codes directly to idiomatic exceptions.

---

## Performance Benchmarks

Verified across distributed 10-node OS process swarms running real TCP socket loops and LLM workloads:

| Metric | Standard Payload (Round 1) | Deduplicated Payload (Round 2+) |
| :--- | :--- | :--- |
| **Payload Size** | 61,000 Bytes | **5 Bytes** |
| **Bandwidth Reduction** | Baseline (0.00%) | **99.99%** |
| **Memory Footprint** | Dynamic Session Cache | Bounded (Configurable Max MB) |
| **Exception Handling** | Bit-exact match validation | Automatic Resync Trigger (`-11`) |

---

## Quick Start Guide

### Python Integration
```python
from client import ZeroWireEngine, ZeroWireUnknownOffsetException

# Initialize engine instance with memory limits
with ZeroWireEngine("path/to/zerowire.dll", max_memory_mb=64) as engine:
    session_id = 10009401
    large_context = b"CONFIDENTIAL FINANCIAL AUDIT REPORT (CONTEXT ATTACHMENT)\n" * 1000

    # Round 1: Initial state registration & transmission
    wire_r1 = engine.compress(session_id, large_context)
    decomp_r1 = engine.decompress(session_id, wire_r1)
    
    # Round 2: Stateful deduplication (Reduces 61KB -> 5 bytes)
    wire_r2 = engine.compress(session_id, large_context)
    decomp_r2 = engine.decompress(session_id, wire_r2)
    
    assert decomp_r2 == large_context
```

### C# Integration
```csharp
using ZeroWire.Client;

using (var engine = new ZeroWireEngine("zerowire.dll", maxMemoryMb: 64))
{
    ulong sessionId = 10009401;
    byte[] payload = System.Text.Encoding.UTF8.GetBytes("Enterprise Agent Ledger Payload...");

    // Compress & transmit over socket
    byte[] wireData = engine.Compress(sessionId, payload);
    
    // Receive & restore on remote node
    byte[] restored = engine.Decompress(sessionId, wireData);
}
```

---

## Licensing & Distribution Model

ZeroWire employs a **Dual-Tier Commercial Licensing** structure:

* **Community Build**: 
  * Distributed freely via NuGet and PyPI.
  * Hard-capped at **2 active concurrent sessions** and **16MB max memory allocation**.
  * Ideal for local development, prototyping, and evaluation.
* **Commercial / Enterprise Build**:
  * Uncapped memory allocations and concurrent active sessions.
  * Protected via RSA license key validation strings and compile-time XOR obfuscation layers.
  * Contact for enterprise licensing inquiries.

---

## Repository Structure

```tree
zerowire-protocol/
├── bin/
│   └── x64/
│       └── Release_Community/    # Compiled Community binaries (zerowire.dll)
├── src/                          # C++ Core Transport Engine source
├── wrappers/
│   ├── python/                   # Python ctypes wrapper & client
│   └── csharp/                   # C# P/Invoke client implementation
└── tests/
    ├── local_tests/              # Unit & bit-exact validation suites
    └── distributed_swarm/        # Real socket + multi-process benchmarks
```

---

## Contributing & Support

Contributions, architectural discussions, and bug reports are welcome. Please review our contribution guidelines before submitting pull requests for wrapper extensions or core protocol improvements.