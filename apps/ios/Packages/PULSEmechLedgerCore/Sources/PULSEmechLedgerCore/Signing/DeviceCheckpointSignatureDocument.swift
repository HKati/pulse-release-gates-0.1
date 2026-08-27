import Foundation

/// The exact four-field canonical subject bound by one Device Ledger v0
/// checkpoint signature.
public struct DeviceCheckpointSignatureSubject: Sendable, Equatable {
    public static let signatureDomain =
        "PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0"
    public static let signatureSuite = "ecdsa-p256-sha256"

    public let ledgerID: LedgerIdentifier
    public let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public let signedObjectSHA256: SHA256HexDigest

    public init(
        ledgerID: LedgerIdentifier,
        observerPublicKeyFingerprintSHA256: SHA256HexDigest,
        signedObjectSHA256: SHA256HexDigest
    ) {
        self.ledgerID = ledgerID
        self.observerPublicKeyFingerprintSHA256 =
            observerPublicKeyFingerprintSHA256
        self.signedObjectSHA256 = signedObjectSHA256
    }

    /// Exact canonical subject reconstructed by the standalone verifier.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            checkpointSignatureMember(
                "ledger_id",
                ledgerID.canonicalValue
            ),
            checkpointSignatureMember(
                "observer_public_key_fingerprint_sha256",
                observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            checkpointSignatureMember(
                "signature_suite",
                checkpointSignatureString(Self.signatureSuite)
            ),
            checkpointSignatureMember(
                "signed_object_sha256",
                signedObjectSHA256.canonicalValue
            ),
        ])
    }

    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    /// Exact framing:
    ///
    /// `ASCII(domain) || 0x00 || canonical_subject_json`.
    public func framedBytes() -> Data {
        var output = Data(Self.signatureDomain.utf8)
        output.append(0x00)
        output.append(canonicalBytes())
        return output
    }

    /// The exact 32-byte digest supplied to the observer signer.
    public var signatureInputSHA256: Data {
        LedgerRecordHasher.sha256Bytes(
            of: framedBytes()
        )
    }

    public var signatureInputSHA256Hex: SHA256HexDigest {
        LedgerRecordHasher.sha256Hex(
            of: framedBytes()
        )
    }
}

/// Canonical checkpoint-signature document matching
/// `pulsemech_device_signature_v0`.
///
/// The document carries no generated time, no private-key material, and no
/// release or device-control authority.
public struct DeviceCheckpointSignatureDocument: Sendable, Equatable {
    public let subject: DeviceCheckpointSignatureSubject
    public let signature: DeviceP256Signature

    init(
        subject: DeviceCheckpointSignatureSubject,
        signature: DeviceP256Signature
    ) {
        self.subject = subject
        self.signature = signature
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            checkpointSignatureMember(
                "authority_effect",
                checkpointSignatureString("none")
            ),
            checkpointSignatureMember(
                "curve",
                checkpointSignatureString("secp256r1")
            ),
            checkpointSignatureMember(
                "document_type",
                checkpointSignatureString("pulsemech_device_signature")
            ),
            checkpointSignatureMember(
                "ecdsa_s_rule",
                checkpointSignatureString("low_s_required")
            ),
            checkpointSignatureMember(
                "ecdsa_scalar_range",
                checkpointSignatureString("one_to_curve_order_minus_one")
            ),
            checkpointSignatureMember(
                "hash_algorithm",
                checkpointSignatureString("SHA-256")
            ),
            checkpointSignatureMember(
                "ledger_id",
                subject.ledgerID.canonicalValue
            ),
            checkpointSignatureMember(
                "observer_public_key_fingerprint_sha256",
                subject.observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            checkpointSignatureMember(
                "public_key_encoding",
                checkpointSignatureString("x963_uncompressed")
            ),
            checkpointSignatureMember(
                "public_key_fingerprint_subject",
                checkpointSignatureString(
                    "exact_65_byte_x963_uncompressed_public_key"
                )
            ),
            checkpointSignatureMember(
                "public_key_size_bytes",
                .integer(65)
            ),
            checkpointSignatureMember(
                "schema_version",
                checkpointSignatureString(
                    "pulsemech_device_signature_v0"
                )
            ),
            checkpointSignatureMember(
                "signature_base64",
                checkpointSignatureString(signature.canonicalBase64)
            ),
            checkpointSignatureMember(
                "signature_domain",
                checkpointSignatureString(
                    DeviceCheckpointSignatureSubject.signatureDomain
                )
            ),
            checkpointSignatureMember(
                "signature_encoding",
                checkpointSignatureString("ieee_p1363_fixed_width")
            ),
            checkpointSignatureMember(
                "signature_role",
                checkpointSignatureString("ledger_checkpoint")
            ),
            checkpointSignatureMember(
                "signature_size_bytes",
                .integer(64)
            ),
            checkpointSignatureMember(
                "signature_subject_canonicalization",
                checkpointSignatureString(
                    "pulsemech_device_canonical_json_v0"
                )
            ),
            checkpointSignatureMember(
                "signature_subject_framing",
                checkpointSignatureString(
                    "ascii_domain_separator_then_0x00_then_canonical_subject_json"
                )
            ),
            checkpointSignatureMember(
                "signature_subject_version",
                checkpointSignatureString(
                    "pulsemech_device_signature_subject_v0"
                )
            ),
            checkpointSignatureMember(
                "signature_suite",
                checkpointSignatureString(
                    DeviceCheckpointSignatureSubject.signatureSuite
                )
            ),
            checkpointSignatureMember(
                "signed_object_sha256",
                subject.signedObjectSHA256.canonicalValue
            ),
            checkpointSignatureMember(
                "signed_object_type",
                checkpointSignatureString(
                    "checkpoint_record_sha256"
                )
            ),
        ])
    }

    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    public var documentSHA256: SHA256HexDigest {
        LedgerRecordHasher.sha256Hex(
            of: canonicalBytes()
        )
    }

    public var sizeBytes: Int64 {
        Int64(canonicalBytes().count)
    }
}

private func checkpointSignatureMember(
    _ key: String,
    _ value: CanonicalJSONValue
) -> CanonicalJSONObjectMember {
    try! CanonicalJSONObjectMember(
        key: key,
        value: value
    )
}

private func checkpointSignatureString(
    _ value: String
) -> CanonicalJSONValue {
    .string(try! CanonicalJSONString(value))
}
