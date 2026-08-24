import Foundation

/// Closed typed representation of one admitted Network.framework path-update
/// callback in the Device Ledger v0 observation domain.
///
/// This payload is intentionally not publicly constructible. The following
/// network-observation state machine creates it only after proving that the
/// callback was accepted while the current observation window was open and the
/// named observer session was active.
///
/// The payload stores the normalized value derived from the exact callback
/// argument. It does not reopen `NWPathMonitor.currentPath`, identify an actor
/// that initiated the change, claim a physical measurement, or establish a
/// causal path.
public struct NetworkPathObservationEventPayload: Sendable, Equatable {
    public static let eventRole = "surface_observation"
    public static let eventType = "path_update_received"
    public static let initiatingCauseClaim = "none"
    public static let sourceInterface = "Network.framework NWPathMonitor.pathUpdateHandler"
    public static let surfaceID = "network_path"

    public let eventID: LedgerIdentifier
    public let targetProjection: NetworkPathState

    /// Creates one payload after observation-window admission has succeeded.
    ///
    /// This initializer is module-internal so external callers cannot create an
    /// `accepted_while_window_open = true` statement without passing through the
    /// network-observation state machine.
    init(
        eventID: LedgerIdentifier,
        targetProjection: NetworkPathState
    ) {
        self.eventID = eventID
        self.targetProjection = targetProjection
    }

    /// Returns the exact canonical event payload stored in the ledger record.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "accepted_while_window_open",
                value: .boolean(true)
            ),
            try! CanonicalJSONObjectMember(
                key: "event_id",
                value: eventID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "event_role",
                value: canonicalString(Self.eventRole)
            ),
            try! CanonicalJSONObjectMember(
                key: "event_type",
                value: canonicalString(Self.eventType)
            ),
            try! CanonicalJSONObjectMember(
                key: "initiating_cause_claim",
                value: canonicalString(Self.initiatingCauseClaim)
            ),
            try! CanonicalJSONObjectMember(
                key: "payload_type",
                value: canonicalString(LedgerRecordType.observationEvent.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "platform_event_time_unix_ns",
                value: .null
            ),
            try! CanonicalJSONObjectMember(
                key: "source_interface",
                value: canonicalString(Self.sourceInterface)
            ),
            try! CanonicalJSONObjectMember(
                key: "surface_id",
                value: canonicalString(Self.surfaceID)
            ),
            try! CanonicalJSONObjectMember(
                key: "target_projection",
                value: targetProjection.canonicalValue()
            ),
        ])
    }

    /// Returns the exact canonical bytes embedded in an observation-event
    /// record.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    /// Builds the session-scoped record draft corresponding to this admitted
    /// callback.
    ///
    /// The method is module-internal for the same reason as the initializer:
    /// only the network-observation state machine may materialize an admitted
    /// callback as a record draft.
    func recordDraft(
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        monotonicTimeNS: Int64
    ) -> LedgerRecordDraft {
        LedgerRecordDraft(
            payload: canonicalValue(),
            recordID: recordID,
            recordType: .observationEvent,
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
        .string(
            try! CanonicalJSONString(rawValue)
        )
    }
}
