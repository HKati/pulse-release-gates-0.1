import Foundation

/// Fail-closed construction errors for the ordered Device Ledger v0 record
/// chain.
public enum LedgerRecordChainError: Error, Sendable, Equatable {
    /// No additional record can be appended after the terminal checkpoint.
    case chainAlreadyCheckpointed

    /// A checkpoint cannot be the first record because a valid ledger contains
    /// at least one closed record before its terminal checkpoint.
    case checkpointRequiresPriorRecord

    /// The ledger's 100,000-record schema limit has been reached.
    case recordLimitReached

    /// The last available record slot is reserved for the terminal checkpoint.
    case checkpointSlotRequired

    /// Record IDs are unique across the complete ledger chain.
    case duplicateRecordID(LedgerIdentifier)

    /// One observer session cannot change its clock epoch.
    case sessionClockEpochChanged(
        sessionID: LedgerIdentifier,
        expected: LedgerIdentifier,
        actual: LedgerIdentifier
    )

    /// One clock epoch cannot be reused by a different observer session.
    case clockEpochReused(
        clockEpochID: LedgerIdentifier,
        existingSessionID: LedgerIdentifier,
        proposedSessionID: LedgerIdentifier
    )

    /// Monotonic time must increase strictly within one clock epoch.
    case monotonicTimeNotStrictlyIncreasing(
        clockEpochID: LedgerIdentifier,
        previous: Int64,
        proposed: Int64
    )
}

/// Input fields supplied by the producer for one new ledger record.
///
/// Sequence index, previous-record digest, ledger identity, observer identity,
/// and record status are deliberately absent. `LedgerRecordChain` derives those
/// fields from its current accepted state so callers cannot choose or skip a
/// chain position.
public struct LedgerRecordDraft: Sendable, Equatable {
    public let payload: CanonicalJSONValue
    public let recordID: LedgerIdentifier
    public let recordType: LedgerRecordType
    public let recordedWallTimeUnixNS: Int64
    public let scope: LedgerRecordScope

    public init(
        payload: CanonicalJSONValue,
        recordID: LedgerIdentifier,
        recordType: LedgerRecordType,
        recordedWallTimeUnixNS: Int64,
        scope: LedgerRecordScope
    ) {
        self.payload = payload
        self.recordID = recordID
        self.recordType = recordType
        self.recordedWallTimeUnixNS = recordedWallTimeUnixNS
        self.scope = scope
    }
}

/// Terminal state of one in-memory record chain.
public enum LedgerRecordChainState: Sendable, Equatable {
    case acceptingRecords
    case checkpointed
}

/// Immutable value snapshot of one record chain.
public struct LedgerRecordChainSnapshot: Sendable, Equatable {
    public let ledgerID: LedgerIdentifier
    public let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public let recordStatus: LedgerRecordStatus
    public let records: [LedgerRecordEnvelope]
    public let state: LedgerRecordChainState

    public var recordCount: Int64 {
        Int64(records.count)
    }

    /// The next sequence index while the chain remains open.
    public var nextSequenceIndex: Int64? {
        state == .acceptingRecords ? Int64(records.count) : nil
    }

    public var firstRecordReference: LedgerRecordReference? {
        records.first?.reference
    }

    public var latestRecordReference: LedgerRecordReference? {
        records.last?.reference
    }

    /// Returns the complete records in accepted sequence order as canonical
    /// values for later ledger-document materialization.
    public var canonicalRecordValues: [CanonicalJSONValue] {
        records.map { $0.canonicalValue() }
    }
}

/// Actor-isolated append machine for one PULSEmech Device Ledger v0 record
/// chain.
///
/// The chain owns sequence assignment, previous-record binding, common ledger
/// identity, observer identity, record status, record-ID uniqueness, and
/// per-clock-epoch monotonic ordering. Each accepted draft is converted into a
/// canonical digest subject, hashed, finalized, and only then committed to the
/// chain state.
///
/// Payload-specific relation semantics remain outside this type and are checked
/// by typed payload builders and the separately implemented verifier.
public actor LedgerRecordChain {
    public static let maximumRecordCount = 100_000

    public nonisolated let ledgerID: LedgerIdentifier
    public nonisolated let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public nonisolated let recordStatus: LedgerRecordStatus

    private var records: [LedgerRecordEnvelope] = []
    private var recordIDs = Set<LedgerIdentifier>()
    private var clockEpochBySessionID: [LedgerIdentifier: LedgerIdentifier] = [:]
    private var sessionIDByClockEpoch: [LedgerIdentifier: LedgerIdentifier] = [:]
    private var lastMonotonicTimeByClockEpoch: [LedgerIdentifier: Int64] = [:]
    private var chainState: LedgerRecordChainState = .acceptingRecords

    public init(
        ledgerID: LedgerIdentifier,
        observerPublicKeyFingerprintSHA256: SHA256HexDigest,
        recordStatus: LedgerRecordStatus
    ) {
        self.ledgerID = ledgerID
        self.observerPublicKeyFingerprintSHA256 = observerPublicKeyFingerprintSHA256
        self.recordStatus = recordStatus
    }

    /// Appends one record through the complete chain-owned materialization path.
    ///
    /// No chain state changes are committed unless every validation, canonical
    /// serialization, digest calculation, and finalization step succeeds.
    @discardableResult
    public func append(
        _ draft: LedgerRecordDraft
    ) throws -> LedgerRecordEnvelope {
        guard chainState == .acceptingRecords else {
            throw LedgerRecordChainError.chainAlreadyCheckpointed
        }

        guard records.count < Self.maximumRecordCount else {
            throw LedgerRecordChainError.recordLimitReached
        }

        if draft.recordType == .checkpoint {
            guard !records.isEmpty else {
                throw LedgerRecordChainError.checkpointRequiresPriorRecord
            }
        } else if records.count == Self.maximumRecordCount - 1 {
            throw LedgerRecordChainError.checkpointSlotRequired
        }

        guard !recordIDs.contains(draft.recordID) else {
            throw LedgerRecordChainError.duplicateRecordID(
                draft.recordID
            )
        }

        let subject = try LedgerRecordDigestSubject(
            ledgerID: ledgerID,
            observerPublicKeyFingerprintSHA256: observerPublicKeyFingerprintSHA256,
            payload: draft.payload,
            previousRecordSHA256: records.last?.recordSHA256,
            recordID: draft.recordID,
            recordStatus: recordStatus,
            recordType: draft.recordType,
            recordedWallTimeUnixNS: draft.recordedWallTimeUnixNS,
            sequenceIndex: Int64(records.count),
            scope: draft.scope
        )

        try validateScopeContinuity(draft.scope)

        let envelope = LedgerRecordHasher.finalize(subject)

        recordIDs.insert(draft.recordID)
        commitScopeContinuity(draft.scope)
        records.append(envelope)

        if draft.recordType == .checkpoint {
            chainState = .checkpointed
        }

        return envelope
    }

    /// Returns one value snapshot without exposing mutable chain storage.
    public func snapshot() -> LedgerRecordChainSnapshot {
        LedgerRecordChainSnapshot(
            ledgerID: ledgerID,
            observerPublicKeyFingerprintSHA256: observerPublicKeyFingerprintSHA256,
            recordStatus: recordStatus,
            records: records,
            state: chainState
        )
    }

    private func validateScopeContinuity(
        _ scope: LedgerRecordScope
    ) throws {
        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = scope else {
            return
        }

        if let expectedEpoch = clockEpochBySessionID[sessionID],
           expectedEpoch != clockEpochID {
            throw LedgerRecordChainError.sessionClockEpochChanged(
                sessionID: sessionID,
                expected: expectedEpoch,
                actual: clockEpochID
            )
        }

        if let existingSessionID = sessionIDByClockEpoch[clockEpochID],
           existingSessionID != sessionID {
            throw LedgerRecordChainError.clockEpochReused(
                clockEpochID: clockEpochID,
                existingSessionID: existingSessionID,
                proposedSessionID: sessionID
            )
        }

        if let previous = lastMonotonicTimeByClockEpoch[clockEpochID],
           monotonicTimeNS <= previous {
            throw LedgerRecordChainError.monotonicTimeNotStrictlyIncreasing(
                clockEpochID: clockEpochID,
                previous: previous,
                proposed: monotonicTimeNS
            )
        }
    }

    private func commitScopeContinuity(
        _ scope: LedgerRecordScope
    ) {
        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = scope else {
            return
        }

        clockEpochBySessionID[sessionID] = clockEpochID
        sessionIDByClockEpoch[clockEpochID] = sessionID
        lastMonotonicTimeByClockEpoch[clockEpochID] = monotonicTimeNS
    }
}
