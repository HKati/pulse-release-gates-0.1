import Foundation

/// Fail-closed construction errors for one canonical Device Ledger v0 package
/// manifest.
public enum DeviceLedgerManifestError:
    Error,
    Sendable,
    Equatable
{
    case negativeCreatedTime
    case invalidRecordCount
    case payloadInventoryMismatch
    case ledgerMemberBindingMismatch
    case observerMemberBindingMismatch
    case checkpointSignatureMemberBindingMismatch
}

/// Canonical Device Ledger v0 package manifest.
///
/// The manifest inventories exactly eight payload members. It deliberately
/// excludes its own bytes and the later package-signature document to avoid a
/// circular digest relation.
public struct DeviceLedgerManifest:
    Sendable,
    Equatable
{
    public static let manifestPath =
        "manifest/pulsemech_device_ledger_manifest_v0.json"
    public static let packageSignaturePath =
        "signatures/package-signature-v0.json"
    public static let maximumCarrierBytes: Int64 = 33_554_432
    public static let maximumTotalUncompressedBytes: Int64 = 33_554_432

    public let createdUnixNS: Int64
    public let ledgerID: LedgerIdentifier
    public let recordStatus: LedgerRecordStatus
    public let ledgerSHA256: SHA256HexDigest
    public let ledgerSizeBytes: Int64
    public let recordCount: Int64
    public let checkpointRecordSHA256: SHA256HexDigest
    public let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public let checkpointSignatureDocumentSHA256: SHA256HexDigest
    public let checkpointSignatureDocumentSizeBytes: Int64
    public let payloadMembers: [DeviceLedgerPayloadMember]

    init(
        createdUnixNS: Int64,
        ledgerID: LedgerIdentifier,
        recordStatus: LedgerRecordStatus,
        ledgerSHA256: SHA256HexDigest,
        ledgerSizeBytes: Int64,
        recordCount: Int64,
        checkpointRecordSHA256: SHA256HexDigest,
        observerPublicKeyFingerprintSHA256: SHA256HexDigest,
        checkpointSignatureDocumentSHA256: SHA256HexDigest,
        checkpointSignatureDocumentSizeBytes: Int64,
        payloadMembers: [DeviceLedgerPayloadMember]
    ) throws {
        guard createdUnixNS >= 0 else {
            throw DeviceLedgerManifestError.negativeCreatedTime
        }
        guard recordCount > 0 else {
            throw DeviceLedgerManifestError.invalidRecordCount
        }

        let expectedKinds = DeviceLedgerManifestPayloadMemberKind.allCases
        guard payloadMembers.count == expectedKinds.count else {
            throw DeviceLedgerManifestError.payloadInventoryMismatch
        }

        for (member, kind) in zip(payloadMembers, expectedKinds) {
            let spec = kind.spec
            guard member.path == spec.path,
                  member.role == spec.role,
                  member.mediaType == spec.mediaType else {
                throw DeviceLedgerManifestError.payloadInventoryMismatch
            }
        }

        let ledgerMember = payloadMembers[
            DeviceLedgerManifestPayloadMemberKind.transitionLedger.rawValue
        ]
        guard ledgerMember.sha256 == ledgerSHA256,
              ledgerMember.sizeBytes == ledgerSizeBytes else {
            throw DeviceLedgerManifestError
                .ledgerMemberBindingMismatch
        }

        let observerMember = payloadMembers[
            DeviceLedgerManifestPayloadMemberKind.observerPublicKey.rawValue
        ]
        guard observerMember.sha256 ==
                observerPublicKeyFingerprintSHA256,
              observerMember.sizeBytes == 65 else {
            throw DeviceLedgerManifestError
                .observerMemberBindingMismatch
        }

        let checkpointSignatureMember = payloadMembers[
            DeviceLedgerManifestPayloadMemberKind
                .checkpointSignature
                .rawValue
        ]
        guard checkpointSignatureMember.sha256 ==
                checkpointSignatureDocumentSHA256,
              checkpointSignatureMember.sizeBytes ==
                checkpointSignatureDocumentSizeBytes else {
            throw DeviceLedgerManifestError
                .checkpointSignatureMemberBindingMismatch
        }

        self.createdUnixNS = createdUnixNS
        self.ledgerID = ledgerID
        self.recordStatus = recordStatus
        self.ledgerSHA256 = ledgerSHA256
        self.ledgerSizeBytes = ledgerSizeBytes
        self.recordCount = recordCount
        self.checkpointRecordSHA256 = checkpointRecordSHA256
        self.observerPublicKeyFingerprintSHA256 =
            observerPublicKeyFingerprintSHA256
        self.checkpointSignatureDocumentSHA256 =
            checkpointSignatureDocumentSHA256
        self.checkpointSignatureDocumentSizeBytes =
            checkpointSignatureDocumentSizeBytes
        self.payloadMembers = payloadMembers
    }

    /// Exact canonical manifest value.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "authority_boundary",
                authorityBoundaryValue()
            ),
            manifestDocumentMember(
                "carrier_contract",
                carrierContractValue()
            ),
            manifestDocumentMember(
                "claim_boundary",
                claimBoundaryValue()
            ),
            manifestDocumentMember(
                "created_unix_ns",
                .integer(createdUnixNS)
            ),
            manifestDocumentMember(
                "document_type",
                manifestDocumentString(
                    "pulsemech_device_ledger_manifest"
                )
            ),
            manifestDocumentMember(
                "ledger_binding",
                ledgerBindingValue()
            ),
            manifestDocumentMember(
                "manifest_contract",
                manifestContractValue()
            ),
            manifestDocumentMember(
                "observer_binding",
                observerBindingValue()
            ),
            manifestDocumentMember(
                "package_format",
                manifestDocumentString("pulseledger_zip_v0")
            ),
            manifestDocumentMember(
                "package_member_count",
                .integer(10)
            ),
            manifestDocumentMember(
                "payload_member_count",
                .integer(8)
            ),
            manifestDocumentMember(
                "payload_members",
                .array(
                    payloadMembers.map {
                        $0.canonicalValue()
                    }
                )
            ),
            manifestDocumentMember(
                "record_status",
                manifestDocumentString(recordStatus.rawValue)
            ),
            manifestDocumentMember(
                "reference_device_class",
                manifestDocumentString("iphone")
            ),
            manifestDocumentMember(
                "reference_platform",
                manifestDocumentString("ios")
            ),
            manifestDocumentMember(
                "schema_version",
                manifestDocumentString(
                    "pulsemech_device_ledger_manifest_v0"
                )
            ),
            manifestDocumentMember(
                "signature_contract",
                signatureContractValue()
            ),
        ])
    }

    /// Exact canonical manifest bytes with no BOM, insignificant whitespace, or
    /// trailing newline.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    /// SHA-256 over the exact canonical manifest bytes. This digest becomes the
    /// signed object of the later package-signature layer.
    public var manifestSHA256: SHA256HexDigest {
        LedgerRecordHasher.sha256Hex(
            of: canonicalBytes()
        )
    }

    public var sizeBytes: Int64 {
        Int64(canonicalBytes().count)
    }

    private func authorityBoundaryValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "authority_effect",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "changes_release_authority",
                .boolean(false)
            ),
            manifestDocumentMember(
                "creates_device_control_authority",
                .boolean(false)
            ),
            manifestDocumentMember(
                "creates_release_decision",
                .boolean(false)
            ),
        ])
    }

    private func claimBoundaryValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "causal_completion_claim",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "continuous_monitoring_claim",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "device_security_claim",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "external_validation_claim",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "malware_claim",
                manifestDocumentString("none")
            ),
            manifestDocumentMember(
                "physical_measurement_claim",
                manifestDocumentString("none")
            ),
        ])
    }

    private func carrierContractValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "archive_comment",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "archive_format",
                manifestDocumentString("zip")
            ),
            manifestDocumentMember(
                "archive_member_set",
                manifestDocumentString(
                    "exact_payload_paths_plus_manifest_and_package_signature"
                )
            ),
            manifestDocumentMember(
                "carrier_identity_location",
                manifestDocumentString("verifier_report_only")
            ),
            manifestDocumentMember(
                "compression_method",
                manifestDocumentString("stored")
            ),
            manifestDocumentMember(
                "crc32",
                manifestDocumentString("required_and_verified")
            ),
            manifestDocumentMember(
                "data_descriptors",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "directory_entries",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "duplicate_member_names",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "encrypted_members",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "extra_fields",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "file_extension",
                manifestDocumentString(".pulseledger")
            ),
            manifestDocumentMember(
                "local_central_directory_consistency",
                manifestDocumentString("required")
            ),
            manifestDocumentMember(
                "max_carrier_bytes",
                .integer(Self.maximumCarrierBytes)
            ),
            manifestDocumentMember(
                "max_member_bytes",
                .integer(
                    DeviceLedgerPayloadMember.maximumSizeBytes
                )
            ),
            manifestDocumentMember(
                "max_total_uncompressed_bytes",
                .integer(Self.maximumTotalUncompressedBytes)
            ),
            manifestDocumentMember(
                "member_comments",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "member_name_encoding",
                manifestDocumentString("ASCII")
            ),
            manifestDocumentMember(
                "member_name_policy",
                manifestDocumentString(
                    "relative_posix_no_dot_segments_no_backslash_no_nul"
                )
            ),
            manifestDocumentMember(
                "member_order_semantics",
                manifestDocumentString(
                    "not_authority_bearing_exact_carrier_hash_records_instance_order"
                )
            ),
            manifestDocumentMember(
                "non_regular_members",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "symlinks",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "timestamp_policy",
                manifestDocumentString(
                    "fixed_1980_01_01_00_00_00"
                )
            ),
            manifestDocumentMember(
                "trailing_data",
                manifestDocumentString("forbidden")
            ),
            manifestDocumentMember(
                "zip64",
                manifestDocumentString("forbidden")
            ),
        ])
    }

    private func ledgerBindingValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "checkpoint_record_sha256",
                checkpointRecordSHA256.canonicalValue
            ),
            manifestDocumentMember(
                "ledger_id",
                ledgerID.canonicalValue
            ),
            manifestDocumentMember(
                "ledger_member_path",
                manifestDocumentString(
                    "ledger/pulsemech_device_transition_ledger_v0.json"
                )
            ),
            manifestDocumentMember(
                "ledger_schema_member_path",
                manifestDocumentString(
                    "schemas/pulsemech_device_transition_ledger_v0.schema.json"
                )
            ),
            manifestDocumentMember(
                "ledger_schema_sha256",
                DeviceLedgerManifestPayloadMemberKind
                    .transitionLedgerSchema
                    .spec
                    .expectedStaticIdentity!
                    .sha256
                    .canonicalValue
            ),
            manifestDocumentMember(
                "ledger_sha256",
                ledgerSHA256.canonicalValue
            ),
            manifestDocumentMember(
                "ledger_size_bytes",
                .integer(ledgerSizeBytes)
            ),
            manifestDocumentMember(
                "record_count",
                .integer(recordCount)
            ),
            manifestDocumentMember(
                "terminal_record_sha256",
                checkpointRecordSHA256.canonicalValue
            ),
        ])
    }

    private func manifestContractValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "canonicalization",
                manifestDocumentString(
                    "pulsemech_device_canonical_json_v0"
                )
            ),
            manifestDocumentMember(
                "digest_algorithm",
                manifestDocumentString("SHA-256")
            ),
            manifestDocumentMember(
                "digest_subject",
                manifestDocumentString(
                    "exact_canonical_manifest_bytes"
                )
            ),
            manifestDocumentMember(
                "manifest_path",
                manifestDocumentString(Self.manifestPath)
            ),
            manifestDocumentMember(
                "manifest_self_inventory",
                manifestDocumentString(
                    "excluded_to_avoid_circularity"
                )
            ),
            manifestDocumentMember(
                "package_signature_inventory",
                manifestDocumentString(
                    "excluded_to_avoid_circularity"
                )
            ),
            manifestDocumentMember(
                "package_signature_path",
                manifestDocumentString(Self.packageSignaturePath)
            ),
        ])
    }

    private func observerBindingValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "fingerprint_algorithm",
                manifestDocumentString("SHA-256")
            ),
            manifestDocumentMember(
                "fingerprint_subject",
                manifestDocumentString(
                    "exact_65_byte_x963_uncompressed_public_key"
                )
            ),
            manifestDocumentMember(
                "observer_public_key_fingerprint_sha256",
                observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            manifestDocumentMember(
                "public_key_encoding",
                manifestDocumentString("x963_uncompressed")
            ),
            manifestDocumentMember(
                "public_key_member_path",
                manifestDocumentString(
                    "keys/observer-public-key-v0.bin"
                )
            ),
            manifestDocumentMember(
                "public_key_size_bytes",
                .integer(65)
            ),
            manifestDocumentMember(
                "signature_suite",
                manifestDocumentString("ecdsa-p256-sha256")
            ),
        ])
    }

    private func signatureContractValue() -> CanonicalJSONValue {
        try! .object([
            manifestDocumentMember(
                "checkpoint_signature_path",
                manifestDocumentString(
                    "signatures/checkpoint-signature-v0.json"
                )
            ),
            manifestDocumentMember(
                "checkpoint_signed_object_type",
                manifestDocumentString(
                    "checkpoint_record_sha256"
                )
            ),
            manifestDocumentMember(
                "package_signature_path",
                manifestDocumentString(Self.packageSignaturePath)
            ),
            manifestDocumentMember(
                "package_signature_subject",
                manifestDocumentString(
                    "SHA-256_of_exact_canonical_manifest_bytes"
                )
            ),
            manifestDocumentMember(
                "package_signed_object_type",
                manifestDocumentString(
                    "ledger_manifest_sha256"
                )
            ),
            manifestDocumentMember(
                "signature_schema_member_path",
                manifestDocumentString(
                    "schemas/pulsemech_device_signature_v0.schema.json"
                )
            ),
            manifestDocumentMember(
                "signature_schema_sha256",
                DeviceLedgerManifestPayloadMemberKind
                    .signatureSchema
                    .spec
                    .expectedStaticIdentity!
                    .sha256
                    .canonicalValue
            ),
            manifestDocumentMember(
                "signature_suite",
                manifestDocumentString("ecdsa-p256-sha256")
            ),
        ])
    }
}

private func manifestDocumentMember(
    _ key: String,
    _ value: CanonicalJSONValue
) -> CanonicalJSONObjectMember {
    try! CanonicalJSONObjectMember(
        key: key,
        value: value
    )
}

private func manifestDocumentString(
    _ value: String
) -> CanonicalJSONValue {
    .string(try! CanonicalJSONString(value))
}
