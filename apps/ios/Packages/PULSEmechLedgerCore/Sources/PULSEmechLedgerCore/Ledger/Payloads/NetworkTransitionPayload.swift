import Foundation

/// Construction failures for one Device Ledger v0 network transition.
public enum NetworkTransitionPayloadError: Error, Sendable, Equatable {
    /// Transition endpoints must appear in strict record-sequence order.
    case endpointOrderInvalid

    /// The coverage record must follow the target snapshot that closes the
    /// relation.
    case coverageOrderInvalid

    /// An event-bound transition requires one exact observer session and clock
    /// epoch across both endpoints.
    case eventBoundEndpointScopeMismatch

    /// The target snapshot's exact source event must appear strictly between the
    /// source and target snapshots.
    case eventBoundEventOrderInvalid

    /// The supplied coverage relation does not describe the exact transition
    /// endpoints or required coverage class.
    case coverageRelationMismatch

    /// A transition record is forbidden when every normalized comparison field
    /// is unchanged.
    case noChangedProperties

    /// Event-bound transition records are session-scoped and require a
    /// strictly ordered monotonic timestamp.
    case eventBoundMonotonicTimeRequired

    /// Endpoint-difference-only transitions are ledger-wide and cannot carry a
    /// session monotonic timestamp.
    case endpointDifferenceMonotonicTimeForbidden
}

/// Closed transition classes admitted by the Device Ledger v0 schema.
public enum NetworkTransitionClass: String, Sendable, Equatable, CaseIterable {
    case eventBound = "event_bound"
    case endpointDifferenceOnly = "endpoint_difference_only"
}

/// Closed observation status for one exact normalized relation change.
public enum NetworkRelationChangeObservationStatus: String, Sendable, Equatable {
    case eventObserved = "event_observed"
    case endpointDifferenceObserved = "endpoint_difference_observed"
}

/// Exact observed endpoint identity and state used by one transition relation.
public struct NetworkTransitionEndpoint: Sendable, Equatable {
    public let sessionID: LedgerIdentifier
    public let clockEpochID: LedgerIdentifier
    public let snapshotReference: LedgerRecordReference
    public let sourceEventReference: LedgerRecordReference
    public let networkPathState: NetworkPathState

    public init(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        snapshotReference: LedgerRecordReference,
        sourceEventReference: LedgerRecordReference,
        networkPathState: NetworkPathState
    ) {
        self.sessionID = sessionID
        self.clockEpochID = clockEpochID
        self.snapshotReference = snapshotReference
        self.sourceEventReference = sourceEventReference
        self.networkPathState = networkPathState
    }

    var coverageEndpoint: NetworkCoverageEndpoint {
        NetworkCoverageEndpoint(
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            snapshotReference: snapshotReference
        )
    }
}

/// One exact changed normalized network-path field.
public struct NetworkPathRelationChange: Sendable, Equatable {
    public let field: NetworkPathStateField
    public let before: CanonicalJSONValue
    public let after: CanonicalJSONValue
    public let observationStatus: NetworkRelationChangeObservationStatus

    init(
        field: NetworkPathStateField,
        before: CanonicalJSONValue,
        after: CanonicalJSONValue,
        observationStatus: NetworkRelationChangeObservationStatus
    ) {
        self.field = field
        self.before = before
        self.after = after
        self.observationStatus = observationStatus
    }

    func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            member("after", after),
            member("before", before),
            member("field_path", string(field.rawValue)),
            member("observation_status", string(observationStatus.rawValue)),
            member("surface_id", string("network_path")),
        ])
    }

    private func member(
        _ key: String,
        _ value: CanonicalJSONValue
    ) -> CanonicalJSONObjectMember {
        try! CanonicalJSONObjectMember(key: key, value: value)
    }

    private func string(_ value: String) -> CanonicalJSONValue {
        .string(try! CanonicalJSONString(value))
    }
}

/// One fully bounded transition relation derived from accepted endpoint,
/// coverage, and event evidence.
///
/// Construction is module-internal. `NetworkTransitionPayload` performs the
/// fail-closed semantic validation before a record draft can be produced.
public struct NetworkTransitionRelation: Sendable, Equatable {
    public let transitionClass: NetworkTransitionClass
    public let source: NetworkTransitionEndpoint
    public let target: NetworkTransitionEndpoint
    public let coverageRelation: NetworkCoverageRelation
    public let coverageReference: LedgerRecordReference
    public let eventReference: LedgerRecordReference?

    public var changedFields: [NetworkPathStateField] {
        NetworkPathStateField.allCases.filter { field in
            source.networkPathState.canonicalValue(for: field) !=
                target.networkPathState.canonicalValue(for: field)
        }
    }

    public var relationChanges: [NetworkPathRelationChange] {
        let observationStatus: NetworkRelationChangeObservationStatus =
            transitionClass == .eventBound
            ? .eventObserved
            : .endpointDifferenceObserved

        return changedFields.map { field in
            NetworkPathRelationChange(
                field: field,
                before: source.networkPathState.canonicalValue(for: field),
                after: target.networkPathState.canonicalValue(for: field),
                observationStatus: observationStatus
            )
        }
    }

    static func eventBound(
        source: NetworkTransitionEndpoint,
        target: NetworkTransitionEndpoint,
        coverageRelation: NetworkCoverageRelation,
        coverageReference: LedgerRecordReference
    ) -> NetworkTransitionRelation {
        NetworkTransitionRelation(
            transitionClass: .eventBound,
            source: source,
            target: target,
            coverageRelation: coverageRelation,
            coverageReference: coverageReference,
            eventReference: target.sourceEventReference
        )
    }

    static func endpointDifferenceOnly(
        source: NetworkTransitionEndpoint,
        target: NetworkTransitionEndpoint,
        coverageRelation: NetworkCoverageRelation,
        coverageReference: LedgerRecordReference
    ) -> NetworkTransitionRelation {
        NetworkTransitionRelation(
            transitionClass: .endpointDifferenceOnly,
            source: source,
            target: target,
            coverageRelation: coverageRelation,
            coverageReference: coverageReference,
            eventReference: nil
        )
    }

    private init(
        transitionClass: NetworkTransitionClass,
        source: NetworkTransitionEndpoint,
        target: NetworkTransitionEndpoint,
        coverageRelation: NetworkCoverageRelation,
        coverageReference: LedgerRecordReference,
        eventReference: LedgerRecordReference?
    ) {
        self.transitionClass = transitionClass
        self.source = source
        self.target = target
        self.coverageRelation = coverageRelation
        self.coverageReference = coverageReference
        self.eventReference = eventReference
    }
}

/// Closed typed representation of one Device Ledger v0 transition payload.
///
/// Callers provide only record identities and times. Transition class,
/// endpoints, event binding, coverage binding, relation-change values, axes,
/// and claim limits are derived from the accepted runtime relation.
public struct NetworkTransitionPayload: Sendable, Equatable {
    public let transitionID: LedgerIdentifier
    public let relation: NetworkTransitionRelation

    init(
        transitionID: LedgerIdentifier,
        relation: NetworkTransitionRelation
    ) throws {
        guard relation.source.snapshotReference.sequenceIndex <
                relation.target.snapshotReference.sequenceIndex else {
            throw NetworkTransitionPayloadError.endpointOrderInvalid
        }
        guard relation.target.snapshotReference.sequenceIndex <
                relation.coverageReference.sequenceIndex else {
            throw NetworkTransitionPayloadError.coverageOrderInvalid
        }

        let expectedCoverageStatus: NetworkCoverageStatus =
            relation.transitionClass == .eventBound
            ? .continuous
            : .interrupted
        guard relation.coverageRelation.status == expectedCoverageStatus,
              relation.coverageRelation.source ==
                relation.source.coverageEndpoint,
              relation.coverageRelation.target ==
                relation.target.coverageEndpoint else {
            throw NetworkTransitionPayloadError.coverageRelationMismatch
        }

        if relation.transitionClass == .eventBound {
            guard relation.source.sessionID == relation.target.sessionID,
                  relation.source.clockEpochID ==
                    relation.target.clockEpochID else {
                throw NetworkTransitionPayloadError
                    .eventBoundEndpointScopeMismatch
            }
            guard let event = relation.eventReference,
                  relation.source.snapshotReference.sequenceIndex <
                    event.sequenceIndex,
                  event.sequenceIndex <
                    relation.target.snapshotReference.sequenceIndex else {
                throw NetworkTransitionPayloadError.eventBoundEventOrderInvalid
            }
        } else {
            guard relation.eventReference == nil else {
                throw NetworkTransitionPayloadError
                    .coverageRelationMismatch
            }
        }

        guard !relation.relationChanges.isEmpty else {
            throw NetworkTransitionPayloadError.noChangedProperties
        }

        self.transitionID = transitionID
        self.relation = relation
    }

    /// Returns the exact canonical transition payload stored in the ledger.
    public func canonicalValue() -> CanonicalJSONValue {
        let values = canonicalClassValues()

        return try! .object([
            member("axes", axesCanonicalValue(values.axes)),
            member("coverage_binding", relation.coverageReference.canonicalValue()),
            member("endpoint_selection_rule", string(values.endpointSelectionRule)),
            member(
                "event_binding",
                relation.eventReference?.canonicalValue() ?? .null
            ),
            member("event_consumption_rule", string(values.eventConsumptionRule)),
            member("initiating_event_unix_ns", .null),
            member("initiating_source_identity", .null),
            member("initiating_source_status", string("unavailable_from_platform")),
            member("payload_type", string(LedgerRecordType.transition.rawValue)),
            member(
                "relation_changes",
                .array(relation.relationChanges.map { $0.canonicalValue() })
            ),
            member("source_snapshot", relation.source.snapshotReference.canonicalValue()),
            member("target_snapshot", relation.target.snapshotReference.canonicalValue()),
            member("transition_class", string(relation.transitionClass.rawValue)),
            member("transition_id", transitionID.canonicalValue),
        ])
    }

    /// Returns the exact canonical bytes embedded in a transition record.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(canonicalValue())
    }

    /// Builds the exact session-scoped or ledger-wide transition record draft.
    func recordDraft(
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64,
        eventBoundMonotonicTimeNS: Int64?
    ) throws -> LedgerRecordDraft {
        let scope: LedgerRecordScope
        switch relation.transitionClass {
        case .eventBound:
            guard let eventBoundMonotonicTimeNS else {
                throw NetworkTransitionPayloadError.eventBoundMonotonicTimeRequired
            }
            scope = .session(
                sessionID: relation.source.sessionID,
                clockEpochID: relation.source.clockEpochID,
                monotonicTimeNS: eventBoundMonotonicTimeNS
            )

        case .endpointDifferenceOnly:
            guard eventBoundMonotonicTimeNS == nil else {
                throw NetworkTransitionPayloadError
                    .endpointDifferenceMonotonicTimeForbidden
            }
            scope = .ledgerWide
        }

        return LedgerRecordDraft(
            payload: canonicalValue(),
            recordID: recordID,
            recordType: .transition,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            scope: scope
        )
    }

    private func canonicalClassValues() -> (
        axes: (
            alternativePathClosureStatus: String,
            observationCoverageStatus: String,
            relationChangeObservationStatus: String,
            timeOrderStatus: String,
            transitionPathVerificationStatus: String
        ),
        endpointSelectionRule: String,
        eventConsumptionRule: String
    ) {
        switch relation.transitionClass {
        case .eventBound:
            return (
                axes: (
                    alternativePathClosureStatus: "not_evaluated",
                    observationCoverageStatus: "continuous",
                    relationChangeObservationStatus: "all_event_observed",
                    timeOrderStatus: "monotonic_and_sequence_verified",
                    transitionPathVerificationStatus: "observation_event_bound"
                ),
                endpointSelectionRule:
                    "immediate_eligible_network_snapshots_around_event",
                eventConsumptionRule:
                    "one_transition_per_event_no_intervening_network_event"
            )

        case .endpointDifferenceOnly:
            return (
                axes: (
                    alternativePathClosureStatus: "open",
                    observationCoverageStatus: "gap_between_endpoints",
                    relationChangeObservationStatus:
                        "all_endpoint_difference_observed",
                    timeOrderStatus: "sequence_verified",
                    transitionPathVerificationStatus:
                        "endpoint_difference_only"
                ),
                endpointSelectionRule:
                    "last_bound_before_gap_and_first_fresh_bound_after_reopen",
                eventConsumptionRule: "no_event_binding_permitted"
            )
        }
    }

    private func axesCanonicalValue(
        _ axes: (
            alternativePathClosureStatus: String,
            observationCoverageStatus: String,
            relationChangeObservationStatus: String,
            timeOrderStatus: String,
            transitionPathVerificationStatus: String
        )
    ) -> CanonicalJSONValue {
        try! .object([
            member(
                "alternative_path_closure_status",
                string(axes.alternativePathClosureStatus)
            ),
            member("causal_necessity_status", string("not_established")),
            member("causal_sufficiency_status", string("not_established")),
            member("endpoint_binding_status", string("verified")),
            member(
                "endpoint_observation_source_binding_status",
                string("all_bound")
            ),
            member(
                "observation_coverage_status",
                string(axes.observationCoverageStatus)
            ),
            member(
                "relation_change_observation_status",
                string(axes.relationChangeObservationStatus)
            ),
            member("time_order_status", string(axes.timeOrderStatus)),
            member(
                "transition_path_verification_status",
                string(axes.transitionPathVerificationStatus)
            ),
        ])
    }

    private func member(
        _ key: String,
        _ value: CanonicalJSONValue
    ) -> CanonicalJSONObjectMember {
        try! CanonicalJSONObjectMember(key: key, value: value)
    }

    private func string(_ value: String) -> CanonicalJSONValue {
        .string(try! CanonicalJSONString(value))
    }
}
