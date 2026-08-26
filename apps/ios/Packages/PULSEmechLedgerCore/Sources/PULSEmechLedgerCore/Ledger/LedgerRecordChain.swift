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

/// The three finalized records produced by one atomic dependent append.
public struct LedgerRecordAtomicTriple: Sendable, Equatable {
    public let first: LedgerRecordEnvelope
    public let second: LedgerRecordEnvelope
    public let third: LedgerRecordEnvelope

    public init(
        first: LedgerRecordEnvelope,
        second: LedgerRecordEnvelope,
        third: LedgerRecordEnvelope
    ) {
        self.first = first
        self.second = second
        self.third = third
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


    /// Fixed-size projection of at most two already prepared records.
    ///
    /// The projection is sufficient to validate the second record of a pair and
    /// the third record of a triple without copying any accumulated chain
    /// collection.
    private struct PreparedAppendProjection: Sendable {
        let first: PreparedAppend?
        let second: PreparedAppend?

        static let empty = PreparedAppendProjection(
            first: nil,
            second: nil
        )

        var count: Int {
            (first == nil ? 0 : 1) + (second == nil ? 0 : 1)
        }

        var latest: PreparedAppend? {
            second ?? first
        }

        var containsCheckpoint: Bool {
            first?.recordType == .checkpoint ||
                second?.recordType == .checkpoint
        }

        func contains(
            recordID: LedgerIdentifier
        ) -> Bool {
            first?.recordID == recordID || second?.recordID == recordID
        }

        func appending(
            _ prepared: PreparedAppend
        ) -> PreparedAppendProjection {
            if first == nil {
                return PreparedAppendProjection(
                    first: prepared,
                    second: nil
                )
            }

            precondition(
                second == nil,
                "Prepared append projection supports at most two records"
            )
            return PreparedAppendProjection(
                first: first,
                second: prepared
            )
        }

        func latestSessionScope(
            forSessionID sessionID: LedgerIdentifier
        ) -> (
            sessionID: LedgerIdentifier,
            clockEpochID: LedgerIdentifier,
            monotonicTimeNS: Int64
        )? {
            for prepared in [second, first] {
                guard let prepared,
                      case let .session(
                          stagedSessionID,
                          stagedClockEpochID,
                          stagedMonotonicTimeNS
                      ) = prepared.scope,
                      stagedSessionID == sessionID else {
                    continue
                }

                return (
                    stagedSessionID,
                    stagedClockEpochID,
                    stagedMonotonicTimeNS
                )
            }
            return nil
        }

        func latestSessionScope(
            forClockEpochID clockEpochID: LedgerIdentifier
        ) -> (
            sessionID: LedgerIdentifier,
            clockEpochID: LedgerIdentifier,
            monotonicTimeNS: Int64
        )? {
            for prepared in [second, first] {
                guard let prepared,
                      case let .session(
                          stagedSessionID,
                          stagedClockEpochID,
                          stagedMonotonicTimeNS
                      ) = prepared.scope,
                      stagedClockEpochID == clockEpochID else {
                    continue
                }

                return (
                    stagedSessionID,
                    stagedClockEpochID,
                    stagedMonotonicTimeNS
                )
            }
            return nil
        }
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
            after: .empty
        )
        commit(prepared)
        return prepared.envelope
    }

    /// Appends two dependent records as one non-reentrant chain transaction.
    ///
    /// Both records are fully prepared before either record is committed. The
    /// second record sees one fixed-size staged predecessor projection.
    @discardableResult
    public func appendAtomically(
        first firstDraft: LedgerRecordDraft,
        makeSecondDraft: @Sendable (LedgerRecordEnvelope) throws -> LedgerRecordDraft
    ) throws -> LedgerRecordAtomicPair {
        let firstPrepared = try prepareAppend(
            firstDraft,
            after: .empty
        )
        let afterFirst = PreparedAppendProjection.empty.appending(
            firstPrepared
        )
        let secondDraft = try makeSecondDraft(
            firstPrepared.envelope
        )
        let secondPrepared = try prepareAppend(
            secondDraft,
            after: afterFirst
        )

        commit(firstPrepared)
        commit(secondPrepared)

        return LedgerRecordAtomicPair(
            first: firstPrepared.envelope,
            second: secondPrepared.envelope
        )
    }

    /// Appends three dependent records as one non-reentrant chain transaction.
    ///
    /// This is the required commit boundary when one admitted callback produces
    /// an observation event, its callback-bound snapshot, and the coverage
    /// relation ending at that snapshot. All three records are prepared before
    /// the first non-throwing commit.
    @discardableResult
    public func appendAtomically(
        first firstDraft: LedgerRecordDraft,
        makeSecondDraft: @Sendable (LedgerRecordEnvelope) throws -> LedgerRecordDraft,
        makeThirdDraft: @Sendable (
            LedgerRecordEnvelope,
            LedgerRecordEnvelope
        ) throws -> LedgerRecordDraft
    ) throws -> LedgerRecordAtomicTriple {
        let firstPrepared = try prepareAppend(
            firstDraft,
            after: .empty
        )
        let afterFirst = PreparedAppendProjection.empty.appending(
            firstPrepared
        )
        let secondDraft = try makeSecondDraft(
            firstPrepared.envelope
        )
        let secondPrepared = try prepareAppend(
            secondDraft,
            after: afterFirst
        )
        let afterSecond = afterFirst.appending(
            secondPrepared
        )
        let thirdDraft = try makeThirdDraft(
            firstPrepared.envelope,
            secondPrepared.envelope
        )
        let thirdPrepared = try prepareAppend(
            thirdDraft,
            after: afterSecond
        )

        commit(firstPrepared)
        commit(secondPrepared)
        commit(thirdPrepared)

        return LedgerRecordAtomicTriple(
            first: firstPrepared.envelope,
            second: secondPrepared.envelope,
            third: thirdPrepared.envelope
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
    /// `stagedProjection` contains at most two already prepared records. It is
    /// sufficient for pair and triple dependent appends while remaining constant
    /// relative to accumulated chain length.
    private func prepareAppend(
        _ draft: LedgerRecordDraft,
        after stagedProjection: PreparedAppendProjection
    ) throws -> PreparedAppend {
        let effectiveState: LedgerRecordChainState =
            stagedProjection.containsCheckpoint ? .checkpointed : chainState

        guard effectiveState == .acceptingRecords else {
            throw LedgerRecordChainError.chainAlreadyCheckpointed
        }

        let effectiveRecordCount = records.count + stagedProjection.count

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
              !stagedProjection.contains(recordID: draft.recordID) else {
            throw LedgerRecordChainError.duplicateRecordID(
                draft.recordID
            )
        }

        let previousRecordSHA256 = stagedProjection.latest?.envelope.recordSHA256
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
            after: stagedProjection
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
        after stagedProjection: PreparedAppendProjection
    ) throws {
        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = scope else {
            return
        }

        let stagedSession = stagedProjection.latestSessionScope(
            forSessionID: sessionID
        )
        let expectedEpoch = stagedSession?.clockEpochID ??
            clockEpochBySessionID[sessionID]

        if let expectedEpoch,
           expectedEpoch != clockEpochID {
            throw LedgerRecordChainError.sessionClockEpochChanged(
                sessionID: sessionID,
                expected: expectedEpoch,
                actual: clockEpochID
            )
        }

        let stagedEpoch = stagedProjection.latestSessionScope(
            forClockEpochID: clockEpochID
        )
        let existingSessionID = stagedEpoch?.sessionID ??
            sessionIDByClockEpoch[clockEpochID]

        if let existingSessionID,
           existingSessionID != sessionID {
            throw LedgerRecordChainError.clockEpochReused(
                clockEpochID: clockEpochID,
                existingSessionID: existingSessionID,
                proposedSessionID: sessionID
            )
        }

        let previousMonotonicTime = stagedEpoch?.monotonicTimeNS ??
            lastMonotonicTimeByClockEpoch[clockEpochID]

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
