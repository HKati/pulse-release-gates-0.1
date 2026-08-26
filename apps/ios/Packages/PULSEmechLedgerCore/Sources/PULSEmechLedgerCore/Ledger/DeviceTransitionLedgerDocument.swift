import Foundation

/// Fail-closed construction errors for the complete Device Transition Ledger v0
/// document.
public enum DeviceTransitionLedgerDocumentError: Error, Sendable, Equatable {
    case observerPublicKeySizeInvalid
    case observerPublicKeyEncodingInvalid
    case observerPublicKeyCurveInvalid
    case observerIdentityProfileMismatch
    case observerFingerprintMismatch
    case checkpointSourceMismatch
    case closedRecordCountMismatch
    case firstRecordMismatch
    case terminalRecordMismatch
    case sourceRecordBindingMismatch(sequenceIndex: Int64)
    case checkpointRecordTypeMismatch
    case checkpointRecordScopeMismatch
    case checkpointSequenceMismatch(expected: Int64, actual: Int64)
    case checkpointPreviousDigestMismatch
    case checkpointCommonBindingMismatch
    case checkpointPayloadMismatch
}

/// Identity scope admitted by the Device Ledger v0 observer-identity schema.
public enum DeviceLedgerIdentityScope: String, Sendable, Equatable {
    case fixtureInstallation = "fixture_installation"
    case installation
}

/// P-256 key-origin profiles admitted by the Device Ledger v0 observer-identity
/// schema.
public enum DeviceLedgerKeyOriginProfile: String, Sendable, Equatable {
    case fixtureSoftwareP256 = "fixture_software_p256"
    case secureEnclaveP256 = "secure_enclave_p256"
    case softwareP256 = "software_p256"
}

/// Exact installation-scoped observer identity embedded in one ledger
/// document.
///
/// This value binds the ledger to exact 65-byte X9.63 uncompressed public-key
/// bytes. It does not claim Secure Enclave origin, platform attestation, or
/// external validation beyond the caller-selected declared key-origin profile.
public struct DeviceLedgerObserverIdentity: Sendable, Equatable {
    public let identityScope: DeviceLedgerIdentityScope
    public let keyOriginProfile: DeviceLedgerKeyOriginProfile
    public let publicKeyX963Uncompressed: Data
    public let publicKeyFingerprintSHA256: SHA256HexDigest

    public init(
        identityScope: DeviceLedgerIdentityScope,
        keyOriginProfile: DeviceLedgerKeyOriginProfile,
        publicKeyX963Uncompressed: Data
    ) throws {
        guard publicKeyX963Uncompressed.count == 65 else {
            throw DeviceTransitionLedgerDocumentError
                .observerPublicKeySizeInvalid
        }
        guard publicKeyX963Uncompressed.first == 0x04 else {
            throw DeviceTransitionLedgerDocumentError
                .observerPublicKeyEncodingInvalid
        }
        guard P256PublicKeyValidator.isValidUncompressedPoint(
            publicKeyX963Uncompressed
        ) else {
            throw DeviceTransitionLedgerDocumentError
                .observerPublicKeyCurveInvalid
        }

        switch (identityScope, keyOriginProfile) {
        case (.fixtureInstallation, .fixtureSoftwareP256),
             (.installation, .secureEnclaveP256),
             (.installation, .softwareP256):
            break
        default:
            throw DeviceTransitionLedgerDocumentError
                .observerIdentityProfileMismatch
        }

        self.identityScope = identityScope
        self.keyOriginProfile = keyOriginProfile
        self.publicKeyX963Uncompressed = Data(publicKeyX963Uncompressed)
        publicKeyFingerprintSHA256 = LedgerRecordHasher.sha256Hex(
            of: publicKeyX963Uncompressed
        )
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member("device_class", string("iphone")),
            member("identity_scope", string(identityScope.rawValue)),
            member("key_origin_profile", string(keyOriginProfile.rawValue)),
            member("platform", string("ios")),
            member("platform_attestation_status", string("not_present")),
            member(
                "public_key_base64",
                string(publicKeyX963Uncompressed.base64EncodedString())
            ),
            member("public_key_encoding", string("x963_uncompressed")),
            member(
                "public_key_fingerprint_sha256",
                publicKeyFingerprintSHA256.canonicalValue
            ),
            member("public_key_size_bytes", .integer(65)),
            member("signature_encoding", string("ieee_p1363_fixed_width")),
            member("signature_suite", string("ecdsa-p256-sha256")),
        ])
    }
}

/// Complete canonical Device Transition Ledger v0 document assembled from one
/// exact finalized record chain and its terminal checkpoint.
///
/// The document is produced before the checkpoint is committed to live chain
/// state. A construction failure therefore cannot leave a checkpointed chain
/// without its corresponding canonical ledger document.
public struct DeviceTransitionLedgerDocument: Sendable, Equatable {
    public let checkpointSource: LedgerCheckpointSource
    public let checkpointPayload: LedgerCheckpointPayload
    public let checkpointRecord: LedgerRecordEnvelope
    public let observerIdentity: DeviceLedgerObserverIdentity
    public let records: [LedgerRecordEnvelope]

    init(
        closedRecords: [LedgerRecordEnvelope],
        checkpointSource: LedgerCheckpointSource,
        checkpointPayload: LedgerCheckpointPayload,
        checkpointRecord: LedgerRecordEnvelope,
        observerIdentity: DeviceLedgerObserverIdentity
    ) throws {
        let reconstructedSource: LedgerCheckpointSource
        do {
            reconstructedSource = try LedgerCheckpointSource(
                ledgerID: checkpointSource.ledgerID,
                observerPublicKeyFingerprintSHA256:
                    checkpointSource.observerPublicKeyFingerprintSHA256,
                recordStatus: checkpointSource.recordStatus,
                records: closedRecords
            )
        } catch {
            throw DeviceTransitionLedgerDocumentError
                .checkpointSourceMismatch
        }
        guard reconstructedSource == checkpointSource else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointSourceMismatch
        }

        guard Int64(closedRecords.count) ==
                checkpointSource.closedRecordCount else {
            throw DeviceTransitionLedgerDocumentError
                .closedRecordCountMismatch
        }
        guard closedRecords.first?.reference ==
                checkpointSource.firstRecord else {
            throw DeviceTransitionLedgerDocumentError.firstRecordMismatch
        }
        guard closedRecords.last?.reference ==
                checkpointSource.terminalRecord else {
            throw DeviceTransitionLedgerDocumentError.terminalRecordMismatch
        }
        guard checkpointPayload.source == checkpointSource else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointPayloadMismatch
        }
        guard observerIdentity.publicKeyFingerprintSHA256 ==
                checkpointSource.observerPublicKeyFingerprintSHA256 else {
            throw DeviceTransitionLedgerDocumentError
                .observerFingerprintMismatch
        }

        for record in closedRecords {
            let subject = record.digestSubject
            guard subject.ledgerID == checkpointSource.ledgerID,
                  subject.observerPublicKeyFingerprintSHA256 ==
                    checkpointSource.observerPublicKeyFingerprintSHA256,
                  subject.recordStatus == checkpointSource.recordStatus else {
                throw DeviceTransitionLedgerDocumentError
                    .sourceRecordBindingMismatch(
                        sequenceIndex: subject.sequenceIndex
                    )
            }
        }

        let checkpointSubject = checkpointRecord.digestSubject
        guard checkpointSubject.recordType == .checkpoint else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointRecordTypeMismatch
        }
        guard checkpointSubject.scope == .ledgerWide else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointRecordScopeMismatch
        }
        guard checkpointSubject.sequenceIndex ==
                checkpointSource.closedRecordCount else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointSequenceMismatch(
                    expected: checkpointSource.closedRecordCount,
                    actual: checkpointSubject.sequenceIndex
                )
        }
        guard checkpointSubject.previousRecordSHA256 ==
                checkpointSource.terminalRecord.recordSHA256 else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointPreviousDigestMismatch
        }
        guard checkpointSubject.ledgerID == checkpointSource.ledgerID,
              checkpointSubject.observerPublicKeyFingerprintSHA256 ==
                checkpointSource.observerPublicKeyFingerprintSHA256,
              checkpointSubject.recordStatus == checkpointSource.recordStatus,
              checkpointSubject.recordedWallTimeUnixNS ==
                checkpointPayload.createdUnixNS else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointCommonBindingMismatch
        }
        guard checkpointSubject.payload == checkpointPayload.canonicalValue()
        else {
            throw DeviceTransitionLedgerDocumentError
                .checkpointPayloadMismatch
        }

        self.checkpointSource = checkpointSource
        self.checkpointPayload = checkpointPayload
        self.checkpointRecord = checkpointRecord
        self.observerIdentity = observerIdentity
        records = closedRecords + [checkpointRecord]
    }

    /// Exact canonical root document value.
    public func canonicalValue() -> CanonicalJSONValue {
        let firstRecordedWallTime = records[0]
            .digestSubject
            .recordedWallTimeUnixNS

        return try! .object([
            member("authority_boundary", authorityBoundaryValue()),
            member(
                "canonicalization_profile",
                canonicalizationProfileBindingValue()
            ),
            member(
                "claim_boundary",
                LedgerRecordClaimBoundary().canonicalValue
            ),
            member(
                "document_type",
                string("pulsemech_device_transition_ledger")
            ),
            member(
                "ledger_identity",
                try! .object([
                    member(
                        "created_unix_ns",
                        .integer(firstRecordedWallTime)
                    ),
                    member(
                        "ledger_id",
                        checkpointSource.ledgerID.canonicalValue
                    ),
                ])
            ),
            member("ledger_summary", ledgerSummaryValue()),
            member(
                "observation_contract",
                observationContractBindingValue()
            ),
            member("observer_identity", observerIdentity.canonicalValue()),
            member(
                "record_status",
                string(checkpointSource.recordStatus.rawValue)
            ),
            member(
                "records",
                .array(records.map { $0.canonicalValue() })
            ),
            member("reference_device_class", string("iphone")),
            member("reference_platform", string("ios")),
            member(
                "schema_version",
                string("pulsemech_device_transition_ledger_v0")
            ),
            member("signature_schema", signatureSchemaBindingValue()),
        ])
    }

    /// Exact canonical ledger bytes with no BOM, whitespace, or trailing
    /// newline.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    /// SHA-256 over the exact canonical ledger-document bytes.
    public var ledgerSHA256: SHA256HexDigest {
        LedgerRecordHasher.sha256Hex(
            of: canonicalBytes()
        )
    }

    public var sizeBytes: Int64 {
        Int64(canonicalBytes().count)
    }

    private func ledgerSummaryValue() -> CanonicalJSONValue {
        try! .object([
            member(
                "checkpoint_record_sha256",
                checkpointRecord.recordSHA256.canonicalValue
            ),
            member(
                "clock_epoch_count",
                .integer(checkpointSource.clockEpochCount)
            ),
            member(
                "coverage_interval_count",
                .integer(
                    checkpointSource.recordTypeCounts.coverageInterval
                )
            ),
            member(
                "observation_event_count",
                .integer(
                    checkpointSource.recordTypeCounts.observationEvent
                )
            ),
            member("record_count", .integer(Int64(records.count))),
            member(
                "session_boundary_count",
                .integer(
                    checkpointSource.recordTypeCounts.sessionBoundary
                )
            ),
            member(
                "session_count",
                .integer(checkpointSource.sessionCount)
            ),
            member(
                "snapshot_count",
                .integer(checkpointSource.recordTypeCounts.stateSnapshot)
            ),
            member(
                "terminal_record_sha256",
                checkpointRecord.recordSHA256.canonicalValue
            ),
            member(
                "transition_count",
                .integer(checkpointSource.recordTypeCounts.transition)
            ),
        ])
    }

    private func authorityBoundaryValue() -> CanonicalJSONValue {
        try! .object([
            member("authority_effect", string("none")),
            member("changes_release_authority", .boolean(false)),
            member("creates_device_control_authority", .boolean(false)),
            member("creates_release_decision", .boolean(false)),
        ])
    }

    private func canonicalizationProfileBindingValue() -> CanonicalJSONValue {
        try! .object([
            member("digest_algorithm", string("SHA-256")),
            member(
                "digest_subject",
                string("exact_package_member_bytes")
            ),
            member(
                "member_path",
                string("contracts/pulsemech_device_canonical_json_v0.json")
            ),
            member(
                "profile_id",
                string("pulsemech_device_canonical_json_v0")
            ),
            member(
                "profile_sha256",
                LedgerRecordDigestSubject
                    .canonicalizationProfileSHA256
                    .canonicalValue
            ),
            member("profile_version", string("0.1.0")),
        ])
    }

    private func observationContractBindingValue() -> CanonicalJSONValue {
        try! .object([
            member(
                "contract_id",
                string("pulsemech_ios_observation_contract_v0")
            ),
            member(
                "contract_sha256",
                LedgerRecordDigestSubject
                    .observationContractSHA256
                    .canonicalValue
            ),
            member("contract_version", string("0.1.0")),
            member("digest_algorithm", string("SHA-256")),
            member(
                "digest_subject",
                string("exact_package_member_bytes")
            ),
            member(
                "member_path",
                string("contracts/pulsemech_ios_observation_contract_v0.json")
            ),
        ])
    }

    private func signatureSchemaBindingValue() -> CanonicalJSONValue {
        try! .object([
            member("digest_algorithm", string("SHA-256")),
            member(
                "digest_subject",
                string("exact_package_member_bytes")
            ),
            member(
                "member_path",
                string("schemas/pulsemech_device_signature_v0.schema.json")
            ),
            member(
                "schema_id",
                string("pulsemech_device_signature_v0")
            ),
            member(
                "schema_sha256",
                LedgerCheckpointPayload
                    .signatureSchemaSHA256
                    .canonicalValue
            ),
            member(
                "schema_version",
                string("pulsemech_device_signature_v0")
            ),
        ])
    }
}

/// Exact result of one atomic terminal ledger closure.
public struct DeviceTransitionLedgerClosure: Sendable, Equatable {
    public let checkpointSource: LedgerCheckpointSource
    public let checkpointPayload: LedgerCheckpointPayload
    public let checkpointRecord: LedgerRecordEnvelope
    public let document: DeviceTransitionLedgerDocument

    init(
        checkpointSource: LedgerCheckpointSource,
        checkpointPayload: LedgerCheckpointPayload,
        checkpointRecord: LedgerRecordEnvelope,
        document: DeviceTransitionLedgerDocument
    ) {
        self.checkpointSource = checkpointSource
        self.checkpointPayload = checkpointPayload
        self.checkpointRecord = checkpointRecord
        self.document = document
    }
}

/// Dependency-free P-256 point-membership validation for exact X9.63 public
/// key bytes.
///
/// The closure layer does not sign or verify signatures. It nevertheless rejects
/// a public-key byte string that cannot represent a point on secp256r1, so the
/// canonical ledger document cannot claim a P-256 observer identity that the
/// standalone verifier will later reject before signature verification.
private enum P256PublicKeyValidator {
    private struct FieldElement: Equatable {
        /// Eight little-endian 32-bit limbs.
        let limbs: [UInt32]

        init(limbs: [UInt32]) {
            precondition(limbs.count == 8)
            self.limbs = limbs
        }

        init(bigEndianBytes bytes: ArraySlice<UInt8>) {
            precondition(bytes.count == 32)
            let values = Array(bytes)
            var words = [UInt32](repeating: 0, count: 8)
            for littleEndianIndex in 0..<8 {
                let start = (7 - littleEndianIndex) * 4
                words[littleEndianIndex] =
                    UInt32(values[start]) << 24 |
                    UInt32(values[start + 1]) << 16 |
                    UInt32(values[start + 2]) << 8 |
                    UInt32(values[start + 3])
            }
            limbs = words
        }

        static let zero = FieldElement(
            limbs: [UInt32](repeating: 0, count: 8)
        )

        static let modulus = FieldElement(
            limbs: [
                0xFFFFFFFF,
                0xFFFFFFFF,
                0xFFFFFFFF,
                0x00000000,
                0x00000000,
                0x00000000,
                0x00000001,
                0xFFFFFFFF,
            ]
        )

        static let curveB = FieldElement(
            limbs: [
                0x27D2604B,
                0x3BCE3C3E,
                0xCC53B0F6,
                0x651D06B0,
                0x769886BC,
                0xB3EBBD55,
                0xAA3A93E7,
                0x5AC635D8,
            ]
        )

        var isCanonicalFieldElement: Bool {
            Self.compare(self, Self.modulus) < 0
        }

        static func add(
            _ left: FieldElement,
            _ right: FieldElement
        ) -> FieldElement {
            var extended = [UInt32](repeating: 0, count: 9)
            var carry: UInt64 = 0

            for index in 0..<8 {
                let sum = UInt64(left.limbs[index]) +
                    UInt64(right.limbs[index]) + carry
                extended[index] = UInt32(truncatingIfNeeded: sum)
                carry = sum >> 32
            }
            extended[8] = UInt32(carry)

            if extended[8] != 0 ||
                compare(
                    FieldElement(limbs: Array(extended[0..<8])),
                    modulus
                ) >= 0 {
                extended = subtractModulus(from: extended)
            }

            precondition(extended[8] == 0)
            return FieldElement(limbs: Array(extended[0..<8]))
        }

        static func subtract(
            _ left: FieldElement,
            _ right: FieldElement
        ) -> FieldElement {
            if compare(left, right) >= 0 {
                return rawSubtract(left, right)
            }

            let difference = rawSubtract(right, left)
            return rawSubtract(modulus, difference)
        }

        static func multiply(
            _ left: FieldElement,
            _ right: FieldElement
        ) -> FieldElement {
            var result = zero
            var addend = left

            for word in right.limbs {
                var remainingBits = word
                for _ in 0..<32 {
                    if remainingBits & 1 == 1 {
                        result = add(result, addend)
                    }
                    remainingBits >>= 1
                    addend = add(addend, addend)
                }
            }

            return result
        }

        private static func compare(
            _ left: FieldElement,
            _ right: FieldElement
        ) -> Int {
            for index in stride(from: 7, through: 0, by: -1) {
                if left.limbs[index] < right.limbs[index] {
                    return -1
                }
                if left.limbs[index] > right.limbs[index] {
                    return 1
                }
            }
            return 0
        }

        private static func rawSubtract(
            _ left: FieldElement,
            _ right: FieldElement
        ) -> FieldElement {
            precondition(compare(left, right) >= 0)
            var output = [UInt32](repeating: 0, count: 8)
            var borrow: UInt64 = 0

            for index in 0..<8 {
                let leftValue = UInt64(left.limbs[index])
                let subtrahend = UInt64(right.limbs[index]) + borrow
                if leftValue >= subtrahend {
                    output[index] = UInt32(leftValue - subtrahend)
                    borrow = 0
                } else {
                    output[index] = UInt32(
                        (UInt64(1) << 32) + leftValue - subtrahend
                    )
                    borrow = 1
                }
            }

            precondition(borrow == 0)
            return FieldElement(limbs: output)
        }

        private static func subtractModulus(
            from value: [UInt32]
        ) -> [UInt32] {
            precondition(value.count == 9)
            var output = value
            var borrow: UInt64 = 0

            for index in 0..<8 {
                let leftValue = UInt64(output[index])
                let subtrahend = UInt64(modulus.limbs[index]) + borrow
                if leftValue >= subtrahend {
                    output[index] = UInt32(leftValue - subtrahend)
                    borrow = 0
                } else {
                    output[index] = UInt32(
                        (UInt64(1) << 32) + leftValue - subtrahend
                    )
                    borrow = 1
                }
            }

            let highValue = UInt64(output[8])
            precondition(highValue >= borrow)
            output[8] = UInt32(highValue - borrow)
            return output
        }
    }

    static func isValidUncompressedPoint(
        _ data: Data
    ) -> Bool {
        guard data.count == 65,
              data.first == 0x04 else {
            return false
        }

        let bytes = Array(data)
        let x = FieldElement(bigEndianBytes: bytes[1..<33])
        let y = FieldElement(bigEndianBytes: bytes[33..<65])
        guard x.isCanonicalFieldElement,
              y.isCanonicalFieldElement else {
            return false
        }

        let ySquared = FieldElement.multiply(y, y)
        let xSquared = FieldElement.multiply(x, x)
        let xCubed = FieldElement.multiply(xSquared, x)
        let threeX = FieldElement.add(
            x,
            FieldElement.add(x, x)
        )
        let rightHandSide = FieldElement.add(
            FieldElement.subtract(xCubed, threeX),
            .curveB
        )

        return ySquared == rightHandSide
    }
}

private func member(
    _ key: String,
    _ value: CanonicalJSONValue
) -> CanonicalJSONObjectMember {
    try! CanonicalJSONObjectMember(
        key: key,
        value: value
    )
}

private func string(
    _ value: String
) -> CanonicalJSONValue {
    .string(try! CanonicalJSONString(value))
}
