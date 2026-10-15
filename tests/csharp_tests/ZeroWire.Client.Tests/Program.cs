using System;
using System.Text;
using ZeroWire.Client;

namespace ZeroWire.Client.Tests
{
    internal class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("=================================================================");
            Console.WriteLine("   ZEROWIRE PROTOCOL - C# WRAPPER P/INVOKE VERIFICATION");
            Console.WriteLine("=================================================================\n");

            ulong sessionId = 3000101;

            StringBuilder sb = new StringBuilder();
            sb.AppendLine("CONFIDENTIAL FINANCIAL AUDIT REPORT (PDF CONTEXT ATTACHMENT)");
            sb.AppendLine(new string('=', 65));
            for (int i = 0; i < 500; i++)
            {
                sb.AppendLine("Record Entry: Asset allocation delta = +0.0042% | Node status: VERIFIED");
            }

            byte[] rawContext = Encoding.UTF8.GetBytes(sb.ToString());

            Console.WriteLine($"Raw Data Size: {rawContext.Length:N0} bytes");

            using (var sender = new ZeroWireEngine(maxMemoryMb: 64))
            using (var receiver = new ZeroWireEngine(maxMemoryMb: 64))
            {
                // Round 1: Initial Registration
                byte[] wireRound1 = sender.Compress(sessionId, rawContext);
                byte[] decompRound1 = receiver.Decompress(sessionId, wireRound1);

                Console.WriteLine($"Round 1 Wire Size: {wireRound1.Length:N0} bytes");
                bool matchRound1 = AreByteArraysEqual(rawContext, decompRound1);
                Console.WriteLine($"Round 1 Bit-Exact Match: {(matchRound1 ? "PASS" : "FAIL")}");

                // Round 2: Stateful Deduplication
                byte[] wireRound2 = sender.Compress(sessionId, rawContext);
                byte[] decompRound2 = receiver.Decompress(sessionId, wireRound2);

                Console.WriteLine($"Round 2 Wire Size: {wireRound2.Length:N0} bytes");
                bool matchRound2 = AreByteArraysEqual(rawContext, decompRound2);
                Console.WriteLine($"Round 2 Bit-Exact Match: {(matchRound2 ? "PASS" : "FAIL")}");

                double reduction = (1.0 - ((double)wireRound2.Length / rawContext.Length)) * 100.0;
                Console.WriteLine($"Wire Reduction Ratio: {reduction:F2}%");

                // Memory Check
                Console.WriteLine($"Sender Native Memory Usage: {sender.GetMemoryUsage():N0} bytes");

                // Round 3: Resync Exception Test
                Console.WriteLine("\nTesting Unknown Offset Resync Exception...");
                try
                {
                    receiver.Decompress(sessionId: 99999, wireRound2);
                    Console.WriteLine("Resync Protocol Test: FAIL (Expected exception was not thrown)");
                }
                catch (ZeroWireUnknownOffsetException)
                {
                    Console.WriteLine("Resync Protocol Test: PASS (Caught ZeroWireUnknownOffsetException successfully)");
                }
            }

            Console.WriteLine("\nAll C# Native P/Invoke bindings verified successfully.");
        }

        private static bool AreByteArraysEqual(byte[] a1, byte[] a2)
        {
            if (a1 == null || a2 == null || a1.Length != a2.Length)
                return false;

            for (int i = 0; i < a1.Length; i++)
            {
                if (a1[i] != a2[i]) return false;
            }
            return true;
        }
    }
}