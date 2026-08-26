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

/// The two finalized records produced by one atomic dependent append.
public struct LedgerRecordAtomicPair: Sendable, Equatable {
    public let first: LedgerRecordEnvelope
    public let second: LedgerRecordEnvelope

    public init(
        first: LedgerRecordEnvelope,
        second: LedgerRecordEnvelope
    ) {
        self.first = first
        self.second = second
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

    private struct PreparedAppend: Sendable {
        let envelope: LedgerRecordEnvelope
        let recordID: LedgerIdentifier
        let recordType: LedgerRecordType
        let scope: LedgerRecordScope
    }

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
        let prepared = try prepareAppend(
            draft,
            after: nil
        )
        commit(prepared)
        return prepared.envelope
    }

    /// Appends two dependent records as one non-reentrant chain transaction.
    ///
    /// The first record is fully validated, canonically finalized, and held in a
    /// constant-size staging value. The second draft is then constructed from
    /// that finalized first record and validated against a one-record staged
    /// projection of the chain. Neither record is committed until both are
    /// ready.
    ///
    /// This avoids retaining copies of the complete record array, record-ID set,
    /// or continuity dictionaries for each callback. Successful pair appends
    /// therefore retain the same asymptotic cost as two ordinary appends rather
    /// than copying the accumulated chain.
    ///
    /// This is the required commit boundary for one admitted network callback:
    /// its observation-event record and callback-bound state snapshot are either
    /// both accepted or neither is accepted.
    @discardableResult
    public func appendAtomically(
        first firstDraft: LedgerRecordDraft,
        makeSecondDraft: @Sendable (LedgerRecordEnvelope) throws -> LedgerRecordDraft
    ) throws -> LedgerRecordAtomicPair {
        let firstPrepared = try prepareAppend(
            firstDraft,
            after: nil
        )
        let secondDraft = try makeSecondDraft(
            firstPrepared.envelope
        )
        let secondPrepared = try prepareAppend(
            secondDraft,
            after: firstPrepared
        )

        commit(firstPrepared)
        commit(secondPrepared)

        return LedgerRecordAtomicPair(
            first: firstPrepared.envelope,
            second: secondPrepared.envelope
        )
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

    /// Validates and finalizes one draft without mutating chain-owned state.
    ///
    /// `stagedPredecessor` represents at most one already prepared record. It is
    /// used by the dependent-pair path to derive the second record's sequence,
    /// predecessor digest, record-ID uniqueness, terminal state, and session
    /// continuity without copying or mutating the accumulated chain.
    private func prepareAppend(
        _ draft: LedgerRecordDraft,
        after stagedPredecessor: PreparedAppend?
    ) throws -> PreparedAppend {
        let effectiveState: LedgerRecordChainState
        if stagedPredecessor?.recordType == .checkpoint {
            effectiveState = .checkpointed
        } else {
            effectiveState = chainState
        }

        guard effectiveState == .acceptingRecords else {
            throw LedgerRecordChainError.chainAlreadyCheckpointed
        }

        let effectiveRecordCount = records.count + (stagedPredecessor == nil ? 0 : 1)

        guard effectiveRecordCount < Self.maximumRecordCount else {
            throw LedgerRecordChainError.recordLimitReached
        }

        if draft.recordType == .checkpoint {
            guard effectiveRecordCount > 0 else {
                throw LedgerRecordChainError.checkpointRequiresPriorRecord
            }
        } else if effectiveRecordCount == Self.maximumRecordCount - 1 {
            throw LedgerRecordChainError.checkpointSlotRequired
        }

        guard !recordIDs.contains(draft.recordID),
              stagedPredecessor?.recordID != draft.recordID else {
            throw LedgerRecordChainError.duplicateRecordID(
                draft.recordID
            )
        }

        let previousRecordSHA256 = stagedPredecessor?.envelope.recordSHA256
            ?? records.last?.recordSHA256

        let subject = try LedgerRecordDigestSubject(
            ledgerID: ledgerID,
            observerPublicKeyFingerprintSHA256: observerPublicKeyFingerprintSHA256,
            payload: draft.payload,
            previousRecordSHA256: previousRecordSHA256,
            recordID: draft.recordID,
            recordStatus: recordStatus,
            recordType: draft.recordType,
            recordedWallTimeUnixNS: draft.recordedWallTimeUnixNS,
            sequenceIndex: Int64(effectiveRecordCount),
            scope: draft.scope
        )

        try validateScopeContinuity(
            draft.scope,
            after: stagedPredecessor
        )

        return PreparedAppend(
            envelope: LedgerRecordHasher.finalize(subject),
            recordID: draft.recordID,
            recordType: draft.recordType,
            scope: draft.scope
        )
    }

    /// Commits one already prepared append without any throwing operation.
    private func commit(
        _ prepared: PreparedAppend
    ) {
        recordIDs.insert(prepared.recordID)
        commitScopeContinuity(prepared.scope)
        records.append(prepared.envelope)

        if prepared.recordType == .checkpoint {
            chainState = .checkpointed
        }
    }

    private func validateScopeContinuity(
        _ scope: LedgerRecordScope,
        after stagedPredecessor: PreparedAppend?
    ) throws {
        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = scope else {
            return
        }

        let stagedSessionScope: (
            sessionID: LedgerIdentifier,
            clockEpochID: LedgerIdentifier,
            monotonicTimeNS: Int64
        )?

        if let stagedPredecessor,
           case let .session(
               stagedSessionID,
               stagedClockEpochID,
               stagedMonotonicTimeNS
           ) = stagedPredecessor.scope {
            stagedSessionScope = (
                stagedSessionID,
                stagedClockEpochID,
                stagedMonotonicTimeNS
            )
        } else {
            stagedSessionScope = nil
        }

        let expectedEpoch: LedgerIdentifier?
        if let stagedSessionScope,
           stagedSessionScope.sessionID == sessionID {
            expectedEpoch = stagedSessionScope.clockEpochID
        } else {
            expectedEpoch = clockEpochBySessionID[sessionID]
        }

        if let expectedEpoch,
           expectedEpoch != clockEpochID {
            throw LedgerRecordChainError.sessionClockEpochChanged(
                sessionID: sessionID,
                expected: expectedEpoch,
                actual: clockEpochID
            )
        }

        let existingSessionID: LedgerIdentifier?
        if let stagedSessionScope,
           stagedSessionScope.clockEpochID == clockEpochID {
            existingSessionID = stagedSessionScope.sessionID
        } else {
            existingSessionID = sessionIDByClockEpoch[clockEpochID]
        }

        if let existingSessionID,
           existingSessionID != sessionID {
            throw LedgerRecordChainError.clockEpochReused(
                clockEpochID: clockEpochID,
                existingSessionID: existingSessionID,
                proposedSessionID: sessionID
            )
        }

        let previousMonotonicTime: Int64?
        if let stagedSessionScope,
           stagedSessionScope.clockEpochID == clockEpochID {
            previousMonotonicTime = stagedSessionScope.monotonicTimeNS
        } else {
            previousMonotonicTime = lastMonotonicTimeByClockEpoch[clockEpochID]
        }

        if let previousMonotonicTime,
           monotonicTimeNS <= previousMonotonicTime {
            throw LedgerRecordChainError.monotonicTimeNotStrictlyIncreasing(
                clockEpochID: clockEpochID,
                previous: previousMonotonicTime,
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
