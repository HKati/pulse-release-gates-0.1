import Foundation

/// Admission and ordering failures for the Device Ledger v0 network-observation
/// state machine.
public enum NetworkObservationStateMachineError: Error, Sendable, Equatable {
    /// The observation ingress contract requires one serial caller. A second
    /// operation entering while this actor awaits a dependent actor is rejected
    /// rather than interleaved.
    case operationInProgress

    /// A terminal checkpoint has already closed the shared ledger. Lifecycle
    /// and observation mutation are forbidden after closure.
    case ledgerAlreadyClosed

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

    /// Every mechanically eligible endpoint relation must be materialized by
    /// the runtime producer in the same atomic callback transaction.
    case coverageMaterializationRequired(NetworkCoverageStatus)

    /// A caller cannot inject a coverage record when no prior observed endpoint
    /// relation exists.
    case coverageMaterializationNotPermitted

    /// Coverage materialization cannot claim receipt before its target snapshot.
    case coverageWallTimePrecedesTargetSnapshot(
        snapshot: Int64,
        coverage: Int64
    )

    /// Every changed mechanically eligible relation must materialize its exact
    /// transition in the same callback transaction.
    case transitionMaterializationRequired(NetworkTransitionClass)

    /// A caller cannot inject a transition when no changed endpoint relation
    /// exists.
    case transitionMaterializationNotPermitted

    /// Transition materialization cannot claim receipt before its bound
    /// coverage record.
    case transitionWallTimePrecedesCoverage(
        coverage: Int64,
        transition: Int64
    )

    /// Event-bound transitions are session-scoped and require a monotonic time.
    case eventBoundTransitionMonotonicTimeRequired

    /// Event-bound transition monotonic time must follow the target snapshot.
    case eventBoundTransitionMonotonicTimeNotAfterSnapshot(
        snapshot: Int64,
        transition: Int64
    )

    /// Endpoint-difference-only transitions are ledger-wide and cannot carry a
    /// monotonic time.
    case endpointDifferenceTransitionMonotonicTimeForbidden
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

    public var coverageEndpoint: NetworkCoverageEndpoint {
        NetworkCoverageEndpoint(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            snapshotReference: snapshotReference
        )
    }

    public var transitionEndpoint: NetworkTransitionEndpoint {
        NetworkTransitionEndpoint(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            snapshotReference: snapshotReference,
            sourceEventReference: eventReference,
            networkPathState: networkPathState
        )
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

/// Producer-supplied identities for one coverage record whose semantics are
/// derived entirely by `NetworkObservationStateMachine`.
public struct NetworkCoverageMaterializationInput: Sendable, Equatable {
    public let intervalID: LedgerIdentifier
    public let recordID: LedgerIdentifier
    public let recordedWallTimeUnixNS: Int64

    public init(
        intervalID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64
    ) {
        self.intervalID = intervalID
        self.recordID = recordID
        self.recordedWallTimeUnixNS = recordedWallTimeUnixNS
    }
}

/// Producer-supplied identities and timing for one transition record whose
/// semantics are derived entirely by `NetworkObservationStateMachine`.
public struct NetworkTransitionMaterializationInput: Sendable, Equatable {
    public let transitionID: LedgerIdentifier
    public let recordID: LedgerIdentifier
    public let recordedWallTimeUnixNS: Int64

    /// Required only for the derived event-bound class. The state machine
    /// rejects this value for endpoint-difference-only transitions.
    public let eventBoundMonotonicTimeNS: Int64?

    public init(
        transitionID: LedgerIdentifier,
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        eventBoundMonotonicTimeNS: Int64? = nil
    ) {
        self.transitionID = transitionID
        self.recordID = recordID
        self.recordedWallTimeUnixNS = recordedWallTimeUnixNS
        self.eventBoundMonotonicTimeNS = eventBoundMonotonicTimeNS
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
    public let coverageMaterialization: NetworkCoverageMaterializationInput?
    public let transitionMaterialization: NetworkTransitionMaterializationInput?

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
        networkPathState: NetworkPathState,
        coverageMaterialization: NetworkCoverageMaterializationInput? = nil,
        transitionMaterialization: NetworkTransitionMaterializationInput? = nil
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
        self.coverageMaterialization = coverageMaterialization
        self.transitionMaterialization = transitionMaterialization
    }
}

/// Result of one admitted path-update callback.
public struct NetworkPathObservationResult: Sendable, Equatable {
    public let eventRecord: LedgerRecordEnvelope
    public let snapshotRecord: LedgerRecordEnvelope
    public let coverageRecord: LedgerRecordEnvelope?
    public let coverageRelation: NetworkCoverageRelation?
    public let transitionRecord: LedgerRecordEnvelope?
    public let transitionRelation: NetworkTransitionRelation?
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
        coverageRecord: LedgerRecordEnvelope?,
        coverageRelation: NetworkCoverageRelation?,
        transitionRecord: LedgerRecordEnvelope?,
        transitionRelation: NetworkTransitionRelation?,
        observedSnapshot: NetworkObservedSnapshot,
        previousSnapshotInSession: NetworkObservedSnapshot?,
        changedFieldsFromPreviousSnapshot: [NetworkPathStateField]?,
        precedingObservationGap: SessionBoundaryObservationGap?,
        retainedGapSourceSnapshot: NetworkObservedSnapshot?
    ) {
        self.eventRecord = eventRecord
        self.snapshotRecord = snapshotRecord
        self.coverageRecord = coverageRecord
        self.coverageRelation = coverageRelation
        self.transitionRecord = transitionRecord
        self.transitionRelation = transitionRelation
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
    public let ledgerClosure: DeviceTransitionLedgerClosure?

    public init(
        networkState: NetworkObservationStateMachineState,
        lifecycleState: SessionBoundaryStateMachineState,
        chain: LedgerRecordChainSnapshot,
        ledgerClosure: DeviceTransitionLedgerClosure? = nil
    ) {
        self.networkState = networkState
        self.lifecycleState = lifecycleState
        self.chain = chain
        self.ledgerClosure = ledgerClosure
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
/// One admitted path update always produces an observation event and its bound
/// snapshot. When a prior observed endpoint relation exists, the same atomic
/// transaction also produces its continuous or interrupted coverage record:
///
/// normalized callback argument
/// → observation-event record
/// → exact event reference
/// → callback-bound state-snapshot record
/// → exact coverage relation, when mechanically eligible
/// → exact transition, when at least one normalized relation field changed
///
/// The state machine records every admitted callback. Equal normalized states
/// retain event, snapshot, and coverage evidence without a transition record.
public actor NetworkObservationStateMachine {
    private enum PendingCoverageRelation: Sendable {
        case absent
        case continuous(
            source: NetworkObservedSnapshot,
            input: NetworkCoverageMaterializationInput
        )
        case interrupted(
            source: NetworkObservedSnapshot,
            gap: SessionBoundaryObservationGap,
            input: NetworkCoverageMaterializationInput
        )

        var status: NetworkCoverageStatus? {
            switch self {
            case .absent:
                nil
            case .continuous:
                .continuous
            case .interrupted:
                .interrupted
            }
        }

        var input: NetworkCoverageMaterializationInput? {
            switch self {
            case .absent:
                nil
            case let .continuous(_, input),
                 let .interrupted(_, _, input):
                input
            }
        }

        func materializedRelation(
            target: NetworkCoverageEndpoint
        ) -> NetworkCoverageRelation? {
            switch self {
            case .absent:
                nil
            case let .continuous(source, _):
                .continuous(
                    source: source.coverageEndpoint,
                    target: target
                )
            case let .interrupted(source, gap, _):
                .interrupted(
                    source: source.coverageEndpoint,
                    target: target,
                    gap: gap
                )
            }
        }
    }

    public nonisolated let ledgerID: LedgerIdentifier
    public nonisolated let observerPublicKeyFingerprintSHA256: SHA256HexDigest
    public nonisolated let recordStatus: LedgerRecordStatus

    private let chain: LedgerRecordChain
    private let lifecycle: SessionBoundaryStateMachine
    private var state: NetworkObservationStateMachineState = .awaitingFirstSession
    private var ledgerClosure: DeviceTransitionLedgerClosure?
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
        try requireLedgerOpen()

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
        try requireLedgerOpen()

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
        try requireLedgerOpen()

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
    /// Every callback produces one event/snapshot pair. When an exact prior
    /// endpoint relation exists, its coverage record is prepared and committed in
    /// the same chain transaction. No event-only, snapshot-only, or uncovered
    /// eligible relation can survive a failed preparation.
    @discardableResult
    public func observePathUpdate(
        _ observation: NetworkPathUpdateObservation
    ) async throws -> NetworkPathObservationResult {
        try beginOperation()
        defer { endOperation() }
        try requireLedgerOpen()

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

        let pendingCoverage: PendingCoverageRelation
        if let previousSnapshot {
            guard let coverageInput = observation.coverageMaterialization else {
                throw NetworkObservationStateMachineError
                    .coverageMaterializationRequired(.continuous)
            }
            pendingCoverage = .continuous(
                source: previousSnapshot,
                input: coverageInput
            )
        } else if let precedingGap,
                  let retainedGapSource {
            guard let coverageInput = observation.coverageMaterialization else {
                throw NetworkObservationStateMachineError
                    .coverageMaterializationRequired(.interrupted)
            }
            pendingCoverage = .interrupted(
                source: retainedGapSource,
                gap: precedingGap,
                input: coverageInput
            )
        } else {
            guard observation.coverageMaterialization == nil else {
                throw NetworkObservationStateMachineError
                    .coverageMaterializationNotPermitted
            }
            pendingCoverage = .absent
        }

        if let coverageInput = pendingCoverage.input,
           coverageInput.recordedWallTimeUnixNS <
            observation.snapshotRecordedWallTimeUnixNS {
            throw NetworkObservationStateMachineError
                .coverageWallTimePrecedesTargetSnapshot(
                    snapshot: observation.snapshotRecordedWallTimeUnixNS,
                    coverage: coverageInput.recordedWallTimeUnixNS
                )
        }

        let relationSource: NetworkObservedSnapshot?
        switch pendingCoverage {
        case .absent:
            relationSource = nil
        case let .continuous(source, _),
             let .interrupted(source, _, _):
            relationSource = source
        }

        let relationChangedFields = relationSource.map { source in
            NetworkPathStateField.allCases.filter { field in
                source.networkPathState.canonicalValue(for: field) !=
                    observation.networkPathState.canonicalValue(for: field)
            }
        }

        let requiredTransitionClass: NetworkTransitionClass?
        if let relationChangedFields,
           !relationChangedFields.isEmpty {
            switch pendingCoverage {
            case .absent:
                requiredTransitionClass = nil
            case .continuous:
                requiredTransitionClass = .eventBound
            case .interrupted:
                requiredTransitionClass = .endpointDifferenceOnly
            }
        } else {
            requiredTransitionClass = nil
        }

        let transitionInput: NetworkTransitionMaterializationInput?
        if let requiredTransitionClass {
            guard let supplied = observation.transitionMaterialization else {
                throw NetworkObservationStateMachineError
                    .transitionMaterializationRequired(requiredTransitionClass)
            }
            guard let coverageInput = pendingCoverage.input else {
                preconditionFailure(
                    "A required transition must have a materialized coverage relation"
                )
            }
            guard supplied.recordedWallTimeUnixNS >=
                    coverageInput.recordedWallTimeUnixNS else {
                throw NetworkObservationStateMachineError
                    .transitionWallTimePrecedesCoverage(
                        coverage: coverageInput.recordedWallTimeUnixNS,
                        transition: supplied.recordedWallTimeUnixNS
                    )
            }

            switch requiredTransitionClass {
            case .eventBound:
                guard let monotonicTimeNS =
                        supplied.eventBoundMonotonicTimeNS else {
                    throw NetworkObservationStateMachineError
                        .eventBoundTransitionMonotonicTimeRequired
                }
                guard monotonicTimeNS >
                        observation.snapshotMonotonicTimeNS else {
                    throw NetworkObservationStateMachineError
                        .eventBoundTransitionMonotonicTimeNotAfterSnapshot(
                            snapshot: observation.snapshotMonotonicTimeNS,
                            transition: monotonicTimeNS
                        )
                }

            case .endpointDifferenceOnly:
                guard supplied.eventBoundMonotonicTimeNS == nil else {
                    throw NetworkObservationStateMachineError
                        .endpointDifferenceTransitionMonotonicTimeForbidden
                }
            }

            transitionInput = supplied
        } else {
            guard observation.transitionMaterialization == nil else {
                throw NetworkObservationStateMachineError
                    .transitionMaterializationNotPermitted
            }
            transitionInput = nil
        }

        let snapshotRole: NetworkPathStateSnapshotRole =
            pendingCoverage.status == nil
            ? .sourceEndpoint
            : .targetEndpoint

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

        let makeSnapshotDraft: @Sendable (
            LedgerRecordEnvelope
        ) throws -> LedgerRecordDraft = { eventRecord in
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

        let eventRecord: LedgerRecordEnvelope
        let snapshotRecord: LedgerRecordEnvelope
        let coverageRecord: LedgerRecordEnvelope?
        let transitionRecord: LedgerRecordEnvelope?

        switch pendingCoverage {
        case .absent:
            let pair = try await chain.appendAtomically(
                first: eventDraft,
                makeSecondDraft: makeSnapshotDraft
            )
            eventRecord = pair.first
            snapshotRecord = pair.second
            coverageRecord = nil
            transitionRecord = nil

        case let .continuous(source, coverageInput):
            let makeCoverageDraft: @Sendable (
                LedgerRecordEnvelope,
                LedgerRecordEnvelope
            ) throws -> LedgerRecordDraft = { _, finalizedSnapshot in
                let target = NetworkCoverageEndpoint(
                    sessionID: currentSessionID,
                    clockEpochID: currentClockEpochID,
                    snapshotReference: finalizedSnapshot.reference
                )
                let payload = try NetworkCoverageIntervalPayload(
                    intervalID: coverageInput.intervalID,
                    relation: .continuous(
                        source: source.coverageEndpoint,
                        target: target
                    )
                )
                return payload.recordDraft(
                    recordID: coverageInput.recordID,
                    recordedWallTimeUnixNS:
                        coverageInput.recordedWallTimeUnixNS
                )
            }

            if let transitionInput {
                let quadruple = try await chain.appendAtomically(
                    first: eventDraft,
                    makeSecondDraft: makeSnapshotDraft,
                    makeThirdDraft: makeCoverageDraft,
                    makeFourthDraft: {
                        finalizedEvent,
                        finalizedSnapshot,
                        finalizedCoverage in
                        let target = NetworkTransitionEndpoint(
                            sessionID: currentSessionID,
                            clockEpochID: currentClockEpochID,
                            snapshotReference: finalizedSnapshot.reference,
                            sourceEventReference: finalizedEvent.reference,
                            networkPathState: observation.networkPathState
                        )
                        let coverageRelation = NetworkCoverageRelation.continuous(
                            source: source.coverageEndpoint,
                            target: target.coverageEndpoint
                        )
                        let relation = NetworkTransitionRelation.eventBound(
                            source: source.transitionEndpoint,
                            target: target,
                            coverageRelation: coverageRelation,
                            coverageReference: finalizedCoverage.reference
                        )
                        let payload = try NetworkTransitionPayload(
                            transitionID: transitionInput.transitionID,
                            relation: relation
                        )
                        return try payload.recordDraft(
                            recordID: transitionInput.recordID,
                            recordedWallTimeUnixNS:
                                transitionInput.recordedWallTimeUnixNS,
                            eventBoundMonotonicTimeNS:
                                transitionInput.eventBoundMonotonicTimeNS
                        )
                    }
                )
                eventRecord = quadruple.first
                snapshotRecord = quadruple.second
                coverageRecord = quadruple.third
                transitionRecord = quadruple.fourth
            } else {
                let triple = try await chain.appendAtomically(
                    first: eventDraft,
                    makeSecondDraft: makeSnapshotDraft,
                    makeThirdDraft: makeCoverageDraft
                )
                eventRecord = triple.first
                snapshotRecord = triple.second
                coverageRecord = triple.third
                transitionRecord = nil
            }

        case let .interrupted(source, gap, coverageInput):
            let makeCoverageDraft: @Sendable (
                LedgerRecordEnvelope,
                LedgerRecordEnvelope
            ) throws -> LedgerRecordDraft = { _, finalizedSnapshot in
                let target = NetworkCoverageEndpoint(
                    sessionID: currentSessionID,
                    clockEpochID: currentClockEpochID,
                    snapshotReference: finalizedSnapshot.reference
                )
                let payload = try NetworkCoverageIntervalPayload(
                    intervalID: coverageInput.intervalID,
                    relation: .interrupted(
                        source: source.coverageEndpoint,
                        target: target,
                        gap: gap
                    )
                )
                return payload.recordDraft(
                    recordID: coverageInput.recordID,
                    recordedWallTimeUnixNS:
                        coverageInput.recordedWallTimeUnixNS
                )
            }

            if let transitionInput {
                let quadruple = try await chain.appendAtomically(
                    first: eventDraft,
                    makeSecondDraft: makeSnapshotDraft,
                    makeThirdDraft: makeCoverageDraft,
                    makeFourthDraft: {
                        finalizedEvent,
                        finalizedSnapshot,
                        finalizedCoverage in
                        let target = NetworkTransitionEndpoint(
                            sessionID: currentSessionID,
                            clockEpochID: currentClockEpochID,
                            snapshotReference: finalizedSnapshot.reference,
                            sourceEventReference: finalizedEvent.reference,
                            networkPathState: observation.networkPathState
                        )
                        let coverageRelation = NetworkCoverageRelation.interrupted(
                            source: source.coverageEndpoint,
                            target: target.coverageEndpoint,
                            gap: gap
                        )
                        let relation =
                            NetworkTransitionRelation.endpointDifferenceOnly(
                                source: source.transitionEndpoint,
                                target: target,
                                coverageRelation: coverageRelation,
                                coverageReference: finalizedCoverage.reference
                            )
                        let payload = try NetworkTransitionPayload(
                            transitionID: transitionInput.transitionID,
                            relation: relation
                        )
                        return try payload.recordDraft(
                            recordID: transitionInput.recordID,
                            recordedWallTimeUnixNS:
                                transitionInput.recordedWallTimeUnixNS,
                            eventBoundMonotonicTimeNS:
                                transitionInput.eventBoundMonotonicTimeNS
                        )
                    }
                )
                eventRecord = quadruple.first
                snapshotRecord = quadruple.second
                coverageRecord = quadruple.third
                transitionRecord = quadruple.fourth
            } else {
                let triple = try await chain.appendAtomically(
                    first: eventDraft,
                    makeSecondDraft: makeSnapshotDraft,
                    makeThirdDraft: makeCoverageDraft
                )
                eventRecord = triple.first
                snapshotRecord = triple.second
                coverageRecord = triple.third
                transitionRecord = nil
            }
        }

        let observedSnapshot = NetworkObservedSnapshot(
            sessionID: currentSessionID,
            clockEpochID: currentClockEpochID,
            eventReference: eventRecord.reference,
            snapshotReference: snapshotRecord.reference,
            snapshotRole: snapshotRole,
            appLifecycleActivationState: observation.appLifecycleActivationState,
            networkPathState: observation.networkPathState
        )
        let coverageRelation = pendingCoverage.materializedRelation(
            target: observedSnapshot.coverageEndpoint
        )

        let transitionRelation: NetworkTransitionRelation?
        if transitionRecord != nil,
           let coverageRecord,
           let coverageRelation {
            switch pendingCoverage {
            case .absent:
                transitionRelation = nil
            case let .continuous(source, _):
                transitionRelation = .eventBound(
                    source: source.transitionEndpoint,
                    target: observedSnapshot.transitionEndpoint,
                    coverageRelation: coverageRelation,
                    coverageReference: coverageRecord.reference
                )
            case let .interrupted(source, _, _):
                transitionRelation = .endpointDifferenceOnly(
                    source: source.transitionEndpoint,
                    target: observedSnapshot.transitionEndpoint,
                    coverageRelation: coverageRelation,
                    coverageReference: coverageRecord.reference
                )
            }
        } else {
            transitionRelation = nil
        }

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
            eventRecord: eventRecord,
            snapshotRecord: snapshotRecord,
            coverageRecord: coverageRecord,
            coverageRelation: coverageRelation,
            transitionRecord: transitionRecord,
            transitionRelation: transitionRelation,
            observedSnapshot: observedSnapshot,
            previousSnapshotInSession: previousSnapshot,
            changedFieldsFromPreviousSnapshot: changedFields,
            precedingObservationGap: precedingGap,
            retainedGapSourceSnapshot: retainedGapSource
        )
    }

    /// Atomically closes the current record chain with one terminal checkpoint
    /// and materializes the complete canonical ledger document.
    ///
    /// The lifecycle and network state must still describe the same accepted
    /// session relation. Checkpoint projection, checkpoint finalization, and
    /// document construction complete before the chain commits its terminal
    /// checkpoint.
    @discardableResult
    public func closeLedger(
        _ input: LedgerCheckpointMaterializationInput,
        observerIdentity: DeviceLedgerObserverIdentity
    ) async throws -> DeviceTransitionLedgerClosure {
        try beginOperation()
        defer { endOperation() }
        try requireLedgerOpen()

        let lifecycleSnapshot = try await lifecycle.snapshot()
        guard lifecycleStateMatches(lifecycleSnapshot.state) else {
            throw NetworkObservationStateMachineError.lifecycleStateMismatch
        }

        let closure = try await chain.closeAndMaterializeLedger(
            input,
            observerIdentity: observerIdentity
        )
        ledgerClosure = closure
        return closure
    }

    /// Returns one consistent network, lifecycle, chain, and terminal-ledger
    /// snapshot.
    public func snapshot() async throws -> NetworkObservationStateMachineSnapshot {
        try beginOperation()
        defer { endOperation() }

        let lifecycleSnapshot = try await lifecycle.snapshot()
        return NetworkObservationStateMachineSnapshot(
            networkState: state,
            lifecycleState: lifecycleSnapshot.state,
            chain: lifecycleSnapshot.chain,
            ledgerClosure: ledgerClosure
        )
    }

    private func requireLedgerOpen() throws {
        guard ledgerClosure == nil else {
            throw NetworkObservationStateMachineError.ledgerAlreadyClosed
        }
    }

    private func lifecycleStateMatches(
        _ lifecycleState: SessionBoundaryStateMachineState
    ) -> Bool {
        switch (state, lifecycleState) {
        case (.awaitingFirstSession, .awaitingFirstSession):
            return true

        case let (
            .observationWindowOpen(
                sessionID,
                clockEpochID,
                openBoundary,
                _,
                precedingGap,
                _
            ),
            .observationWindowOpen(
                lifecycleSessionID,
                lifecycleClockEpochID,
                lifecycleOpenBoundary,
                _,
                lifecycleGap
            )
        ):
            return sessionID == lifecycleSessionID &&
                clockEpochID == lifecycleClockEpochID &&
                openBoundary == lifecycleOpenBoundary &&
                precedingGap == lifecycleGap

        case let (
            .observationWindowClosed(
                sessionID,
                clockEpochID,
                closeBoundary,
                _
            ),
            .observationWindowClosed(
                lifecycleSessionID,
                lifecycleClockEpochID,
                _,
                lifecycleCloseBoundary
            )
        ):
            return sessionID == lifecycleSessionID &&
                clockEpochID == lifecycleClockEpochID &&
                closeBoundary == lifecycleCloseBoundary

        case let (
            .sessionTerminated(
                sessionID,
                clockEpochID,
                terminalBoundary,
                _
            ),
            .sessionTerminated(
                lifecycleSessionID,
                lifecycleClockEpochID,
                _,
                _,
                lifecycleTerminalBoundary
            )
        ):
            return sessionID == lifecycleSessionID &&
                clockEpochID == lifecycleClockEpochID &&
                terminalBoundary == lifecycleTerminalBoundary

        default:
            return false
        }
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
