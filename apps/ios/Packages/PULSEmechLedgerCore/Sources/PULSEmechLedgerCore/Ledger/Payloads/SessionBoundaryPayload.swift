import Foundation

/// Construction failures for the closed Device Ledger v0 session-boundary
/// payload.
public enum SessionBoundaryPayloadError: Error, Sendable, Equatable {
    /// Opening a new observer session cannot name that same session as its
    /// predecessor.
    case openedPreviousSessionMatchesCurrentSession(LedgerIdentifier)

    /// Closing or terminating payloads must be bound to the same session that
    /// appears in the record envelope scope.
    case boundarySessionMismatch(
        kind: SessionBoundaryKind,
        expected: LedgerIdentifier,
        actual: LedgerIdentifier
    )
}

/// The three session-boundary classes admitted by the Device Ledger v0 schema.
public enum SessionBoundaryKind: String, Sendable, Equatable, CaseIterable {
    case opened
    case observationWindowClosed = "observation_window_closed"
    case sessionTerminated = "session_terminated"
}

/// The only lifecycle callbacks represented by session-boundary records.
public enum SessionBoundaryLifecycleEvent: String, Sendable, Equatable {
    case sceneDidBecomeActive = "scene_did_become_active"
    case sceneWillResignActive = "scene_will_resign_active"
    case sceneDidDisconnect = "scene_did_disconnect"
}

/// Declares how repeated delivery of one lifecycle boundary is interpreted.
public enum SessionBoundaryDuplicateRule: String, Sendable, Equatable {
    case notApplicableNewSession = "not_applicable_new_session"
    case idempotentNoSecondGapStart = "idempotent_no_second_gap_start"
    case terminalOnceNoFutureEvents = "terminal_once_no_future_events"
}

/// Declares the network-surface state immediately after a session boundary.
public enum SessionBoundaryNetworkSurfaceState: String, Sendable, Equatable {
    case unavailableUntilFreshPathUpdate = "unavailable_until_fresh_path_update"
    case lastBoundValueRetainedForGapSourceOnly = "last_bound_value_retained_for_gap_source_only"
    case unavailableTerminal = "unavailable_terminal"
}

/// Observation-window state materialized by a session-boundary record.
public enum SessionBoundaryObservationWindowState: String, Sendable, Equatable {
    case open
    case closed
    case terminal
}

/// Closed typed representation of a Device Ledger v0 session-boundary payload.
///
/// Each case derives the complete set of schema-coupled fields. Callers cannot
/// combine an `opened` boundary with a close event, mark a window close as
/// terminal, or retain a network value after session termination.
///
/// Cross-record lifecycle ordering remains the responsibility of the session
/// observation state machine and the separately implemented verifier.
public enum SessionBoundaryPayload: Sendable, Equatable {
    /// Opens one new observer session and one new clock epoch.
    ///
    /// `previousSessionID` is `nil` for the first session and identifies the
    /// immediately preceding observer session for later openings.
    case opened(
        boundaryID: LedgerIdentifier,
        previousSessionID: LedgerIdentifier?
    )

    /// Closes the current observation window without terminating the session.
    ///
    /// `sessionID` is serialized as `previous_session_id` and must match the
    /// session carried by the record envelope scope.
    case observationWindowClosed(
        boundaryID: LedgerIdentifier,
        sessionID: LedgerIdentifier
    )

    /// Terminates the current observer session exactly once.
    ///
    /// `sessionID` is serialized as `previous_session_id` and must match the
    /// session carried by the record envelope scope.
    case sessionTerminated(
        boundaryID: LedgerIdentifier,
        sessionID: LedgerIdentifier
    )

    public var boundaryID: LedgerIdentifier {
        switch self {
        case let .opened(boundaryID, _),
             let .observationWindowClosed(boundaryID, _),
             let .sessionTerminated(boundaryID, _):
            boundaryID
        }
    }

    public var kind: SessionBoundaryKind {
        switch self {
        case .opened:
            .opened
        case .observationWindowClosed:
            .observationWindowClosed
        case .sessionTerminated:
            .sessionTerminated
        }
    }

    public var lifecycleEvent: SessionBoundaryLifecycleEvent {
        switch self {
        case .opened:
            .sceneDidBecomeActive
        case .observationWindowClosed:
            .sceneWillResignActive
        case .sessionTerminated:
            .sceneDidDisconnect
        }
    }

    public var duplicateBoundaryRule: SessionBoundaryDuplicateRule {
        switch self {
        case .opened:
            .notApplicableNewSession
        case .observationWindowClosed:
            .idempotentNoSecondGapStart
        case .sessionTerminated:
            .terminalOnceNoFutureEvents
        }
    }

    public var networkSurfaceAfterBoundary: SessionBoundaryNetworkSurfaceState {
        switch self {
        case .opened:
            .unavailableUntilFreshPathUpdate
        case .observationWindowClosed:
            .lastBoundValueRetainedForGapSourceOnly
        case .sessionTerminated:
            .unavailableTerminal
        }
    }

    public var observationWindowState: SessionBoundaryObservationWindowState {
        switch self {
        case .opened:
            .open
        case .observationWindowClosed:
            .closed
        case .sessionTerminated:
            .terminal
        }
    }

    public var previousSessionID: LedgerIdentifier? {
        switch self {
        case let .opened(_, previousSessionID):
            previousSessionID
        case let .observationWindowClosed(_, sessionID),
             let .sessionTerminated(_, sessionID):
            sessionID
        }
    }

    public var sessionTerminal: Bool {
        switch self {
        case .opened,
             .observationWindowClosed:
            false
        case .sessionTerminated:
            true
        }
    }

    /// Returns the exact canonical payload object stored in the record.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "boundary_id",
                value: boundaryID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "boundary_kind",
                value: canonicalString(kind.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "duplicate_boundary_rule",
                value: canonicalString(duplicateBoundaryRule.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "lifecycle_event",
                value: canonicalString(lifecycleEvent.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "network_surface_after_boundary",
                value: canonicalString(networkSurfaceAfterBoundary.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "observation_window_state",
                value: canonicalString(observationWindowState.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "payload_type",
                value: canonicalString(LedgerRecordType.sessionBoundary.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "previous_session_id",
                value: previousSessionID?.canonicalValue ?? .null
            ),
            try! CanonicalJSONObjectMember(
                key: "session_terminal",
                value: .boolean(sessionTerminal)
            ),
        ])
    }

    /// Returns the exact canonical payload bytes.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    /// Builds the corresponding session-scoped record draft.
    ///
    /// This method binds closing and terminal payloads to the exact current
    /// session carried by the record envelope. It also prevents a new session
    /// from naming itself as its predecessor.
    public func recordDraft(
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        monotonicTimeNS: Int64
    ) throws -> LedgerRecordDraft {
        switch self {
        case let .opened(_, previousSessionID):
            if previousSessionID == sessionID {
                throw SessionBoundaryPayloadError
                    .openedPreviousSessionMatchesCurrentSession(sessionID)
            }

        case let .observationWindowClosed(_, expectedSessionID),
             let .sessionTerminated(_, expectedSessionID):
            guard expectedSessionID == sessionID else {
                throw SessionBoundaryPayloadError.boundarySessionMismatch(
                    kind: kind,
                    expected: expectedSessionID,
                    actual: sessionID
                )
            }
        }

        return LedgerRecordDraft(
            payload: canonicalValue(),
            recordID: recordID,
            recordType: .sessionBoundary,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            scope: .session(
                sessionID: sessionID,
                clockEpochID: clockEpochID,
                monotonicTimeNS: monotonicTimeNS
            )
        )
    }

    private func canonicalString(
        _ rawValue: String
    ) -> CanonicalJSONValue {
        .string(try! CanonicalJSONString(rawValue))
    }
}
