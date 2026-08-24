import Foundation

#if canImport(CryptoKit)
import CryptoKit
#endif

/// Calculates the exact SHA-256 identities used by Device Ledger v0 records.
///
/// Apple-platform builds use CryptoKit. Environments where CryptoKit is not
/// available use a closed, dependency-free SHA-256 fallback so the package can
/// run the same parity tests on non-Apple Swift hosts. Both paths hash the exact
/// bytes supplied by the caller without parsing, canonicalizing, normalizing, or
/// otherwise transforming them.
public enum LedgerRecordHasher {
    /// Returns the 32 raw SHA-256 digest bytes for one exact byte sequence.
    public static func sha256Bytes(
        of exactBytes: Data
    ) -> Data {
#if canImport(CryptoKit)
        Data(SHA256.hash(data: exactBytes))
#else
        Data(SHA256Core.hash(exactBytes))
#endif
    }

    /// Returns the lowercase hexadecimal SHA-256 identity for one exact byte
    /// sequence.
    public static func sha256Hex(
        of exactBytes: Data
    ) -> SHA256HexDigest {
        let digestBytes = Array(
            sha256Bytes(of: exactBytes)
        )
        let hex = lowercaseHexString(digestBytes)
        return try! SHA256HexDigest(hex)
    }

    /// Calculates `record_sha256` from the canonical record digest subject.
    ///
    /// `LedgerRecordDigestSubject.canonicalBytes()` contains the complete record
    /// with only its own `record_sha256` field omitted.
    public static func recordSHA256(
        for digestSubject: LedgerRecordDigestSubject
    ) -> SHA256HexDigest {
        sha256Hex(
            of: digestSubject.canonicalBytes()
        )
    }

    /// Calculates and attaches `record_sha256` to one validated digest subject.
    public static func finalize(
        _ digestSubject: LedgerRecordDigestSubject
    ) -> LedgerRecordEnvelope {
        digestSubject.finalized(
            recordSHA256: recordSHA256(
                for: digestSubject
            )
        )
    }

    private static let lowercaseHexDigits: [UInt8] = Array(
        "0123456789abcdef".utf8
    )

    private static func lowercaseHexString(
        _ bytes: [UInt8]
    ) -> String {
        var encoded: [UInt8] = []
        encoded.reserveCapacity(bytes.count * 2)

        for byte in bytes {
            encoded.append(
                lowercaseHexDigits[Int(byte >> 4)]
            )
            encoded.append(
                lowercaseHexDigits[Int(byte & 0x0F)]
            )
        }

        return String(
            decoding: encoded,
            as: UTF8.self
        )
    }
}

#if !canImport(CryptoKit)
private enum SHA256Core {
    private static let initialState: [UInt32] = [
        0x6A09E667,
        0xBB67AE85,
        0x3C6EF372,
        0xA54FF53A,
        0x510E527F,
        0x9B05688C,
        0x1F83D9AB,
        0x5BE0CD19,
    ]

    private static let roundConstants: [UInt32] = [
        0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5,
        0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
        0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
        0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
        0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC,
        0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
        0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7,
        0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
        0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
        0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
        0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3,
        0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
        0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5,
        0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
        0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
        0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
    ]

    static func hash(
        _ exactBytes: Data
    ) -> [UInt8] {
        var message = Array(exactBytes)
        let byteCount = UInt64(message.count)

        precondition(
            byteCount <= UInt64.max / 8,
            "SHA-256 input length exceeds the 64-bit bit-length field"
        )

        let bitLength = byteCount * 8
        message.append(0x80)

        while message.count % 64 != 56 {
            message.append(0x00)
        }

        for shift in stride(
            from: 56,
            through: 0,
            by: -8
        ) {
            message.append(
                UInt8(
                    truncatingIfNeeded: bitLength >> shift
                )
            )
        }

        var state = initialState

        for chunkStart in stride(
            from: 0,
            to: message.count,
            by: 64
        ) {
            var words = [UInt32](
                repeating: 0,
                count: 64
            )

            for index in 0..<16 {
                let offset = chunkStart + index * 4
                words[index] =
                    UInt32(message[offset]) << 24 |
                    UInt32(message[offset + 1]) << 16 |
                    UInt32(message[offset + 2]) << 8 |
                    UInt32(message[offset + 3])
            }

            for index in 16..<64 {
                let sigma0 = rotateRight(
                    words[index - 15],
                    by: 7
                ) ^ rotateRight(
                    words[index - 15],
                    by: 18
                ) ^ (words[index - 15] >> 3)
                let sigma1 = rotateRight(
                    words[index - 2],
                    by: 17
                ) ^ rotateRight(
                    words[index - 2],
                    by: 19
                ) ^ (words[index - 2] >> 10)

                words[index] = words[index - 16]
                    &+ sigma0
                    &+ words[index - 7]
                    &+ sigma1
            }

            var a = state[0]
            var b = state[1]
            var c = state[2]
            var d = state[3]
            var e = state[4]
            var f = state[5]
            var g = state[6]
            var h = state[7]

            for index in 0..<64 {
                let bigSigma1 = rotateRight(
                    e,
                    by: 6
                ) ^ rotateRight(
                    e,
                    by: 11
                ) ^ rotateRight(
                    e,
                    by: 25
                )
                let choose = (e & f) ^ ((~e) & g)
                let temporary1 = h
                    &+ bigSigma1
                    &+ choose
                    &+ roundConstants[index]
                    &+ words[index]
                let bigSigma0 = rotateRight(
                    a,
                    by: 2
                ) ^ rotateRight(
                    a,
                    by: 13
                ) ^ rotateRight(
                    a,
                    by: 22
                )
                let majority = (a & b) ^ (a & c) ^ (b & c)
                let temporary2 = bigSigma0 &+ majority

                h = g
                g = f
                f = e
                e = d &+ temporary1
                d = c
                c = b
                b = a
                a = temporary1 &+ temporary2
            }

            state[0] = state[0] &+ a
            state[1] = state[1] &+ b
            state[2] = state[2] &+ c
            state[3] = state[3] &+ d
            state[4] = state[4] &+ e
            state[5] = state[5] &+ f
            state[6] = state[6] &+ g
            state[7] = state[7] &+ h
        }

        var digest: [UInt8] = []
        digest.reserveCapacity(32)

        for word in state {
            digest.append(
                UInt8(
                    truncatingIfNeeded: word >> 24
                )
            )
            digest.append(
                UInt8(
                    truncatingIfNeeded: word >> 16
                )
            )
            digest.append(
                UInt8(
                    truncatingIfNeeded: word >> 8
                )
            )
            digest.append(
                UInt8(
                    truncatingIfNeeded: word
                )
            )
        }

        return digest
    }

    private static func rotateRight(
        _ value: UInt32,
        by amount: UInt32
    ) -> UInt32 {
        (value >> amount) |
        (value << (32 - amount))
    }
}
#endif
