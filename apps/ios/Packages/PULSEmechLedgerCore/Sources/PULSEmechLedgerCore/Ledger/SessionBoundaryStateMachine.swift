import Foundation

/// Fail-closed lifecycle-ordering errors for the Device Ledger v0 session
/// boundary state machine.
public enum SessionBoundaryStateMachineError: Error, Sendable, Equatable {
    /// The observation ingress contract requires one serial caller. A second
    /// operation that enters while this state machine is awaiting the ordered
    /// record chain is rejected rather than interleaved.
    case operationInProgress

    /// A close or disconnect callback arrived before any observer session was
    /// opened.
    case noCurrentSession(
        event: SessionBoundaryLifecycleEvent
    )

    /// A new active callback attempted to replace an observation window that is
    /// still open.
    case activeSessionConflict(
        currentSessionID: LedgerIdentifier,
        currentClockEpochID: LedgerIdentifier,
        proposedSessionID: LedgerIdentifier,
        proposedClockEpochID: LedgerIdentifier
    )

    /// A lifecycle callback was submitted for a session other than the current
    /// session.
    case callbackSessionMismatch(
        event: SessionBoundaryLifecycleEvent,
        expectedSessionID: LedgerIdentifier,
        actualSessionID: LedgerIdentifier
    )

    /// A lifecycle callback for the already terminated session cannot create a
    /// new boundary record.
    case eventAfterTerminalSession(
        event: SessionBoundaryLifecycleEvent,
        sessionID: LedgerIdentifier
    )

    /// Observer-session identifiers are single-use across the state-machine
    /// lifetime.
    case sessionIDReused(LedgerIdentifier)

    /// Every accepted observer session requires a previously unused clock
    /// epoch.
    case clockEpochIDReused(LedgerIdentifier)
}

/// One completed, explicitly bounded observation gap.
///
/// The relation begins at the accepted close or terminal boundary of one
/// observer session and ends at the accepted open boundary of the next session.
/// It does not claim that a hidden event or causal path inside the gap was
/// observed.
public struct SessionBoundaryObservationGap: Sendable, Equatable {
    public let sourceSessionID: LedgerIdentifier
    public let sourceClockEpochID: LedgerIdentifier
    public let targetSessionID: LedgerIdentifier
    public let targetClockEpochID: LedgerIdentifier
    public let gapStartBoundary: LedgerRecordReference
    public let gapEndBoundary: LedgerRecordReference

    public init(
        sourceSessionID: LedgerIdentifier,
        sourceClockEpochID: LedgerIdentifier,
        targetSessionID: LedgerIdentifier,
        targetClockEpochID: LedgerIdentifier,
        gapStartBoundary: LedgerRecordReference,
        gapEndBoundary: LedgerRecordReference
    ) {
        self.sourceSessionID = sourceSessionID
        self.sourceClockEpochID = sourceClockEpochID
        self.targetSessionID = targetSessionID
        self.targetClockEpochID = targetClockEpochID
        self.gapStartBoundary = gapStartBoundary
        self.gapEndBoundary = gapEndBoundary
    }
}

/// Complete lifecycle state derived from accepted session-boundary records.
public enum SessionBoundaryStateMachineState: Sendable, Equatable {
    /// No observer session has been accepted yet.
    case awaitingFirstSession

    /// One observation window is open for the current observer session.
    ///
    /// `precedingObservationGap` is present only when this open boundary ended a
    /// gap created by the immediately preceding session.
    case observationWindowOpen(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        previousSessionID: LedgerIdentifier?,
        precedingObservationGap: SessionBoundaryObservationGap?
    )

    /// The current observation window is closed, but the session has not yet
    /// terminated.
    case observationWindowClosed(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        closeBoundary: LedgerRecordReference
    )

    /// The current observer session has terminated exactly once.
    ///
    /// `closeBoundary` is present when the window had already been closed before
    /// disconnect. Otherwise the terminal boundary itself begins any later gap.
    case sessionTerminated(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        closeBoundary: LedgerRecordReference?,
        terminalBoundary: LedgerRecordReference
    )

    public var currentSessionID: LedgerIdentifier? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(sessionID, _, _, _, _),
             let .observationWindowClosed(sessionID, _, _, _),
             let .sessionTerminated(sessionID, _, _, _, _):
            sessionID
        }
    }

    public var currentClockEpochID: LedgerIdentifier? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, clockEpochID, _, _, _),
             let .observationWindowClosed(_, clockEpochID, _, _),
             let .sessionTerminated(_, clockEpochID, _, _, _):
            clockEpochID
        }
    }

    public var observationWindowState: SessionBoundaryObservationWindowState? {
        switch self {
        case .awaitingFirstSession:
            nil
        case .observationWindowOpen:
            .open
        case .observationWindowClosed:
            .closed
        case .sessionTerminated:
            .terminal
        }
    }

    public var currentOpenBoundary: LedgerRecordReference? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, _, openBoundary, _, _),
             let .observationWindowClosed(_, _, openBoundary, _),
             let .sessionTerminated(_, _, openBoundary, _, _):
            openBoundary
        }
    }

    /// Boundary that begins the pending or most recently completed observation
    /// gap associated with the current state.
    public var observationGapStartBoundary: LedgerRecordReference? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, _, _, _, gap):
            gap?.gapStartBoundary
        case let .observationWindowClosed(_, _, _, closeBoundary):
            closeBoundary
        case let .sessionTerminated(_, _, _, closeBoundary, terminalBoundary):
            closeBoundary ?? terminalBoundary
        }
    }

    /// Completed close-to-open gap for the current open session, when present.
    public var completedObservationGap: SessionBoundaryObservationGap? {
        guard case let .observationWindowOpen(_, _, _, _, gap) = self else {
            return nil
        }
        return gap
    }

    public var latestBoundaryReference: LedgerRecordReference? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, _, openBoundary, _, _):
            openBoundary
        case let .observationWindowClosed(_, _, _, closeBoundary):
            closeBoundary
        case let .sessionTerminated(_, _, _, _, terminalBoundary):
            terminalBoundary
        }
    }
}

/// Result of one lifecycle callback submitted to the state machine.
public enum SessionBoundaryLifecycleResult: Sendable, Equatable {
    /// One new boundary record was appended. `completedGap` is present only when
    /// this opening record ended a previously pending observation gap.
    case recorded(
        record: LedgerRecordEnvelope,
        completedGap: SessionBoundaryObservationGap?
    )

    /// The callback was an exact idempotent duplicate and produced no record.
    case ignoredDuplicate(
        event: SessionBoundaryLifecycleEvent,
        sessionID: LedgerIdentifier,
        existingBoundary: LedgerRecordReference
    )
}

/// Consistent value snapshot of lifecycle state and the underlying ordered
/// record chain.
public struct SessionBoundaryStateMachineSnapshot: Sendable, Equatable {
    public let state: SessionBoundaryStateMachineState
    public let chain: LedgerRecordChainSnapshot
}

/// Actor-isolated lifecycle machine for Device Ledger v0 session-boundary
/// records.
///
/// The machine derives cross-record lifecycle state from accepted boundaries,
/// suppresses only the declared idempotent duplicates, binds callbacks to the
/// current session, requires single-use session and clock-epoch identities, and
/// appends typed boundary drafts through one ordered record chain.
///
/// Machine state changes only after the chain has accepted and finalized the
/// corresponding record. The caller must use one serialized ingress path for
/// this state machine and must not independently append session-boundary drafts
/// to the same chain.
public actor SessionBoundaryStateMachine {
    public nonisolated let ledgerID: LedgerIdentifier
    public nonisolated let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public nonisolated let recordStatus: LedgerRecordStatus

    private let chain: LedgerRecordChain
    private var state: SessionBoundaryStateMachineState = .awaitingFirstSession
    private var usedSessionIDs = Set<LedgerIdentifier>()
    private var usedClockEpochIDs = Set<LedgerIdentifier>()
    private var operationInProgress = false

    public init(
        chain: LedgerRecordChain
    ) {
        self.chain = chain
        ledgerID = chain.ledgerID
        observerPublicKeyFingerprintSHA256 = chain.observerPublicKeyFingerprintSHA256
        recordStatus = chain.recordStatus
    }

    /// Handles `scene_did_become_active` by opening the first observer session
    /// or a new observer session after the preceding window closed or session
    /// terminated.
    ///
    /// An exact repeat for the currently open session and clock epoch is
    /// idempotently ignored. A different proposed session while the current
    /// window remains open is rejected.
    @discardableResult
    public func sceneDidBecomeActive(
        boundaryID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        monotonicTimeNS: Int64
    ) async throws -> SessionBoundaryLifecycleResult {
        try beginOperation()
        defer { endOperation() }

        let previousSessionID: LedgerIdentifier?
        let sourceClockEpochID: LedgerIdentifier?
        let gapStartBoundary: LedgerRecordReference?

        switch state {
        case .awaitingFirstSession:
            previousSessionID = nil
            sourceClockEpochID = nil
            gapStartBoundary = nil

        case let .observationWindowOpen(
            currentSessionID,
            currentClockEpochID,
            openBoundary,
            _,
            _
        ):
            if currentSessionID == sessionID,
               currentClockEpochID == clockEpochID {
                return .ignoredDuplicate(
                    event: .sceneDidBecomeActive,
                    sessionID: currentSessionID,
                    existingBoundary: openBoundary
                )
            }

            throw SessionBoundaryStateMachineError.activeSessionConflict(
                currentSessionID: currentSessionID,
                currentClockEpochID: currentClockEpochID,
                proposedSessionID: sessionID,
                proposedClockEpochID: clockEpochID
            )

        case let .observationWindowClosed(
            currentSessionID,
            currentClockEpochID,
            _,
            closeBoundary
        ):
            previousSessionID = currentSessionID
            sourceClockEpochID = currentClockEpochID
            gapStartBoundary = closeBoundary

        case let .sessionTerminated(
            currentSessionID,
            currentClockEpochID,
            _,
            closeBoundary,
            terminalBoundary
        ):
            if currentSessionID == sessionID {
                throw SessionBoundaryStateMachineError.eventAfterTerminalSession(
                    event: .sceneDidBecomeActive,
                    sessionID: currentSessionID
                )
            }

            previousSessionID = currentSessionID
            sourceClockEpochID = currentClockEpochID
            gapStartBoundary = closeBoundary ?? terminalBoundary
        }

        guard !usedSessionIDs.contains(sessionID) else {
            throw SessionBoundaryStateMachineError.sessionIDReused(sessionID)
        }
        guard !usedClockEpochIDs.contains(clockEpochID) else {
            throw SessionBoundaryStateMachineError.clockEpochIDReused(clockEpochID)
        }

        let payload = SessionBoundaryPayload.opened(
            boundaryID: boundaryID,
            previousSessionID: previousSessionID
        )
        let draft = try payload.recordDraft(
            recordID: recordID,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            monotonicTimeNS: monotonicTimeNS
        )
        let envelope = try await chain.append(draft)

        let completedGap: SessionBoundaryObservationGap?
        if let previousSessionID,
           let sourceClockEpochID,
           let gapStartBoundary {
            completedGap = SessionBoundaryObservationGap(
                sourceSessionID: previousSessionID,
                sourceClockEpochID: sourceClockEpochID,
                targetSessionID: sessionID,
                targetClockEpochID: clockEpochID,
                gapStartBoundary: gapStartBoundary,
                gapEndBoundary: envelope.reference
            )
        } else {
            completedGap = nil
        }

        usedSessionIDs.insert(sessionID)
        usedClockEpochIDs.insert(clockEpochID)
        state = .observationWindowOpen(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            openBoundary: envelope.reference,
            previousSessionID: previousSessionID,
            precedingObservationGap: completedGap
        )

        return .recorded(
            record: envelope,
            completedGap: completedGap
        )
    }

    /// Handles `scene_will_resign_active` for the current session.
    ///
    /// The first callback closes the window and records one boundary. Repeated
    /// callbacks for that same closed session are idempotently ignored and do
    /// not create a second gap start.
    @discardableResult
    public func sceneWillResignActive(
        boundaryID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        sessionID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        monotonicTimeNS: Int64
    ) async throws -> SessionBoundaryLifecycleResult {
        try beginOperation()
        defer { endOperation() }

        switch state {
        case .awaitingFirstSession:
            throw SessionBoundaryStateMachineError.noCurrentSession(
                event: .sceneWillResignActive
            )

        case let .observationWindowOpen(
            currentSessionID,
            clockEpochID,
            openBoundary,
            _,
            _
        ):
            try requireSessionMatch(
                event: .sceneWillResignActive,
                expected: currentSessionID,
                actual: sessionID
            )

            let payload = SessionBoundaryPayload.observationWindowClosed(
                boundaryID: boundaryID,
                sessionID: currentSessionID
            )
            let draft = try payload.recordDraft(
                recordID: recordID,
                recordedWallTimeUnixNS: recordedWallTimeUnixNS,
                sessionID: currentSessionID,
                clockEpochID: clockEpochID,
                monotonicTimeNS: monotonicTimeNS
            )
            let envelope = try await chain.append(draft)

            state = .observationWindowClosed(
                sessionID: currentSessionID,
                clockEpochID: clockEpochID,
                openBoundary: openBoundary,
                closeBoundary: envelope.reference
            )

            return .recorded(
                record: envelope,
                completedGap: nil
            )

        case let .observationWindowClosed(
            currentSessionID,
            _,
            _,
            closeBoundary
        ):
            try requireSessionMatch(
                event: .sceneWillResignActive,
                expected: currentSessionID,
                actual: sessionID
            )

            return .ignoredDuplicate(
                event: .sceneWillResignActive,
                sessionID: currentSessionID,
                existingBoundary: closeBoundary
            )

        case let .sessionTerminated(
            currentSessionID,
            _,
            _,
            _,
            _
        ):
            try requireSessionMatch(
                event: .sceneWillResignActive,
                expected: currentSessionID,
                actual: sessionID
            )

            throw SessionBoundaryStateMachineError.eventAfterTerminalSession(
                event: .sceneWillResignActive,
                sessionID: currentSessionID
            )
        }
    }

    /// Handles `scene_did_disconnect` for the current session.
    ///
    /// Disconnect terminates an open or already closed session with one
    /// terminal boundary. An exact repeated disconnect for the terminal session
    /// is idempotently ignored. Other callbacks after terminal state are
    /// rejected.
    @discardableResult
    public func sceneDidDisconnect(
        boundaryID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        sessionID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        monotonicTimeNS: Int64
    ) async throws -> SessionBoundaryLifecycleResult {
        try beginOperation()
        defer { endOperation() }

        switch state {
        case .awaitingFirstSession:
            throw SessionBoundaryStateMachineError.noCurrentSession(
                event: .sceneDidDisconnect
            )

        case let .observationWindowOpen(
            currentSessionID,
            clockEpochID,
            openBoundary,
            _,
            _
        ):
            try requireSessionMatch(
                event: .sceneDidDisconnect,
                expected: currentSessionID,
                actual: sessionID
            )

            return try await recordTermination(
                boundaryID: boundaryID,
                recordID: recordID,
                sessionID: currentSessionID,
                clockEpochID: clockEpochID,
                openBoundary: openBoundary,
                closeBoundary: nil,
                recordedWallTimeUnixNS: recordedWallTimeUnixNS,
                monotonicTimeNS: monotonicTimeNS
            )

        case let .observationWindowClosed(
            currentSessionID,
            clockEpochID,
            openBoundary,
            closeBoundary
        ):
            try requireSessionMatch(
                event: .sceneDidDisconnect,
                expected: currentSessionID,
                actual: sessionID
            )

            return try await recordTermination(
                boundaryID: boundaryID,
                recordID: recordID,
                sessionID: currentSessionID,
                clockEpochID: clockEpochID,
                openBoundary: openBoundary,
                closeBoundary: closeBoundary,
                recordedWallTimeUnixNS: recordedWallTimeUnixNS,
                monotonicTimeNS: monotonicTimeNS
            )

        case let .sessionTerminated(
            currentSessionID,
            _,
            _,
            _,
            terminalBoundary
        ):
            try requireSessionMatch(
                event: .sceneDidDisconnect,
                expected: currentSessionID,
                actual: sessionID
            )

            return .ignoredDuplicate(
                event: .sceneDidDisconnect,
                sessionID: currentSessionID,
                existingBoundary: terminalBoundary
            )
        }
    }

    /// Returns one consistent lifecycle-and-chain snapshot.
    ///
    /// Snapshot acquisition participates in the same non-reentrant operation
    /// boundary as lifecycle mutation, so callers cannot observe a chain append
    /// before its corresponding lifecycle state has committed.
    public func snapshot() async throws -> SessionBoundaryStateMachineSnapshot {
        try beginOperation()
        defer { endOperation() }

        let chainSnapshot = await chain.snapshot()
        return SessionBoundaryStateMachineSnapshot(
            state: state,
            chain: chainSnapshot
        )
    }

    private func recordTermination(
        boundaryID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        closeBoundary: LedgerRecordReference?,
        recordedWallTimeUnixNS: Int64,
        monotonicTimeNS: Int64
    ) async throws -> SessionBoundaryLifecycleResult {
        let payload = SessionBoundaryPayload.sessionTerminated(
            boundaryID: boundaryID,
            sessionID: sessionID
        )
        let draft = try payload.recordDraft(
            recordID: recordID,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            monotonicTimeNS: monotonicTimeNS
        )
        let envelope = try await chain.append(draft)

        state = .sessionTerminated(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            openBoundary: openBoundary,
            closeBoundary: closeBoundary,
            terminalBoundary: envelope.reference
        )

        return .recorded(
            record: envelope,
            completedGap: nil
        )
    }

    private func requireSessionMatch(
        event: SessionBoundaryLifecycleEvent,
        expected: LedgerIdentifier,
        actual: LedgerIdentifier
    ) throws {
        guard expected == actual else {
            throw SessionBoundaryStateMachineError.callbackSessionMismatch(
                event: event,
                expectedSessionID: expected,
                actualSessionID: actual
            )
        }
    }

    private func beginOperation() throws {
        guard !operationInProgress else {
            throw SessionBoundaryStateMachineError.operationInProgress
        }
        operationInProgress = true
    }

    private func endOperation() {
        operationInProgress = false
    }
}
