import Foundation

/// Normalized UIKit scene activation states admitted by the Device Ledger v0
/// observation contract.
///
/// The Apple-platform adapter captures `UIScene.activationState` on the main
/// actor and submits only this immutable normalized value to the serial ledger
/// ingress. No raw scene persistent identifier is retained.
public enum AppLifecycleActivationState: String, Sendable, Equatable, CaseIterable {
    case foregroundActive = "foreground_active"
    case foregroundInactive = "foreground_inactive"
    case background
    case unattached
    case unknown
}

/// Declared role of one Device Ledger v0 state snapshot.
public enum NetworkPathStateSnapshotRole: String, Sendable, Equatable, CaseIterable {
    case baseline
    case sourceEndpoint = "source_endpoint"
    case targetEndpoint = "target_endpoint"
}

/// Closed typed representation of a state snapshot materialized from one
/// admitted Network.framework path-update callback.
///
/// The payload always contains both declared surfaces in their normative order:
/// app lifecycle first and network path second. The network surface is the exact
/// normalized projection stored by the immediately preceding observation-event
/// record. The source-event reference is therefore concrete and cannot be
/// selected by an external caller.
///
/// This payload is intentionally not publicly constructible. Only
/// `NetworkObservationStateMachine` may create a fresh callback-bound snapshot.
public struct NetworkPathStateSnapshotPayload: Sendable, Equatable {
    public static let appLifecycleSourceInterface =
        "UIKit UIScene.activationState and UISceneDelegate lifecycle callbacks"
    public static let appLifecycleSurfaceID = "app_lifecycle"
    public static let networkSourceInterface =
        NetworkPathObservationEventPayload.sourceInterface
    public static let networkSurfaceID = NetworkPathObservationEventPayload.surfaceID
    public static let networkFreshnessStatus =
        "fresh_callback_bound_in_same_session"

    public let snapshotID: LedgerIdentifier
    public let snapshotRole: NetworkPathStateSnapshotRole
    public let sourceEventBinding: LedgerRecordReference
    public let appLifecycleActivationState: AppLifecycleActivationState
    public let networkPathState: NetworkPathState

    init(
        snapshotID: LedgerIdentifier,
        snapshotRole: NetworkPathStateSnapshotRole,
        sourceEventBinding: LedgerRecordReference,
        appLifecycleActivationState: AppLifecycleActivationState,
        networkPathState: NetworkPathState
    ) {
        self.snapshotID = snapshotID
        self.snapshotRole = snapshotRole
        self.sourceEventBinding = sourceEventBinding
        self.appLifecycleActivationState = appLifecycleActivationState
        self.networkPathState = networkPathState
    }

    /// Returns the exact canonical state-snapshot payload stored in the ledger.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "network_freshness_status",
                value: canonicalString(Self.networkFreshnessStatus)
            ),
            try! CanonicalJSONObjectMember(
                key: "payload_type",
                value: canonicalString(LedgerRecordType.stateSnapshot.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "snapshot_id",
                value: snapshotID.canonicalValue
            ),
            try! CanonicalJSONObjectMember(
                key: "snapshot_role",
                value: canonicalString(snapshotRole.rawValue)
            ),
            try! CanonicalJSONObjectMember(
                key: "source_event_binding",
                value: sourceEventBinding.canonicalValue()
            ),
            try! CanonicalJSONObjectMember(
                key: "surfaces",
                value: .array([
                    appLifecycleSurfaceValue(),
                    networkPathSurfaceValue(),
                ])
            ),
        ])
    }

    /// Returns the exact canonical bytes embedded in a state-snapshot record.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    /// Builds the session-scoped record draft corresponding to this snapshot.
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
            recordType: .stateSnapshot,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            scope: .session(
                sessionID: sessionID,
                clockEpochID: clockEpochID,
                monotonicTimeNS: monotonicTimeNS
            )
        )
    }

    private func appLifecycleSurfaceValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "availability",
                value: canonicalString("observed")
            ),
            try! CanonicalJSONObjectMember(
                key: "source_interface",
                value: canonicalString(Self.appLifecycleSourceInterface)
            ),
            try! CanonicalJSONObjectMember(
                key: "state",
                value: try! .object([
                    try! CanonicalJSONObjectMember(
                        key: "activation_state",
                        value: canonicalString(
                            appLifecycleActivationState.rawValue
                        )
                    ),
                ])
            ),
            try! CanonicalJSONObjectMember(
                key: "surface_id",
                value: canonicalString(Self.appLifecycleSurfaceID)
            ),
        ])
    }

    private func networkPathSurfaceValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "availability",
                value: canonicalString("observed")
            ),
            try! CanonicalJSONObjectMember(
                key: "source_interface",
                value: canonicalString(Self.networkSourceInterface)
            ),
            try! CanonicalJSONObjectMember(
                key: "state",
                value: networkPathState.canonicalValue()
            ),
            try! CanonicalJSONObjectMember(
                key: "surface_id",
                value: canonicalString(Self.networkSurfaceID)
            ),
        ])
    }

    private func canonicalString(
        _ rawValue: String
    ) -> CanonicalJSONValue {
        .string(
            try! CanonicalJSONString(rawValue)
        )
    }
}
