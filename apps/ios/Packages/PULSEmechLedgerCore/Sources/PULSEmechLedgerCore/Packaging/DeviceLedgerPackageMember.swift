import Foundation

/// Fail-closed identity errors for the five fixed contract and schema members
/// consumed by Device Ledger v0 manifest materialization.
public enum DeviceLedgerManifestContractMembersError:
    Error,
    Sendable,
    Equatable
{
    case staticMemberIdentityMismatch(path: String)
}

/// Exact bytes of the five repository-bound contract and schema members that
/// participate in one Device Ledger v0 payload inventory.
///
/// Construction verifies both byte count and SHA-256 for every member. The
/// caller supplies bytes only; package path, semantic role, media type, and
/// expected identity remain closed implementation values.
public struct DeviceLedgerManifestContractMembers:
    Sendable,
    Equatable
{
    public let canonicalizationProfileBytes: Data
    public let observationContractBytes: Data
    public let manifestSchemaBytes: Data
    public let signatureSchemaBytes: Data
    public let transitionLedgerSchemaBytes: Data

    public init(
        canonicalizationProfileBytes: Data,
        observationContractBytes: Data,
        manifestSchemaBytes: Data,
        signatureSchemaBytes: Data,
        transitionLedgerSchemaBytes: Data
    ) throws {
        self.canonicalizationProfileBytes = try Self.validate(
            canonicalizationProfileBytes,
            kind: .canonicalizationProfile
        )
        self.observationContractBytes = try Self.validate(
            observationContractBytes,
            kind: .observationContract
        )
        self.manifestSchemaBytes = try Self.validate(
            manifestSchemaBytes,
            kind: .manifestSchema
        )
        self.signatureSchemaBytes = try Self.validate(
            signatureSchemaBytes,
            kind: .signatureSchema
        )
        self.transitionLedgerSchemaBytes = try Self.validate(
            transitionLedgerSchemaBytes,
            kind: .transitionLedgerSchema
        )
    }

    func exactBytes(
        for kind: DeviceLedgerManifestPayloadMemberKind
    ) -> Data? {
        switch kind {
        case .canonicalizationProfile:
            canonicalizationProfileBytes
        case .observationContract:
            observationContractBytes
        case .manifestSchema:
            manifestSchemaBytes
        case .signatureSchema:
            signatureSchemaBytes
        case .transitionLedgerSchema:
            transitionLedgerSchemaBytes
        case .observerPublicKey,
             .transitionLedger,
             .checkpointSignature:
            nil
        }
    }

    private static func validate(
        _ exactBytes: Data,
        kind: DeviceLedgerManifestPayloadMemberKind
    ) throws -> Data {
        guard let expected = kind.spec.expectedStaticIdentity else {
            preconditionFailure(
                "Dynamic payload member passed to static-member validation"
            )
        }

        let observedSize = Int64(exactBytes.count)
        let observedSHA256 = LedgerRecordHasher.sha256Hex(
            of: exactBytes
        )

        guard observedSize == expected.sizeBytes,
              observedSHA256 == expected.sha256 else {
            throw DeviceLedgerManifestContractMembersError
                .staticMemberIdentityMismatch(
                    path: kind.spec.path
                )
        }

        return Data(exactBytes)
    }
}

/// Fail-closed byte-boundary errors for one exact manifest payload member.
public enum DeviceLedgerPayloadMemberError:
    Error,
    Sendable,
    Equatable
{
    case emptyMember(path: String)
    case memberExceedsCarrierLimit(path: String)
    case staticMemberIdentityMismatch(path: String)
}

/// One exact byte member in the ordered Device Ledger v0 manifest inventory.
///
/// The initializer is module-internal so external clients cannot assign a
/// package path, role, or media type. Public access is read-only and retains the
/// exact bytes needed by the later package-assembly layer.
public struct DeviceLedgerPayloadMember:
    Sendable,
    Equatable
{
    public static let maximumSizeBytes: Int64 = 16_777_216

    public let path: String
    public let role: String
    public let mediaType: String
    public let exactBytes: Data
    public let sha256: SHA256HexDigest
    public let sizeBytes: Int64

    init(
        kind: DeviceLedgerManifestPayloadMemberKind,
        exactBytes: Data
    ) throws {
        let spec = kind.spec
        let sizeBytes = Int64(exactBytes.count)

        guard sizeBytes > 0 else {
            throw DeviceLedgerPayloadMemberError.emptyMember(
                path: spec.path
            )
        }
        guard sizeBytes <= Self.maximumSizeBytes else {
            throw DeviceLedgerPayloadMemberError
                .memberExceedsCarrierLimit(
                    path: spec.path
                )
        }

        let sha256 = LedgerRecordHasher.sha256Hex(
            of: exactBytes
        )
        if let expected = spec.expectedStaticIdentity {
            guard sizeBytes == expected.sizeBytes,
                  sha256 == expected.sha256 else {
                throw DeviceLedgerPayloadMemberError
                    .staticMemberIdentityMismatch(
                        path: spec.path
                    )
            }
        }

        path = spec.path
        role = spec.role
        mediaType = spec.mediaType
        self.exactBytes = Data(exactBytes)
        self.sha256 = sha256
        self.sizeBytes = sizeBytes
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            manifestPayloadMember(
                "byte_identity",
                manifestPayloadString("exact_member_bytes")
            ),
            manifestPayloadMember(
                "media_type",
                manifestPayloadString(mediaType)
            ),
            manifestPayloadMember(
                "path",
                manifestPayloadString(path)
            ),
            manifestPayloadMember(
                "role",
                manifestPayloadString(role)
            ),
            manifestPayloadMember(
                "sha256",
                sha256.canonicalValue
            ),
            manifestPayloadMember(
                "size_bytes",
                .integer(sizeBytes)
            ),
        ])
    }
}

enum DeviceLedgerManifestPayloadMemberKind:
    Int,
    CaseIterable,
    Sendable
{
    case canonicalizationProfile
    case observationContract
    case observerPublicKey
    case transitionLedger
    case manifestSchema
    case signatureSchema
    case transitionLedgerSchema
    case checkpointSignature

    var spec: DeviceLedgerManifestPayloadMemberSpec {
        switch self {
        case .canonicalizationProfile:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "contracts/pulsemech_device_canonical_json_v0.json",
                role: "canonicalization_profile",
                mediaType: "application/json",
                expectedStaticIdentity:
                    DeviceLedgerManifestStaticIdentity(
                        sizeBytes: 2_719,
                        sha256: try! SHA256HexDigest(
                            "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550"
                        )
                    )
            )
        case .observationContract:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "contracts/pulsemech_ios_observation_contract_v0.json",
                role: "ios_observation_contract",
                mediaType: "application/json",
                expectedStaticIdentity:
                    DeviceLedgerManifestStaticIdentity(
                        sizeBytes: 9_893,
                        sha256: try! SHA256HexDigest(
                            "e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2"
                        )
                    )
            )
        case .observerPublicKey:
            DeviceLedgerManifestPayloadMemberSpec(
                path: "keys/observer-public-key-v0.bin",
                role: "observer_public_key",
                mediaType: "application/octet-stream",
                expectedStaticIdentity: nil
            )
        case .transitionLedger:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "ledger/pulsemech_device_transition_ledger_v0.json",
                role: "transition_ledger",
                mediaType: "application/json",
                expectedStaticIdentity: nil
            )
        case .manifestSchema:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "schemas/pulsemech_device_ledger_manifest_v0.schema.json",
                role: "ledger_manifest_schema",
                mediaType: "application/schema+json",
                expectedStaticIdentity:
                    DeviceLedgerManifestStaticIdentity(
                        sizeBytes: 19_913,
                        sha256: try! SHA256HexDigest(
                            "bf8126db9a9c5c40f1dbe3ad835ae7711a98d77fa8b3a59016f4ebd406d0ce3d"
                        )
                    )
            )
        case .signatureSchema:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "schemas/pulsemech_device_signature_v0.schema.json",
                role: "signature_schema",
                mediaType: "application/schema+json",
                expectedStaticIdentity:
                    DeviceLedgerManifestStaticIdentity(
                        sizeBytes: 5_031,
                        sha256: try! SHA256HexDigest(
                            "80304b08b73f3c05092909e7917240af94121e2c15b9305440a7e01460c049c0"
                        )
                    )
            )
        case .transitionLedgerSchema:
            DeviceLedgerManifestPayloadMemberSpec(
                path:
                    "schemas/pulsemech_device_transition_ledger_v0.schema.json",
                role: "transition_ledger_schema",
                mediaType: "application/schema+json",
                expectedStaticIdentity:
                    DeviceLedgerManifestStaticIdentity(
                        sizeBytes: 54_069,
                        sha256: try! SHA256HexDigest(
                            "58eddf75d9c89fef4aa3787e3e4db4d86624f4a387b2a33a3c2fd1f972d6c07f"
                        )
                    )
            )
        case .checkpointSignature:
            DeviceLedgerManifestPayloadMemberSpec(
                path: "signatures/checkpoint-signature-v0.json",
                role: "checkpoint_signature",
                mediaType: "application/json",
                expectedStaticIdentity: nil
            )
        }
    }
}

struct DeviceLedgerManifestPayloadMemberSpec:
    Sendable,
    Equatable
{
    let path: String
    let role: String
    let mediaType: String
    let expectedStaticIdentity: DeviceLedgerManifestStaticIdentity?
}

struct DeviceLedgerManifestStaticIdentity:
    Sendable,
    Equatable
{
    let sizeBytes: Int64
    let sha256: SHA256HexDigest
}

private func manifestPayloadMember(
    _ key: String,
    _ value: CanonicalJSONValue
) -> CanonicalJSONObjectMember {
    try! CanonicalJSONObjectMember(
        key: key,
        value: value
    )
}

private func manifestPayloadString(
    _ value: String
) -> CanonicalJSONValue {
    .string(try! CanonicalJSONString(value))
}
