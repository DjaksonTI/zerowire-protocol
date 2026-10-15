import os

# Hardcoded Gemini API Credentials
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"

# Default Model for Agent Reasoning
GEMINI_MODEL = "gemini-3.8-flash"

# Resolve absolute path to project root (zerowire-protocol)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))               # tests/distributed_swarm
SWARM_DIR = CONFIG_DIR
TESTS_DIR = os.path.dirname(SWARM_DIR)                               # tests
PROJECT_ROOT = os.path.dirname(TESTS_DIR)                             # zerowire-protocol

# Direct path to compiled C++ DLL
DLL_PATH = os.path.abspath(
    os.path.join(PROJECT_ROOT, "bin", "x64", "Release_Community", "zerowire.dll")
)

# Network Socket Allocation Base
BASE_PORT = 50051