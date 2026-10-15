using System;
using System.Runtime.InteropServices;

namespace ZeroWire.Client
{
    internal static class NativeMethods
    {
        private const string DllName = "zerowire.dll";

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl, CharSet = CharSet.Ansi)]
        public static extern IntPtr ZeroWire_CreateEngine(
            uint maxMemoryMb,
            uint sessionTtlSeconds,
            [MarshalAs(UnmanagedType.LPStr)] string stream_config_blob);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern void ZeroWire_DestroyEngine(IntPtr handle);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ZeroWire_DestroySession(IntPtr handle, ulong sessionId);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ZeroWire_ResetSessionState(IntPtr handle, ulong sessionId);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern UIntPtr ZeroWire_GetMemoryUsage(IntPtr handle);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ZeroWire_CompressStream(
            IntPtr handle,
            ulong sessionId,
            [In] byte[] input,
            int inputLen,
            [In, Out] byte[] output,
            int maxOut,
            [MarshalAs(UnmanagedType.I1)] bool forceResync);

        [DllImport(DllName, CallingConvention = CallingConvention.Cdecl)]
        public static extern int ZeroWire_DecompressStream(
            IntPtr handle,
            ulong sessionId,
            [In] byte[] input,
            int inputLen,
            [In, Out] byte[] output,
            int maxOut);
    }
}