import Foundation

/// Errors raised while constructing the closed PULSEmech Device Ledger v0
/// JSON value domain.
public enum CanonicalJSONValueError: Error, Sendable, Equatable {
    /// A string contains at least one scalar outside the v0 ASCII ledger
    /// domain.
    case nonASCIIString

    /// An object contains more than one member with the same normalized key.
    ///
    /// The v0 ledger domain is ASCII-only, so NFC normalization cannot change
    /// a key and normalized-key equality is exact string equality.
    case duplicateObjectKey(String)
}

/// A validated string in the PULSEmech Device Ledger v0 signed-document
/// domain.
///
/// The v0 ledger contract restricts signed-document strings to ASCII. ASCII is
/// a strict subset of the canonical JSON profile's Unicode 14.0.0 domain and is
/// already NFC-normalized.
///
/// This prevents the Swift producer from silently depending on the Unicode
/// normalization version supplied by the current Apple runtime.
public struct CanonicalJSONString: Sendable, Hashable {
    public let value: String

    public init(_ value: String) throws {
        guard value.unicodeScalars.allSatisfy({ $0.value <= 0x7F }) else {
            throw CanonicalJSONValueError.nonASCIIString
        }

        self.value = value
    }

    var utf8Bytes: [UInt8] {
        Array(value.utf8)
    }
}

/// One key/value member of a canonical JSON object.
public struct CanonicalJSONObjectMember: Sendable, Equatable {
    public let key: CanonicalJSONString
    public let value: CanonicalJSONValue

    public init(
        key: CanonicalJSONString,
        value: CanonicalJSONValue
    ) {
        self.key = key
        self.value = value
    }

    public init(
        key: String,
        value: CanonicalJSONValue
    ) throws {
        self.init(
            key: try CanonicalJSONString(key),
            value: value
        )
    }
}

/// A duplicate-free canonical JSON object whose members are retained in
/// canonical key order.
public struct CanonicalJSONObject: Sendable, Equatable {
    public let members: [CanonicalJSONObjectMember]

    public init(
        _ members: [CanonicalJSONObjectMember]
    ) throws {
        var observedKeys = Set<CanonicalJSONString>()

        for member in members {
            guard observedKeys.insert(member.key).inserted else {
                throw CanonicalJSONValueError.duplicateObjectKey(
                    member.key.value
                )
            }
        }

        self.members = members.sorted { left, right in
            left.key.utf8Bytes.lexicographicallyPrecedes(
                right.key.utf8Bytes
            )
        }
    }
}

/// Closed JSON value domain used by the PULSEmech Device Ledger v0 producer.
///
/// Floating-point values, non-finite numbers, arbitrary Foundation JSON values,
/// and unordered dictionaries are intentionally unrepresentable.
///
/// Arrays retain caller order. Objects reject duplicate keys and store members
/// in ascending unsigned lexicographic UTF-8 key order.
public indirect enum CanonicalJSONValue: Sendable, Equatable {
    case null
    case boolean(Bool)
    case integer(Int64)
    case string(CanonicalJSONString)
    case array([CanonicalJSONValue])
    case object(CanonicalJSONObject)

    /// Constructs one validated v0 ASCII string value.
    public static func string(
        _ value: String
    ) throws -> CanonicalJSONValue {
        .string(
            try CanonicalJSONString(value)
        )
    }

    /// Constructs one duplicate-free, canonically ordered object value.
    public static func object(
        _ members: [CanonicalJSONObjectMember]
    ) throws -> CanonicalJSONValue {
        .object(
            try CanonicalJSONObject(members)
        )
    }
}
