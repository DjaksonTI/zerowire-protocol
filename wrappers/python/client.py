import ctypes
import os

# Exception Hierarchy
class ZeroWireException(Exception):
    """Base exception for native ZeroWire engine errors."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{message} (Error Code: {code})")

class ZeroWireUnknownOffsetException(ZeroWireException):
    """Raised when receiver encounters an unknown offset handle requiring stream resync."""
    def __init__(self):
        super().__init__(-11, "Unknown offset handle encountered. Requesting full resync stream.")

class ZeroWireQuotaExceededException(ZeroWireException):
    """Raised when Community build session limits (max 2 active) are exceeded."""
    def __init__(self):
        super().__init__(-105, "Community session quota exceeded (max 2 active sessions supported in Community Build).")

class ZeroWireAuthDeniedException(ZeroWireException):
    """Raised when stream configuration authorization fails or session expires."""
    def __init__(self):
        super().__init__(-106, "Stream configuration authorization failed or session expired.")


class ZeroWireEngine:
    ZEROWIRE_OK = 0
    ZEROWIRE_ERR_INVALID_HANDLE = -1
    ZEROWIRE_ERR_BUFFER_TOO_SMALL = -2
    ZEROWIRE_ERR_INVALID_MAGIC = -10
    ZEROWIRE_ERR_UNKNOWN_OFFSET = -11
    ZEROWIRE_ERR_CORRUPTED_STREAM = -12
    ZEROWIRE_ERR_QUOTA_EXCEEDED = -105
    ZEROWIRE_ERR_AUTH_DENIED = -106

    def __init__(self, dll_path: str, max_memory_mb: int = 64, session_ttl_seconds: int = 3600, stream_config_blob: str = None):
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"ZeroWire native library not found at: {dll_path}")

        self._lib = ctypes.CDLL(dll_path)

        # C-ABI Prototypes
        self._lib.ZeroWire_CreateEngine.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_char_p]
        self._lib.ZeroWire_CreateEngine.restype = ctypes.c_void_p

        self._lib.ZeroWire_DestroyEngine.argtypes = [ctypes.c_void_p]
        self._lib.ZeroWire_DestroyEngine.restype = None

        self._lib.ZeroWire_DestroySession.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        self._lib.ZeroWire_DestroySession.restype = ctypes.c_int32

        self._lib.ZeroWire_ResetSessionState.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        self._lib.ZeroWire_ResetSessionState.restype = ctypes.c_int32

        self._lib.ZeroWire_GetMemoryUsage.argtypes = [ctypes.c_void_p]
        self._lib.ZeroWire_GetMemoryUsage.restype = ctypes.c_size_t

        self._lib.ZeroWire_CompressStream.argtypes = [
            ctypes.c_void_p, ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32,
            ctypes.c_bool
        ]
        self._lib.ZeroWire_CompressStream.restype = ctypes.c_int32

        self._lib.ZeroWire_DecompressStream.argtypes = [
            ctypes.c_void_p, ctypes.c_uint64,
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32,
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_int32
        ]
        self._lib.ZeroWire_DecompressStream.restype = ctypes.c_int32

        # Initialize Handle
        config_bytes = stream_config_blob.encode('utf-8') if stream_config_blob else None
        self._handle = self._lib.ZeroWire_CreateEngine(max_memory_mb, session_ttl_seconds, config_bytes)

        if not self._handle:
            raise RuntimeError("Failed to initialize native ZeroWire engine instance.")

    def _check_error(self, code: int):
        if code >= 0:
            return
        if code == self.ZEROWIRE_ERR_UNKNOWN_OFFSET:
            raise ZeroWireUnknownOffsetException()
        elif code == self.ZEROWIRE_ERR_QUOTA_EXCEEDED:
            raise ZeroWireQuotaExceededException()
        elif code == self.ZEROWIRE_ERR_AUTH_DENIED:
            raise ZeroWireAuthDeniedException()
        elif code == self.ZEROWIRE_ERR_INVALID_MAGIC:
            raise ZeroWireException(code, "Invalid ZeroWire magic framing header ('Z' 'W' signature mismatch).")
        elif code == self.ZEROWIRE_ERR_BUFFER_TOO_SMALL:
            raise ZeroWireException(code, "Destination output buffer capacity too small.")
        elif code == self.ZEROWIRE_ERR_CORRUPTED_STREAM:
            raise ZeroWireException(code, "Corrupted wire payload stream.")
        else:
            raise ZeroWireException(code, f"Native ZeroWire engine failure (Error Code: {code})")

    def compress(self, session_id: int, data: bytes, force_resync: bool = False) -> bytes:
        if not data:
            return b""
        in_len = len(data)
        max_out = in_len + 128
        out_buf = (ctypes.c_uint8 * max_out)()
        in_buf = (ctypes.c_uint8 * in_len).from_buffer_copy(data)

        res = self._lib.ZeroWire_CompressStream(
            self._handle, session_id, in_buf, in_len, out_buf, max_out, force_resync
        )
        self._check_error(res)
        return bytes(out_buf[:res])

    def decompress(self, session_id: int, wire_data: bytes, max_output_estimate: int = 10 * 1024 * 1024) -> bytes:
        if not wire_data:
            return b""
        in_len = len(wire_data)
        # Ensure buffer is large enough for restored context on 5-byte deduplicated payloads
        max_out = max(max_output_estimate, in_len * 128 + 1024)
        out_buf = (ctypes.c_uint8 * max_out)()
        in_buf = (ctypes.c_uint8 * in_len).from_buffer_copy(wire_data)

        res = self._lib.ZeroWire_DecompressStream(
            self._handle, session_id, in_buf, in_len, out_buf, max_out
        )
        self._check_error(res)
        return bytes(out_buf[:res])
    def destroy_session(self, session_id: int):
        res = self._lib.ZeroWire_DestroySession(self._handle, session_id)
        self._check_error(res)

    def reset_session_state(self, session_id: int):
        res = self._lib.ZeroWire_ResetSessionState(self._handle, session_id)
        self._check_error(res)

    def get_memory_usage(self) -> int:
        return self._lib.ZeroWire_GetMemoryUsage(self._handle)

    def close(self):
        if self._handle:
            self._lib.ZeroWire_DestroyEngine(self._handle)
            self._handle = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()