import Foundation

/// Fail-closed validation errors for one fixed-width Device Ledger v0
/// ECDSA P-256 signature.
public enum DeviceP256SignatureError: Error, Sendable, Equatable {
    case signatureSizeInvalid
    case rScalarZero
    case rScalarOutOfRange
    case sScalarZero
    case sScalarOutOfRange
    case highSForbidden
}

/// One exact 64-byte IEEE P1363 ECDSA P-256 signature.
///
/// Construction enforces the signature contract required by
/// `pulsemech_device_signature_v0`:
///
/// - 32-byte big-endian `r`;
/// - 32-byte big-endian `s`;
/// - both scalars in `1 ... n - 1`;
/// - mandatory low-S form.
///
/// This value validates signature shape and scalar canonicality. The signer
/// boundary is responsible for producing a signature over the supplied digest;
/// the separately implemented package verifier reconstructs and verifies the
/// ECDSA equation.
public struct DeviceP256Signature: Sendable, Equatable {
    public static let byteCount = 64

    public let ieeeP1363FixedWidth: Data

    public init(
        ieeeP1363FixedWidth: Data
    ) throws {
        guard ieeeP1363FixedWidth.count == Self.byteCount else {
            throw DeviceP256SignatureError.signatureSizeInvalid
        }

        let bytes = Array(ieeeP1363FixedWidth)
        let r = Array(bytes[0..<32])
        let s = Array(bytes[32..<64])

        guard !Self.isZero(r) else {
            throw DeviceP256SignatureError.rScalarZero
        }
        guard Self.compare(r, Self.curveOrder) < 0 else {
            throw DeviceP256SignatureError.rScalarOutOfRange
        }
        guard !Self.isZero(s) else {
            throw DeviceP256SignatureError.sScalarZero
        }
        guard Self.compare(s, Self.curveOrder) < 0 else {
            throw DeviceP256SignatureError.sScalarOutOfRange
        }
        guard Self.compare(s, Self.halfCurveOrder) <= 0 else {
            throw DeviceP256SignatureError.highSForbidden
        }

        self.ieeeP1363FixedWidth = Data(ieeeP1363FixedWidth)
    }

    /// Canonical RFC 4648 Base64 for the exact 64 stored bytes.
    public var canonicalBase64: String {
        ieeeP1363FixedWidth.base64EncodedString()
    }

    public var rBytes: Data {
        Data(ieeeP1363FixedWidth.prefix(32))
    }

    public var sBytes: Data {
        Data(ieeeP1363FixedWidth.suffix(32))
    }

    private static let curveOrder: [UInt8] = [
        0xFF, 0xFF, 0xFF, 0xFF,
        0x00, 0x00, 0x00, 0x00,
        0xFF, 0xFF, 0xFF, 0xFF,
        0xFF, 0xFF, 0xFF, 0xFF,
        0xBC, 0xE6, 0xFA, 0xAD,
        0xA7, 0x17, 0x9E, 0x84,
        0xF3, 0xB9, 0xCA, 0xC2,
        0xFC, 0x63, 0x25, 0x51,
    ]

    private static let halfCurveOrder: [UInt8] = [
        0x7F, 0xFF, 0xFF, 0xFF,
        0x80, 0x00, 0x00, 0x00,
        0x7F, 0xFF, 0xFF, 0xFF,
        0xFF, 0xFF, 0xFF, 0xFF,
        0xDE, 0x73, 0x7D, 0x56,
        0xD3, 0x8B, 0xCF, 0x42,
        0x79, 0xDC, 0xE5, 0x61,
        0x7E, 0x31, 0x92, 0xA8,
    ]

    private static func isZero(
        _ bytes: [UInt8]
    ) -> Bool {
        bytes.allSatisfy { $0 == 0 }
    }

    /// Unsigned big-endian lexical comparison.
    private static func compare(
        _ left: [UInt8],
        _ right: [UInt8]
    ) -> Int {
        precondition(left.count == right.count)

        for index in left.indices {
            if left[index] < right[index] {
                return -1
            }
            if left[index] > right[index] {
                return 1
            }
        }
        return 0
    }
}
