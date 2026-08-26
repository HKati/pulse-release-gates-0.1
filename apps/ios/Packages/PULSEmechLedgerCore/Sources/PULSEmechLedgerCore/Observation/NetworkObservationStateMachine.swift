import Foundation

/// Admission and ordering failures for the Device Ledger v0 network-observation
/// state machine.
public enum NetworkObservationStateMachineError: Error, Sendable, Equatable {
    /// The observation ingress contract requires one serial caller. A second
    /// operation entering while this actor awaits a dependent actor is rejected
    /// rather than interleaved.
    case operationInProgress

    /// A path update arrived before a session opened or after its observation
    /// window closed or terminated.
    case noOpenObservationWindow

    /// The callback named a session other than the current open observer
    /// session.
    case callbackSessionMismatch(
        expected: LedgerIdentifier,
        actual: LedgerIdentifier
    )

    /// The callback named a clock epoch other than the current observer
    /// session's epoch.
    case callbackClockEpochMismatch(
        expected: LedgerIdentifier,
        actual: LedgerIdentifier
    )

    /// The local network state and the lifecycle state machine no longer
    /// describe the same open session and boundary. This indicates forbidden
    /// out-of-band mutation of the shared chain or lifecycle machine.
    case lifecycleStateMismatch

    /// A callback admitted while the lifecycle surface is not foreground-active
    /// would contradict `accepted_while_window_open = true`.
    case appLifecycleNotForegroundActive(AppLifecycleActivationState)

    /// The snapshot record cannot claim a wall-clock receipt earlier than the
    /// event record from which it is derived.
    case snapshotWallTimePrecedesEvent(
        event: Int64,
        snapshot: Int64
    )

    /// Sequence-local monotonic time must increase from the event record to its
    /// dependent snapshot record.
    case snapshotMonotonicTimeNotAfterEvent(
        event: Int64,
        snapshot: Int64
    )
}

/// Why the network surface is unavailable in one newly opened observation
/// window before its first accepted path-update callback.
public enum NetworkObservationUnavailableReason: String, Sendable, Equatable {
    case awaitingFirstPathUpdate = "awaiting_first_path_update"
    case awaitingFreshPostReopenPathUpdate =
        "awaiting_fresh_post_reopen_path_update"
}

/// One finalized observed network snapshot retained by the runtime producer.
public struct NetworkObservedSnapshot: Sendable, Equatable {
    public let sessionID: LedgerIdentifier
    public let clockEpochID: LedgerIdentifier
    public let eventReference: LedgerRecordReference
    public let snapshotReference: LedgerRecordReference
    public let snapshotRole: NetworkPathStateSnapshotRole
    public let appLifecycleActivationState: AppLifecycleActivationState
    public let networkPathState: NetworkPathState

    public init(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        eventReference: LedgerRecordReference,
        snapshotReference: LedgerRecordReference,
        snapshotRole: NetworkPathStateSnapshotRole,
        appLifecycleActivationState: AppLifecycleActivationState,
        networkPathState: NetworkPathState
    ) {
        self.sessionID = sessionID
        self.clockEpochID = clockEpochID
        self.eventReference = eventReference
        self.snapshotReference = snapshotReference
        self.snapshotRole = snapshotRole
        self.appLifecycleActivationState = appLifecycleActivationState
        self.networkPathState = networkPathState
    }
}

/// Network-surface state inside one open observer session.
public enum NetworkObservationWindowAvailability: Sendable, Equatable {
    /// The session has opened, but no callback from that exact session has been
    /// accepted yet.
    case awaitingFreshCallback(
        reason: NetworkObservationUnavailableReason
    )

    /// At least one callback has been accepted in the exact current session.
    ///
    /// `firstFreshSnapshot` remains stable across later callbacks so a following
    /// coverage layer can bind the first post-reopen endpoint. `latestSnapshot`
    /// advances after every accepted callback.
    case observed(
        firstFreshSnapshot: NetworkObservedSnapshot,
        latestSnapshot: NetworkObservedSnapshot
    )
}

/// Complete network-observation state derived from accepted lifecycle
/// boundaries and path-update callback materializations.
public enum NetworkObservationStateMachineState: Sendable, Equatable {
    case awaitingFirstSession

    case observationWindowOpen(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        availability: NetworkObservationWindowAvailability,
        precedingObservationGap: SessionBoundaryObservationGap?,
        retainedGapSourceSnapshot: NetworkObservedSnapshot?
    )

    case observationWindowClosed(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        closeBoundary: LedgerRecordReference,
        retainedGapSourceSnapshot: NetworkObservedSnapshot?
    )

    case sessionTerminated(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        terminalBoundary: LedgerRecordReference,
        retainedGapSourceSnapshot: NetworkObservedSnapshot?
    )

    public var currentSessionID: LedgerIdentifier? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(sessionID, _, _, _, _, _),
             let .observationWindowClosed(sessionID, _, _, _),
             let .sessionTerminated(sessionID, _, _, _):
            sessionID
        }
    }

    public var currentClockEpochID: LedgerIdentifier? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, clockEpochID, _, _, _, _),
             let .observationWindowClosed(_, clockEpochID, _, _),
             let .sessionTerminated(_, clockEpochID, _, _):
            clockEpochID
        }
    }

    /// Latest snapshot in the current or most recently closed session.
    public var latestObservedSnapshot: NetworkObservedSnapshot? {
        switch self {
        case .awaitingFirstSession:
            return nil
        case let .observationWindowOpen(_, _, _, availability, _, _):
            guard case let .observed(_, latestSnapshot) = availability else {
                return nil
            }
            return latestSnapshot
        case let .observationWindowClosed(_, _, _, retained),
             let .sessionTerminated(_, _, _, retained):
            return retained
        }
    }

    public var precedingObservationGap: SessionBoundaryObservationGap? {
        guard case let .observationWindowOpen(_, _, _, _, gap, _) = self else {
            return nil
        }
        return gap
    }

    public var retainedGapSourceSnapshot: NetworkObservedSnapshot? {
        switch self {
        case .awaitingFirstSession:
            nil
        case let .observationWindowOpen(_, _, _, _, _, retained),
             let .observationWindowClosed(_, _, _, retained),
             let .sessionTerminated(_, _, _, retained):
            retained
        }
    }
}

/// Immutable normalized input for one received `NWPathMonitor` callback.
///
/// The Apple adapter derives `networkPathState` once from the callback argument,
/// captures the lifecycle state on the main actor, and submits this value to the
/// serial ledger ingress. There is no `currentPath` access in this type or in the
/// state machine.
public struct NetworkPathUpdateObservation: Sendable, Equatable {
    public let eventID: LedgerIdentifier
    public let eventRecordID: LedgerIdentifier
    public let eventRecordedWallTimeUnixNS: Int64
    public let eventMonotonicTimeNS: Int64

    public let snapshotID: LedgerIdentifier
    public let snapshotRecordID: LedgerIdentifier
    public let snapshotRecordedWallTimeUnixNS: Int64
    public let snapshotMonotonicTimeNS: Int64

    public let sessionID: LedgerIdentifier
    public let clockEpochID: LedgerIdentifier
    public let appLifecycleActivationState: AppLifecycleActivationState
    public let networkPathState: NetworkPathState

    public init(
        eventID: LedgerIdentifier,
        eventRecordID: LedgerIdentifier,
        eventRecordedWallTimeUnixNS: Int64,
        eventMonotonicTimeNS: Int64,
        snapshotID: LedgerIdentifier,
        snapshotRecordID: LedgerIdentifier,
        snapshotRecordedWallTimeUnixNS: Int64,
        snapshotMonotonicTimeNS: Int64,
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        appLifecycleActivationState: AppLifecycleActivationState,
        networkPathState: NetworkPathState
    ) {
        self.eventID = eventID
        self.eventRecordID = eventRecordID
        self.eventRecordedWallTimeUnixNS = eventRecordedWallTimeUnixNS
        self.eventMonotonicTimeNS = eventMonotonicTimeNS
        self.snapshotID = snapshotID
        self.snapshotRecordID = snapshotRecordID
        self.snapshotRecordedWallTimeUnixNS = snapshotRecordedWallTimeUnixNS
        self.snapshotMonotonicTimeNS = snapshotMonotonicTimeNS
        self.sessionID = sessionID
        self.clockEpochID = clockEpochID
        self.appLifecycleActivationState = appLifecycleActivationState
        self.networkPathState = networkPathState
    }
}

/// Result of one admitted path-update callback.
public struct NetworkPathObservationResult: Sendable, Equatable {
    public let eventRecord: LedgerRecordEnvelope
    public let snapshotRecord: LedgerRecordEnvelope
    public let observedSnapshot: NetworkObservedSnapshot

    /// Previous observed snapshot in the same session, if one existed.
    public let previousSnapshotInSession: NetworkObservedSnapshot?

    /// Exact normalized fields changed from the previous same-session snapshot.
    ///
    /// `nil` means no previous same-session endpoint exists. An empty array means
    /// the callback was retained as evidence but no transition record may be
    /// emitted under the zero-normalized-difference rule.
    public let changedFieldsFromPreviousSnapshot: [NetworkPathStateField]?

    /// Completed lifecycle gap carried into this open session, when present.
    public let precedingObservationGap: SessionBoundaryObservationGap?

    /// Last observed snapshot from the preceding session, when available.
    public let retainedGapSourceSnapshot: NetworkObservedSnapshot?

    public init(
        eventRecord: LedgerRecordEnvelope,
        snapshotRecord: LedgerRecordEnvelope,
        observedSnapshot: NetworkObservedSnapshot,
        previousSnapshotInSession: NetworkObservedSnapshot?,
        changedFieldsFromPreviousSnapshot: [NetworkPathStateField]?,
        precedingObservationGap: SessionBoundaryObservationGap?,
        retainedGapSourceSnapshot: NetworkObservedSnapshot?
    ) {
        self.eventRecord = eventRecord
        self.snapshotRecord = snapshotRecord
        self.observedSnapshot = observedSnapshot
        self.previousSnapshotInSession = previousSnapshotInSession
        self.changedFieldsFromPreviousSnapshot = changedFieldsFromPreviousSnapshot
        self.precedingObservationGap = precedingObservationGap
        self.retainedGapSourceSnapshot = retainedGapSourceSnapshot
    }
}

/// Consistent value snapshot of network state, lifecycle state, and the shared
/// ordered record chain.
public struct NetworkObservationStateMachineSnapshot: Sendable, Equatable {
    public let networkState: NetworkObservationStateMachineState
    public let lifecycleState: SessionBoundaryStateMachineState
    public let chain: LedgerRecordChainSnapshot

    public init(
        networkState: NetworkObservationStateMachineState,
        lifecycleState: SessionBoundaryStateMachineState,
        chain: LedgerRecordChainSnapshot
    ) {
        self.networkState = networkState
        self.lifecycleState = lifecycleState
        self.chain = chain
    }
}

/// Actor-isolated cross-source ingress for Device Ledger v0 lifecycle boundaries
/// and normalized Network.framework path-update callbacks.
///
/// This actor owns the `SessionBoundaryStateMachine` used with the supplied
/// ordered chain. Callers must route lifecycle and network callbacks through this
/// actor and must not append records independently to the same chain. The actor's
/// explicit non-reentrant operation boundary keeps lifecycle state, network
/// state, and chain materialization aligned across actor suspension points.
///
/// One admitted path update produces exactly two dependent records through the
/// chain's atomic append transaction:
///
/// normalized callback argument
/// → observation-event record
/// → exact event reference
/// → callback-bound state-snapshot record
///
/// The state machine records every admitted callback, including a callback whose
/// normalized state equals the prior state. It does not create coverage or
/// transition records; a later layer consumes the returned endpoint relation.
public actor NetworkObservationStateMachine {
    public nonisolated let ledgerID: LedgerIdentifier
    public nonisolated let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public nonisolated let recordStatus: LedgerRecordStatus

    private let chain: LedgerRecordChain
    private let lifecycle: SessionBoundaryStateMachine
    private var state: NetworkObservationStateMachineState = .awaitingFirstSession
    private var operationInProgress = false

    public init(
        chain: LedgerRecordChain
    ) {
        self.chain = chain
        lifecycle = SessionBoundaryStateMachine(chain: chain)
        ledgerID = chain.ledgerID
        observerPublicKeyFingerprintSHA256 = chain.observerPublicKeyFingerprintSHA256
        recordStatus = chain.recordStatus
    }

    /// Opens the first or next observer session through the owned lifecycle
    /// machine and resets the network surface to unavailable until a callback
    /// from that exact session is accepted.
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

        let retainedSource = state.latestObservedSnapshot
        let result = try await lifecycle.sceneDidBecomeActive(
            boundaryID: boundaryID,
            recordID: recordID,
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            monotonicTimeNS: monotonicTimeNS
        )

        guard case let .recorded(record, completedGap) = result else {
            return result
        }

        let reason: NetworkObservationUnavailableReason =
            completedGap == nil
            ? .awaitingFirstPathUpdate
            : .awaitingFreshPostReopenPathUpdate

        state = .observationWindowOpen(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            openBoundary: record.reference,
            availability: .awaitingFreshCallback(reason: reason),
            precedingObservationGap: completedGap,
            retainedGapSourceSnapshot: completedGap == nil ? nil : retainedSource
        )

        return result
    }

    /// Closes the current observation window through the owned lifecycle
    /// machine. The most recent observed snapshot is retained only as a possible
    /// source endpoint for the following explicit gap relation.
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

        let retainedSource = state.latestObservedSnapshot
        let currentClockEpochID = state.currentClockEpochID
        let result = try await lifecycle.sceneWillResignActive(
            boundaryID: boundaryID,
            recordID: recordID,
            sessionID: sessionID,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            monotonicTimeNS: monotonicTimeNS
        )

        guard case let .recorded(record, _) = result,
              let currentClockEpochID else {
            return result
        }

        state = .observationWindowClosed(
            sessionID: sessionID,
            clockEpochID: currentClockEpochID,
            closeBoundary: record.reference,
            retainedGapSourceSnapshot: retainedSource
        )

        return result
    }

    /// Terminates the current observer session through the owned lifecycle
    /// machine. A direct disconnect preserves the latest observed snapshot only
    /// as the source endpoint for a possible later interrupted relation.
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

        let retainedSource = state.latestObservedSnapshot
        let currentClockEpochID = state.currentClockEpochID
        let result = try await lifecycle.sceneDidDisconnect(
            boundaryID: boundaryID,
            recordID: recordID,
            sessionID: sessionID,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            monotonicTimeNS: monotonicTimeNS
        )

        guard case let .recorded(record, _) = result,
              let currentClockEpochID else {
            return result
        }

        state = .sessionTerminated(
            sessionID: sessionID,
            clockEpochID: currentClockEpochID,
            terminalBoundary: record.reference,
            retainedGapSourceSnapshot: retainedSource
        )

        return result
    }

    /// Admits and materializes one immutable normalized path-update callback.
    ///
    /// The method proves that the named session and epoch are exactly current,
    /// the lifecycle window remains open, and the lifecycle surface was captured
    /// as foreground-active. It then atomically appends the event and its bound
    /// snapshot. No state changes are committed unless both records finalize.
    @discardableResult
    public func observePathUpdate(
        _ observation: NetworkPathUpdateObservation
    ) async throws -> NetworkPathObservationResult {
        try beginOperation()
        defer { endOperation() }

        guard case let .observationWindowOpen(
            currentSessionID,
            currentClockEpochID,
            openBoundary,
            availability,
            precedingGap,
            retainedGapSource
        ) = state else {
            throw NetworkObservationStateMachineError.noOpenObservationWindow
        }

        guard observation.sessionID == currentSessionID else {
            throw NetworkObservationStateMachineError.callbackSessionMismatch(
                expected: currentSessionID,
                actual: observation.sessionID
            )
        }
        guard observation.clockEpochID == currentClockEpochID else {
            throw NetworkObservationStateMachineError.callbackClockEpochMismatch(
                expected: currentClockEpochID,
                actual: observation.clockEpochID
            )
        }
        guard observation.appLifecycleActivationState == .foregroundActive else {
            throw NetworkObservationStateMachineError.appLifecycleNotForegroundActive(
                observation.appLifecycleActivationState
            )
        }
        guard observation.snapshotRecordedWallTimeUnixNS >=
                observation.eventRecordedWallTimeUnixNS else {
            throw NetworkObservationStateMachineError.snapshotWallTimePrecedesEvent(
                event: observation.eventRecordedWallTimeUnixNS,
                snapshot: observation.snapshotRecordedWallTimeUnixNS
            )
        }
        guard observation.snapshotMonotonicTimeNS >
                observation.eventMonotonicTimeNS else {
            throw NetworkObservationStateMachineError.snapshotMonotonicTimeNotAfterEvent(
                event: observation.eventMonotonicTimeNS,
                snapshot: observation.snapshotMonotonicTimeNS
            )
        }

        let lifecycleSnapshot = try await lifecycle.snapshot()
        guard case let .observationWindowOpen(
            lifecycleSessionID,
            lifecycleClockEpochID,
            lifecycleOpenBoundary,
            _,
            _
        ) = lifecycleSnapshot.state,
              lifecycleSessionID == currentSessionID,
              lifecycleClockEpochID == currentClockEpochID,
              lifecycleOpenBoundary == openBoundary else {
            throw NetworkObservationStateMachineError.lifecycleStateMismatch
        }

        let previousSnapshot: NetworkObservedSnapshot?
        let firstFreshSnapshot: NetworkObservedSnapshot?
        switch availability {
        case .awaitingFreshCallback:
            previousSnapshot = nil
            firstFreshSnapshot = nil
        case let .observed(first, latest):
            previousSnapshot = latest
            firstFreshSnapshot = first
        }

        let snapshotRole: NetworkPathStateSnapshotRole =
            previousSnapshot != nil ||
            (precedingGap != nil && retainedGapSource != nil)
            ? .targetEndpoint
            : .sourceEndpoint

        let eventPayload = NetworkPathObservationEventPayload(
            eventID: observation.eventID,
            targetProjection: observation.networkPathState
        )
        let eventDraft = eventPayload.recordDraft(
            recordID: observation.eventRecordID,
            recordedWallTimeUnixNS: observation.eventRecordedWallTimeUnixNS,
            sessionID: currentSessionID,
            clockEpochID: currentClockEpochID,
            monotonicTimeNS: observation.eventMonotonicTimeNS
        )

        let pair = try await chain.appendAtomically(
            first: eventDraft,
            makeSecondDraft: { eventRecord in
                let snapshotPayload = NetworkPathStateSnapshotPayload(
                    snapshotID: observation.snapshotID,
                    snapshotRole: snapshotRole,
                    sourceEventBinding: eventRecord.reference,
                    appLifecycleActivationState:
                        observation.appLifecycleActivationState,
                    networkPathState: observation.networkPathState
                )
                return snapshotPayload.recordDraft(
                    recordID: observation.snapshotRecordID,
                    recordedWallTimeUnixNS:
                        observation.snapshotRecordedWallTimeUnixNS,
                    sessionID: currentSessionID,
                    clockEpochID: currentClockEpochID,
                    monotonicTimeNS: observation.snapshotMonotonicTimeNS
                )
            }
        )

        let observedSnapshot = NetworkObservedSnapshot(
            sessionID: currentSessionID,
            clockEpochID: currentClockEpochID,
            eventReference: pair.first.reference,
            snapshotReference: pair.second.reference,
            snapshotRole: snapshotRole,
            appLifecycleActivationState: observation.appLifecycleActivationState,
            networkPathState: observation.networkPathState
        )

        let retainedFirstFreshSnapshot = firstFreshSnapshot ?? observedSnapshot
        state = .observationWindowOpen(
            sessionID: currentSessionID,
            clockEpochID: currentClockEpochID,
            openBoundary: openBoundary,
            availability: .observed(
                firstFreshSnapshot: retainedFirstFreshSnapshot,
                latestSnapshot: observedSnapshot
            ),
            precedingObservationGap: precedingGap,
            retainedGapSourceSnapshot: retainedGapSource
        )

        let changedFields = previousSnapshot.map { previous in
            NetworkPathStateField.allCases.filter { field in
                previous.networkPathState.canonicalValue(for: field) !=
                    observation.networkPathState.canonicalValue(for: field)
            }
        }

        return NetworkPathObservationResult(
            eventRecord: pair.first,
            snapshotRecord: pair.second,
            observedSnapshot: observedSnapshot,
            previousSnapshotInSession: previousSnapshot,
            changedFieldsFromPreviousSnapshot: changedFields,
            precedingObservationGap: precedingGap,
            retainedGapSourceSnapshot: retainedGapSource
        )
    }

    /// Returns one consistent network, lifecycle, and chain snapshot.
    public func snapshot() async throws -> NetworkObservationStateMachineSnapshot {
        try beginOperation()
        defer { endOperation() }

        let lifecycleSnapshot = try await lifecycle.snapshot()
        return NetworkObservationStateMachineSnapshot(
            networkState: state,
            lifecycleState: lifecycleSnapshot.state,
            chain: lifecycleSnapshot.chain
        )
    }

    private func beginOperation() throws {
        guard !operationInProgress else {
            throw NetworkObservationStateMachineError.operationInProgress
        }
        operationInProgress = true
    }

    private func endOperation() {
        operationInProgress = false
    }
}
