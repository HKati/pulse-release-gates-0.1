import Foundation

/// Fail-closed construction errors for the Device Ledger v0 terminal
/// checkpoint projection and payload.
public enum LedgerCheckpointPayloadError: Error, Sendable, Equatable {
    /// A valid ledger checkpoint must close at least one prior record.
    case noClosedRecords

    /// A checkpoint projection must be derived before any checkpoint record is
    /// present in the source chain.
    case checkpointAlreadyPresent

    /// Every source record must retain the chain-owned ledger, observer, and
    /// record-status bindings.
    case sourceRecordBindingMismatch(sequenceIndex: Int64)

    /// Source records must remain contiguous and ordered exactly by their
    /// sequence index.
    case sourceSequenceMismatch(expected: Int64, actual: Int64)

    /// A coverage record did not contain one admitted coverage-status value.
    case unsupportedCoverageStatus(sequenceIndex: Int64)

    /// A transition record did not contain one admitted transition-class value.
    case unsupportedTransitionClass(sequenceIndex: Int64)

    /// Checkpoint and record wall times are non-negative signed 64-bit values.
    case negativeCreatedTime
}

/// Exact non-checkpoint record counts closed by one terminal checkpoint.
public struct LedgerCheckpointRecordTypeCounts: Sendable, Equatable {
    public let coverageInterval: Int64
    public let observationEvent: Int64
    public let sessionBoundary: Int64
    public let stateSnapshot: Int64
    public let transition: Int64

    public init(
        coverageInterval: Int64,
        observationEvent: Int64,
        sessionBoundary: Int64,
        stateSnapshot: Int64,
        transition: Int64
    ) {
        self.coverageInterval = coverageInterval
        self.observationEvent = observationEvent
        self.sessionBoundary = sessionBoundary
        self.stateSnapshot = stateSnapshot
        self.transition = transition
    }

    func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member("coverage_interval", .integer(coverageInterval)),
            member("observation_event", .integer(observationEvent)),
            member("session_boundary", .integer(sessionBoundary)),
            member("state_snapshot", .integer(stateSnapshot)),
            member("transition", .integer(transition)),
        ])
    }
}

/// Exact continuous and interrupted coverage counts closed by one checkpoint.
public struct LedgerCheckpointCoverageSummary: Sendable, Equatable {
    public let continuousIntervals: Int64
    public let interruptedIntervals: Int64

    public init(
        continuousIntervals: Int64,
        interruptedIntervals: Int64
    ) {
        self.continuousIntervals = continuousIntervals
        self.interruptedIntervals = interruptedIntervals
    }

    func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member("continuous_intervals", .integer(continuousIntervals)),
            member("interrupted_intervals", .integer(interruptedIntervals)),
        ])
    }
}

/// Exact event-bound and endpoint-difference transition counts closed by one
/// checkpoint.
public struct LedgerCheckpointTransitionSummary: Sendable, Equatable {
    public let endpointDifferenceOnly: Int64
    public let eventBound: Int64

    public init(
        endpointDifferenceOnly: Int64,
        eventBound: Int64
    ) {
        self.endpointDifferenceOnly = endpointDifferenceOnly
        self.eventBound = eventBound
    }

    func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member(
                "endpoint_difference_only",
                .integer(endpointDifferenceOnly)
            ),
            member("event_bound", .integer(eventBound)),
        ])
    }
}

/// Immutable projection of the exact open record chain that one checkpoint
/// closes.
///
/// All counts and bindings are derived from finalized chain records. Callers do
/// not provide record totals, coverage totals, transition totals, session
/// counts, epoch counts, first-record identity, or terminal-record identity.
public struct LedgerCheckpointSource: Sendable, Equatable {
    public let ledgerID: LedgerIdentifier
    public let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public let recordStatus: LedgerRecordStatus
    public let closedRecordCount: Int64
    public let firstRecord: LedgerRecordReference
    public let terminalRecord: LedgerRecordReference
    public let terminalSequenceIndex: Int64
    public let sessionCount: Int64
    public let clockEpochCount: Int64
    public let recordTypeCounts: LedgerCheckpointRecordTypeCounts
    public let coverageSummary: LedgerCheckpointCoverageSummary
    public let transitionSummary: LedgerCheckpointTransitionSummary

    init(
        ledgerID: LedgerIdentifier,
        observerPublicKeyFingerprintSHA256: SHA256HexDigest,
        recordStatus: LedgerRecordStatus,
        records: [LedgerRecordEnvelope]
    ) throws {
        guard let first = records.first,
              let terminal = records.last else {
            throw LedgerCheckpointPayloadError.noClosedRecords
        }

        var coverageIntervalCount: Int64 = 0
        var observationEventCount: Int64 = 0
        var sessionBoundaryCount: Int64 = 0
        var stateSnapshotCount: Int64 = 0
        var transitionCount: Int64 = 0

        var continuousCoverageCount: Int64 = 0
        var interruptedCoverageCount: Int64 = 0
        var eventBoundTransitionCount: Int64 = 0
        var endpointDifferenceTransitionCount: Int64 = 0

        var sessionIDs = Set<LedgerIdentifier>()
        var clockEpochIDs = Set<LedgerIdentifier>()

        for (offset, record) in records.enumerated() {
            let subject = record.digestSubject
            let expectedSequence = Int64(offset)

            guard subject.sequenceIndex == expectedSequence else {
                throw LedgerCheckpointPayloadError.sourceSequenceMismatch(
                    expected: expectedSequence,
                    actual: subject.sequenceIndex
                )
            }
            guard subject.ledgerID == ledgerID,
                  subject.observerPublicKeyFingerprintSHA256 ==
                    observerPublicKeyFingerprintSHA256,
                  subject.recordStatus == recordStatus else {
                throw LedgerCheckpointPayloadError.sourceRecordBindingMismatch(
                    sequenceIndex: subject.sequenceIndex
                )
            }

            switch subject.scope {
            case let .session(sessionID, clockEpochID, _):
                sessionIDs.insert(sessionID)
                clockEpochIDs.insert(clockEpochID)
            case .ledgerWide:
                break
            }

            switch subject.recordType {
            case .sessionBoundary:
                sessionBoundaryCount += 1
            case .stateSnapshot:
                stateSnapshotCount += 1
            case .observationEvent:
                observationEventCount += 1
            case .coverageInterval:
                coverageIntervalCount += 1
                switch subject.payload.objectStringValue(
                    forKey: "coverage_status"
                ) {
                case "continuous":
                    continuousCoverageCount += 1
                case "interrupted":
                    interruptedCoverageCount += 1
                default:
                    throw LedgerCheckpointPayloadError
                        .unsupportedCoverageStatus(
                            sequenceIndex: subject.sequenceIndex
                        )
                }
            case .transition:
                transitionCount += 1
                switch subject.payload.objectStringValue(
                    forKey: "transition_class"
                ) {
                case "event_bound":
                    eventBoundTransitionCount += 1
                case "endpoint_difference_only":
                    endpointDifferenceTransitionCount += 1
                default:
                    throw LedgerCheckpointPayloadError
                        .unsupportedTransitionClass(
                            sequenceIndex: subject.sequenceIndex
                        )
                }
            case .checkpoint:
                throw LedgerCheckpointPayloadError.checkpointAlreadyPresent
            }
        }

        self.ledgerID = ledgerID
        self.observerPublicKeyFingerprintSHA256 =
            observerPublicKeyFingerprintSHA256
        self.recordStatus = recordStatus
        closedRecordCount = Int64(records.count)
        firstRecord = first.reference
        terminalRecord = terminal.reference
        terminalSequenceIndex = terminal.digestSubject.sequenceIndex
        sessionCount = Int64(sessionIDs.count)
        clockEpochCount = Int64(clockEpochIDs.count)
        recordTypeCounts = LedgerCheckpointRecordTypeCounts(
            coverageInterval: coverageIntervalCount,
            observationEvent: observationEventCount,
            sessionBoundary: sessionBoundaryCount,
            stateSnapshot: stateSnapshotCount,
            transition: transitionCount
        )
        coverageSummary = LedgerCheckpointCoverageSummary(
            continuousIntervals: continuousCoverageCount,
            interruptedIntervals: interruptedCoverageCount
        )
        transitionSummary = LedgerCheckpointTransitionSummary(
            endpointDifferenceOnly: endpointDifferenceTransitionCount,
            eventBound: eventBoundTransitionCount
        )
    }
}

/// Producer-supplied identities and wall time for one terminal checkpoint.
///
/// All semantic closure fields are derived from the exact current chain.
public struct LedgerCheckpointMaterializationInput: Sendable, Equatable {
    public let checkpointID: LedgerIdentifier
    public let recordID: LedgerIdentifier
    public let recordedWallTimeUnixNS: Int64

    public init(
        checkpointID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64
    ) {
        self.checkpointID = checkpointID
        self.recordID = recordID
        self.recordedWallTimeUnixNS = recordedWallTimeUnixNS
    }
}

/// Closed typed Device Ledger v0 checkpoint payload.
///
/// The payload is a complete summary over the exact finalized non-checkpoint
/// chain. It does not sign the checkpoint and does not create package or release
/// authority.
public struct LedgerCheckpointPayload: Sendable, Equatable {
    public static let signatureSchemaSHA256 = try! SHA256HexDigest(
        "80304b08b73f3c05092909e7917240af94121e2c15b9305440a7e01460c049c0"
    )

    public let checkpointID: LedgerIdentifier
    public let createdUnixNS: Int64
    public let source: LedgerCheckpointSource

    init(
        checkpointID: LedgerIdentifier,
        createdUnixNS: Int64,
        source: LedgerCheckpointSource
    ) throws {
        guard createdUnixNS >= 0 else {
            throw LedgerCheckpointPayloadError.negativeCreatedTime
        }

        self.checkpointID = checkpointID
        self.createdUnixNS = createdUnixNS
        self.source = source
    }

    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member(
                "canonicalization_profile_sha256",
                LedgerRecordDigestSubject
                    .canonicalizationProfileSHA256
                    .canonicalValue
            ),
            member("checkpoint_id", checkpointID.canonicalValue),
            member("checkpoint_signature_required", .boolean(true)),
            member("clock_epoch_count", .integer(source.clockEpochCount)),
            member("closed_record_count", .integer(source.closedRecordCount)),
            member("coverage_summary", source.coverageSummary.canonicalValue()),
            member("created_unix_ns", .integer(createdUnixNS)),
            member("first_record", source.firstRecord.canonicalValue()),
            member("ledger_id", source.ledgerID.canonicalValue),
            member(
                "observation_contract_sha256",
                LedgerRecordDigestSubject
                    .observationContractSHA256
                    .canonicalValue
            ),
            member(
                "observer_public_key_fingerprint_sha256",
                source.observerPublicKeyFingerprintSHA256.canonicalValue
            ),
            member("payload_type", string("checkpoint")),
            member(
                "record_type_counts",
                source.recordTypeCounts.canonicalValue()
            ),
            member("session_count", .integer(source.sessionCount)),
            member(
                "signature_schema_sha256",
                Self.signatureSchemaSHA256.canonicalValue
            ),
            member("terminal_record", source.terminalRecord.canonicalValue()),
            member(
                "terminal_sequence_index",
                .integer(source.terminalSequenceIndex)
            ),
            member(
                "transition_summary",
                source.transitionSummary.canonicalValue()
            ),
        ])
    }

    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    func recordDraft(
        recordID: LedgerIdentifier
    ) -> LedgerRecordDraft {
        LedgerRecordDraft(
            payload: canonicalValue(),
            recordID: recordID,
            recordType: .checkpoint,
            recordedWallTimeUnixNS: createdUnixNS,
            scope: .ledgerWide
        )
    }
}

private extension CanonicalJSONValue {
    func objectStringValue(
        forKey key: String
    ) -> String? {
        guard case let .object(object) = self,
              let member = object.members.first(
                  where: { $0.key.value == key }
              ),
              case let .string(value) = member.value else {
            return nil
        }
        return value.value
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
