using System;

namespace ZeroWire.Client
{
    public class ZeroWireException : Exception
    {
        public int ErrorCode { get; }
        public ZeroWireException(int errorCode, string message) : base(message) => ErrorCode = errorCode;
    }

    public class ZeroWireUnknownOffsetException : ZeroWireException
    {
        public ZeroWireUnknownOffsetException() : base(-103, "Handle mismatch: receiver missing dictionary offset handle. Resync required.") { }
    }

    public sealed class ZeroWireEngine : IDisposable
    {
        private IntPtr _handle;
        private bool _disposed;

        public const int ZEROWIRE_OK = 0;
        public const int ZEROWIRE_ERR_INVALID_HANDLE = -1;
        public const int ZEROWIRE_ERR_BUFFER_TOO_SMALL = -2;
        public const int ZEROWIRE_ERR_INVALID_MAGIC = -10;
        public const int ZEROWIRE_ERR_UNKNOWN_OFFSET = -11;
        public const int ZEROWIRE_ERR_CORRUPTED_STREAM = -12;
        public const int ZEROWIRE_ERR_QUOTA_EXCEEDED = -105;
        public const int ZEROWIRE_ERR_AUTH_DENIED = -106;
        public ZeroWireEngine(uint maxMemoryMb = 64, uint sessionTtlSeconds = 3600, string licenseKey = null)
        {
            _handle = NativeMethods.ZeroWire_CreateEngine(maxMemoryMb, sessionTtlSeconds, licenseKey);
            if (_handle == IntPtr.Zero)
                throw new InvalidOperationException("Failed to initialize native ZeroWire engine core (invalid handle or invalid license key).");
        }
        public byte[] Compress(ulong sessionId, byte[] inputData, bool forceResync = false)
        {
            ThrowIfDisposed();
            if (inputData == null || inputData.Length == 0) return Array.Empty<byte>();

            int maxOut = inputData.Length + 128;
            byte[] outputBuffer = new byte[maxOut];

            int result = NativeMethods.ZeroWire_CompressStream(
                _handle, sessionId, inputData, inputData.Length, outputBuffer, maxOut, forceResync);

            if (result < 0)
                ThrowMappedException(result);

            byte[] compressedPayload = new byte[result];
            Buffer.BlockCopy(outputBuffer, 0, compressedPayload, 0, result);
            return compressedPayload;
        }

        public byte[] Decompress(ulong sessionId, byte[] wireBytes, int maxOutputEstimate = 1024 * 1024)
        {
            ThrowIfDisposed();
            if (wireBytes == null || wireBytes.Length == 0) return Array.Empty<byte>();

            byte[] outputBuffer = new byte[maxOutputEstimate];

            int result = NativeMethods.ZeroWire_DecompressStream(
                _handle, sessionId, wireBytes, wireBytes.Length, outputBuffer, maxOutputEstimate);

            if (result == ZEROWIRE_ERR_BUFFER_TOO_SMALL)
            {
                // Double buffer capacity and retry
                maxOutputEstimate *= 4;
                outputBuffer = new byte[maxOutputEstimate];
                result = NativeMethods.ZeroWire_DecompressStream(
                    _handle, sessionId, wireBytes, wireBytes.Length, outputBuffer, maxOutputEstimate);
            }

            if (result < 0)
                ThrowMappedException(result);

            byte[] decompressedPayload = new byte[result];
            Buffer.BlockCopy(outputBuffer, 0, decompressedPayload, 0, result);
            return decompressedPayload;
        }

        public void ResetSession(ulong sessionId)
        {
            ThrowIfDisposed();
            int res = NativeMethods.ZeroWire_ResetSessionState(_handle, sessionId);
            if (res < 0) ThrowMappedException(res);
        }

        public void DestroySession(ulong sessionId)
        {
            ThrowIfDisposed();
            int res = NativeMethods.ZeroWire_DestroySession(_handle, sessionId);
            if (res < 0) ThrowMappedException(res);
        }

        public ulong GetMemoryUsage()
        {
            ThrowIfDisposed();
            return NativeMethods.ZeroWire_GetMemoryUsage(_handle).ToUInt64();
        }

        private static void ThrowMappedException(int errorCode)
        {
            switch (errorCode)
            {
                case ZEROWIRE_ERR_UNKNOWN_OFFSET:
                    throw new ZeroWireUnknownOffsetException();

                case ZEROWIRE_ERR_QUOTA_EXCEEDED:
                    throw new ZeroWireException(errorCode, "Community session quota exceeded (maximum 2 active sessions supported in Community Build).");

                case ZEROWIRE_ERR_AUTH_DENIED:
                    throw new ZeroWireException(errorCode, "Stream configuration authorization failed or session expired.");

                case ZEROWIRE_ERR_INVALID_MAGIC:
                    throw new ZeroWireException(errorCode, "Invalid ZeroWire magic framing header ('Z' 'W' signature mismatch).");

                case ZEROWIRE_ERR_BUFFER_TOO_SMALL:
                    throw new ZeroWireException(errorCode, "Destination output buffer capacity too small.");

                case ZEROWIRE_ERR_CORRUPTED_STREAM:
                    throw new ZeroWireException(errorCode, "Corrupted wire payload stream.");

                default:
                    throw new ZeroWireException(errorCode, $"Native ZeroWire engine failure (Error Code: {errorCode}).");
            }
        }
        private void ThrowIfDisposed()
        {
            if (_disposed) throw new ObjectDisposedException(nameof(ZeroWireEngine));
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                if (_handle != IntPtr.Zero)
                {
                    NativeMethods.ZeroWire_DestroyEngine(_handle);
                    _handle = IntPtr.Zero;
                }
                _disposed = true;
            }
        }
    }
}