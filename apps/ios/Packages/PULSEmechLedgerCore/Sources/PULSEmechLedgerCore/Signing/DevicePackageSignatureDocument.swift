import Foundation

/// The exact four-field canonical subject bound by one Device Ledger v0
/// package signature.
public struct DevicePackageSignatureSubject: Sendable, Equatable {
    public static let signatureDomain =
        "PULSEMECH-DEVICE-LEDGER-PACKAGE-V0"
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
            packageSignatureMember(
                "ledger_id",
                ledgerID.canonicalValue
            ),
            packageSignatureMember(
                "observer_public_key_fingerprint_sha256",
                observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            packageSignatureMember(
                "signature_suite",
                packageSignatureString(Self.signatureSuite)
            ),
            packageSignatureMember(
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

    /// The exact 32-byte digest supplied to the observer-owned package signer.
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

/// Canonical package-signature document matching
/// `pulsemech_device_signature_v0`.
///
/// The document carries no generated time, no private-key material, and no
/// release or device-control authority.
public struct DevicePackageSignatureDocument: Sendable, Equatable {
    public let subject: DevicePackageSignatureSubject
    public let signature: DeviceP256Signature

    init(
        subject: DevicePackageSignatureSubject,
        signature: DeviceP256Signature
    ) {
        self.subject = subject
        self.signature = signature
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            packageSignatureMember(
                "authority_effect",
                packageSignatureString("none")
            ),
            packageSignatureMember(
                "curve",
                packageSignatureString("secp256r1")
            ),
            packageSignatureMember(
                "document_type",
                packageSignatureString("pulsemech_device_signature")
            ),
            packageSignatureMember(
                "ecdsa_s_rule",
                packageSignatureString("low_s_required")
            ),
            packageSignatureMember(
                "ecdsa_scalar_range",
                packageSignatureString("one_to_curve_order_minus_one")
            ),
            packageSignatureMember(
                "hash_algorithm",
                packageSignatureString("SHA-256")
            ),
            packageSignatureMember(
                "ledger_id",
                subject.ledgerID.canonicalValue
            ),
            packageSignatureMember(
                "observer_public_key_fingerprint_sha256",
                subject.observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            packageSignatureMember(
                "public_key_encoding",
                packageSignatureString("x963_uncompressed")
            ),
            packageSignatureMember(
                "public_key_fingerprint_subject",
                packageSignatureString(
                    "exact_65_byte_x963_uncompressed_public_key"
                )
            ),
            packageSignatureMember(
                "public_key_size_bytes",
                .integer(65)
            ),
            packageSignatureMember(
                "schema_version",
                packageSignatureString(
                    "pulsemech_device_signature_v0"
                )
            ),
            packageSignatureMember(
                "signature_base64",
                packageSignatureString(signature.canonicalBase64)
            ),
            packageSignatureMember(
                "signature_domain",
                packageSignatureString(
                    DevicePackageSignatureSubject.signatureDomain
                )
            ),
            packageSignatureMember(
                "signature_encoding",
                packageSignatureString("ieee_p1363_fixed_width")
            ),
            packageSignatureMember(
                "signature_role",
                packageSignatureString("ledger_package")
            ),
            packageSignatureMember(
                "signature_size_bytes",
                .integer(64)
            ),
            packageSignatureMember(
                "signature_subject_canonicalization",
                packageSignatureString(
                    "pulsemech_device_canonical_json_v0"
                )
            ),
            packageSignatureMember(
                "signature_subject_framing",
                packageSignatureString(
                    "ascii_domain_separator_then_0x00_then_canonical_subject_json"
                )
            ),
            packageSignatureMember(
                "signature_subject_version",
                packageSignatureString(
                    "pulsemech_device_signature_subject_v0"
                )
            ),
            packageSignatureMember(
                "signature_suite",
                packageSignatureString(
                    DevicePackageSignatureSubject.signatureSuite
                )
            ),
            packageSignatureMember(
                "signed_object_sha256",
                subject.signedObjectSHA256.canonicalValue
            ),
            packageSignatureMember(
                "signed_object_type",
                packageSignatureString(
                    "ledger_manifest_sha256"
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

private func packageSignatureMember(
    _ key: String,
    _ value: CanonicalJSONValue
) -> CanonicalJSONObjectMember {
    try! CanonicalJSONObjectMember(
        key: key,
        value: value
    )
}

private func packageSignatureString(
    _ value: String
) -> CanonicalJSONValue {
    .string(try! CanonicalJSONString(value))
}
