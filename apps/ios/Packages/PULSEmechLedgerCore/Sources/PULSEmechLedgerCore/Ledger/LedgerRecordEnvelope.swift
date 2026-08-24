import Foundation

/// Construction failures for the closed Device Ledger v0 record envelope.
public enum LedgerRecordEnvelopeError: Error, Sendable, Equatable {
    case identifierLengthOutOfRange
    case identifierContainsForbiddenByte(UInt8)
    case sha256DigestMustBeLowercaseHex
    case negativeSequenceIndex
    case negativeRecordedWallTime
    case negativeMonotonicTime
    case firstRecordRequiresNoPreviousDigest
    case nonFirstRecordRequiresPreviousDigest
    case payloadMustBeObject
    case payloadTypeMissing
    case payloadTypeMustBeString
    case payloadTypeMismatch(expected: String, actual: String)
    case transitionClassMissing
    case transitionClassMustBeString
    case unsupportedTransitionClass(String)
    case transitionClassScopeMismatch(String)
    case scopeMismatch(LedgerRecordType)
}

/// A closed ASCII identifier accepted by the Device Ledger v0 schemas.
///
/// The lexical form is one through 256 ASCII bytes drawn from:
/// `A-Z a-z 0-9 . _ : / + -`.
public struct LedgerIdentifier: Sendable, Hashable {
    public let rawValue: String

    public init(_ rawValue: String) throws {
        let bytes = Array(rawValue.utf8)
        guard (1...256).contains(bytes.count) else {
            throw LedgerRecordEnvelopeError.identifierLengthOutOfRange
        }

        for byte in bytes where !Self.isAllowed(byte) {
            throw LedgerRecordEnvelopeError.identifierContainsForbiddenByte(byte)
        }

        self.rawValue = rawValue
    }

    private static func isAllowed(_ byte: UInt8) -> Bool {
        switch byte {
        case 0x41...0x5A,
             0x61...0x7A,
             0x30...0x39,
             0x2E,
             0x5F,
             0x3A,
             0x2F,
             0x2B,
             0x2D:
            true
        default:
            false
        }
    }

    var canonicalValue: CanonicalJSONValue {
        .string(try! CanonicalJSONString(rawValue))
    }
}

/// One lowercase hexadecimal SHA-256 identity.
public struct SHA256HexDigest: Sendable, Hashable {
    public let rawValue: String

    public init(_ rawValue: String) throws {
        let bytes = Array(rawValue.utf8)
        guard bytes.count == 64,
              bytes.allSatisfy({
                  (0x30...0x39).contains($0) ||
                  (0x61...0x66).contains($0)
              }) else {
            throw LedgerRecordEnvelopeError.sha256DigestMustBeLowercaseHex
        }

        self.rawValue = rawValue
    }

    var canonicalValue: CanonicalJSONValue {
        .string(try! CanonicalJSONString(rawValue))
    }
}

/// The six record classes admitted by the Device Transition Ledger v0 schema.
public enum LedgerRecordType: String, Sendable, Equatable, CaseIterable {
    case sessionBoundary = "session_boundary"
    case stateSnapshot = "state_snapshot"
    case observationEvent = "observation_event"
    case coverageInterval = "coverage_interval"
    case transition
    case checkpoint
}

/// Declares whether one record is a synthetic fixture or a platform observation.
public enum LedgerRecordStatus: String, Sendable, Equatable {
    case syntheticReference = "synthetic_reference"
    case observed
}

/// Binds a record either to one observer session and clock epoch or to the
/// ledger-wide relation layer.
public enum LedgerRecordScope: Sendable, Equatable {
    case session(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        monotonicTimeNS: Int64
    )
    case ledgerWide
}

/// The non-authority claim boundary repeated in every Device Ledger v0 record.
public struct LedgerRecordClaimBoundary: Sendable, Equatable {
    public init() {}

    var canonicalValue: CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "causal_completion_claim",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "continuous_monitoring_claim",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "device_security_claim",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "malware_claim",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "physical_measurement_claim",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "release_authority_effect",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "system_wide_network_claim",
                value: .string("none")
            ),
        ])
    }
}

/// The exact record bytes that are hashed, excluding only `record_sha256`.
///
/// This type validates the envelope-level invariants before a digest is
/// calculated. Payload-specific relation rules remain the responsibility of the
/// typed payload builders and the separately implemented verifier.
public struct LedgerRecordDigestSubject: Sendable, Equatable {
    public static let canonicalizationProfileSHA256 = try! SHA256HexDigest(
        "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550"
    )
    public static let observationContractSHA256 = try! SHA256HexDigest(
        "e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2"
    )

    public let ledgerID: LedgerIdentifier
    public let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public let payload: CanonicalJSONValue
    public let previousRecordSHA256: SHA256HexDigest?
    public let recordID: LedgerIdentifier
    public let recordStatus: LedgerRecordStatus
    public let recordType: LedgerRecordType
    public let recordedWallTimeUnixNS: Int64
    public let sequenceIndex: Int64
    public let scope: LedgerRecordScope

    public init(
        ledgerID: LedgerIdentifier,
        observerPublicKeyFingerprintSHA256: SHA256HexDigest,
        payload: CanonicalJSONValue,
        previousRecordSHA256: SHA256HexDigest?,
        recordID: LedgerIdentifier,
        recordStatus: LedgerRecordStatus,
        recordType: LedgerRecordType,
        recordedWallTimeUnixNS: Int64,
        sequenceIndex: Int64,
        scope: LedgerRecordScope
    ) throws {
        guard sequenceIndex >= 0 else {
            throw LedgerRecordEnvelopeError.negativeSequenceIndex
        }
        guard recordedWallTimeUnixNS >= 0 else {
            throw LedgerRecordEnvelopeError.negativeRecordedWallTime
        }

        if sequenceIndex == 0 {
            guard previousRecordSHA256 == nil else {
                throw LedgerRecordEnvelopeError.firstRecordRequiresNoPreviousDigest
            }
        } else {
            guard previousRecordSHA256 != nil else {
                throw LedgerRecordEnvelopeError.nonFirstRecordRequiresPreviousDigest
            }
        }

        guard case let .object(payloadObject) = payload else {
            throw LedgerRecordEnvelopeError.payloadMustBeObject
        }

        guard let payloadTypeMember = payloadObject.members.first(
            where: { $0.key.value == "payload_type" }
        ) else {
            throw LedgerRecordEnvelopeError.payloadTypeMissing
        }
        guard case let .string(payloadTypeString) = payloadTypeMember.value else {
            throw LedgerRecordEnvelopeError.payloadTypeMustBeString
        }
        guard payloadTypeString.value == recordType.rawValue else {
            throw LedgerRecordEnvelopeError.payloadTypeMismatch(
                expected: recordType.rawValue,
                actual: payloadTypeString.value
            )
        }

        switch scope {
        case let .session(_, _, monotonicTimeNS):
            guard monotonicTimeNS >= 0 else {
                throw LedgerRecordEnvelopeError.negativeMonotonicTime
            }
        case .ledgerWide:
            break
        }

        switch (recordType, scope) {
        case (.sessionBoundary, .session),
             (.stateSnapshot, .session),
             (.observationEvent, .session),
             (.coverageInterval, .ledgerWide),
             (.checkpoint, .ledgerWide),
             (.transition, .session),
             (.transition, .ledgerWide):
            break
        default:
            throw LedgerRecordEnvelopeError.scopeMismatch(recordType)
        }

        if recordType == .transition {
            guard let transitionClassMember = payloadObject.members.first(
                where: { $0.key.value == "transition_class" }
            ) else {
                throw LedgerRecordEnvelopeError.transitionClassMissing
            }
            guard case let .string(transitionClassString) = transitionClassMember.value else {
                throw LedgerRecordEnvelopeError.transitionClassMustBeString
            }

            switch (transitionClassString.value, scope) {
            case ("event_bound", .session),
                 ("endpoint_difference_only", .ledgerWide):
                break
            case ("event_bound", .ledgerWide),
                 ("endpoint_difference_only", .session):
                throw LedgerRecordEnvelopeError.transitionClassScopeMismatch(
                    transitionClassString.value
                )
            default:
                throw LedgerRecordEnvelopeError.unsupportedTransitionClass(
                    transitionClassString.value
                )
            }
        }

        self.ledgerID = ledgerID
        self.observerPublicKeyFingerprintSHA256 = observerPublicKeyFingerprintSHA256
        self.payload = payload
        self.previousRecordSHA256 = previousRecordSHA256
        self.recordID = recordID
        self.recordStatus = recordStatus
        self.recordType = recordType
        self.recordedWallTimeUnixNS = recordedWallTimeUnixNS
        self.sequenceIndex = sequenceIndex
        self.scope = scope
    }

    /// Returns the exact canonical value hashed for `record_sha256`.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object(canonicalMembers())
    }

    /// Returns the exact canonical bytes hashed for `record_sha256`.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    /// Attaches a separately calculated record digest to this subject.
    public func finalized(
        recordSHA256: SHA256HexDigest
    ) -> LedgerRecordEnvelope {
        LedgerRecordEnvelope(
            digestSubject: self,
            recordSHA256: recordSHA256
        )
    }

    fileprivate func canonicalMembers() -> [CanonicalJSONObjectMember] {
        let scopeValues: (
            sessionID: CanonicalJSONValue,
            clockEpochID: CanonicalJSONValue,
            monotonicTimeNS: CanonicalJSONValue
        )

        switch scope {
        case let .session(sessionID, clockEpochID, monotonicTimeNS):
            scopeValues = (
                sessionID.canonicalValue,
                clockEpochID.canonicalValue,
                .integer(monotonicTimeNS)
            )
        case .ledgerWide:
            scopeValues = (
                .null,
                .null,
                .null
            )
        }

        return [
            try! CanonicalJSONObjectMember(
                key: "authority_effect",
                value: .string("none")
            ),
            try! CanonicalJSONObjectMember(
                key: "canonicalization_profile_sha256",
                value: Self.canonicalizationProfileSHA256.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "claim_boundary",
                value: LedgerRecordClaimBoundary().canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "clock_epoch_id",
                value: scopeValues.clockEpochID
            ),
            try! CanonicalJSONObjectMember(
                key: "document_type",
                value: .string("pulsemech_device_ledger_record")
            ),
            try! CanonicalJSONObjectMember(
                key: "ledger_id",
                value: ledgerID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "monotonic_time_ns",
                value: scopeValues.monotonicTimeNS
            ),
            try! CanonicalJSONObjectMember(
                key: "observation_contract_sha256",
                value: Self.observationContractSHA256.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "observer_public_key_fingerprint_sha256",
                value: observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "payload",
                value: payload
            ),
            try! CanonicalJSONObjectMember(
                key: "previous_record_sha256",
                value: previousRecordSHA256?.canonicalValue ?? .null
            ),
            try! CanonicalJSONObjectMember(
                key: "record_id",
                value: recordID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "record_status",
                value: .string(recordStatus.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "record_type",
                value: .string(recordType.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "recorded_wall_time_unix_ns",
                value: .integer(recordedWallTimeUnixNS)
            ),
            try! CanonicalJSONObjectMember(
                key: "schema_version",
                value: .string("pulsemech_device_ledger_record_v0")
            ),
            try! CanonicalJSONObjectMember(
                key: "sequence_index",
                value: .integer(sequenceIndex)
            ),
            try! CanonicalJSONObjectMember(
                key: "session_id",
                value: scopeValues.sessionID
            ),
        ]
    }
}

/// One finalized Device Ledger v0 record carrying its declared canonical
/// digest. The next hashing layer is responsible for calculating that digest
/// from `digestSubject.canonicalBytes()` before attachment.
public struct LedgerRecordEnvelope: Sendable, Equatable {
    public let digestSubject: LedgerRecordDigestSubject
    public let recordSHA256: SHA256HexDigest

    public init(
        digestSubject: LedgerRecordDigestSubject,
        recordSHA256: SHA256HexDigest
    ) {
        self.digestSubject = digestSubject
        self.recordSHA256 = recordSHA256
    }

    /// Returns the complete canonical record, including `record_sha256`.
    public func canonicalValue() -> CanonicalJSONValue {
        var members = digestSubject.canonicalMembers()
        members.append(
            try! CanonicalJSONObjectMember(
                key: "record_sha256",
                value: recordSHA256.canonicalValue
            )
        )
        return try! .object(members)
    }

    /// Returns the complete exact canonical record bytes.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    /// Returns the compact cross-record reference used by payload relations.
    public var reference: LedgerRecordReference {
        LedgerRecordReference(
            validatedRecordID: digestSubject.recordID,
            recordSHA256: recordSHA256,
            sequenceIndex: digestSubject.sequenceIndex
        )
    }
}

/// The exact three-field cross-record reference used by ledger payloads.
public struct LedgerRecordReference: Sendable, Equatable {
    public let recordID: LedgerIdentifier
    public let recordSHA256: SHA256HexDigest
    public let sequenceIndex: Int64

    public init(
        recordID: LedgerIdentifier,
        recordSHA256: SHA256HexDigest,
        sequenceIndex: Int64
    ) throws {
        guard sequenceIndex >= 0 else {
            throw LedgerRecordEnvelopeError.negativeSequenceIndex
        }

        self.recordID = recordID
        self.recordSHA256 = recordSHA256
        self.sequenceIndex = sequenceIndex
    }

    fileprivate init(
        validatedRecordID recordID: LedgerIdentifier,
        recordSHA256: SHA256HexDigest,
        sequenceIndex: Int64
    ) {
        self.recordID = recordID
        self.recordSHA256 = recordSHA256
        self.sequenceIndex = sequenceIndex
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "record_id",
                value: recordID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "record_sha256",
                value: recordSHA256.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "sequence_index",
                value: .integer(sequenceIndex)
            ),
        ])
    }

    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }
}
