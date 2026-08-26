import Foundation

/// Construction failures for one Device Ledger v0 coverage relation.
public enum NetworkCoverageIntervalPayloadError: Error, Sendable, Equatable {
    /// Coverage endpoints must appear in strict record-sequence order.
    case endpointOrderInvalid

    /// Continuous coverage requires one exact observer session and clock epoch.
    case continuousEndpointScopeMismatch

    /// Interrupted coverage endpoints must match the completed lifecycle gap.
    case interruptedEndpointScopeMismatch

    /// The retained source, gap boundaries, and first-fresh target must be
    /// strictly ordered in the ledger.
    case interruptedBoundaryOrderInvalid
}

/// Closed coverage classes admitted by the Device Ledger v0 schema.
public enum NetworkCoverageStatus: String, Sendable, Equatable, CaseIterable {
    case continuous
    case interrupted
}

/// Exact observed endpoint identity used by one coverage relation.
public struct NetworkCoverageEndpoint: Sendable, Equatable {
    public let sessionID: LedgerIdentifier
    public let clockEpochID: LedgerIdentifier
    public let snapshotReference: LedgerRecordReference

    public init(
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        snapshotReference: LedgerRecordReference
    ) {
        self.sessionID = sessionID
        self.clockEpochID = clockEpochID
        self.snapshotReference = snapshotReference
    }
}

/// One fully bounded coverage relation produced from admitted runtime evidence.
public enum NetworkCoverageRelation: Sendable, Equatable {
    case continuous(
        source: NetworkCoverageEndpoint,
        target: NetworkCoverageEndpoint
    )

    case interrupted(
        source: NetworkCoverageEndpoint,
        target: NetworkCoverageEndpoint,
        gap: SessionBoundaryObservationGap
    )

    public var status: NetworkCoverageStatus {
        switch self {
        case .continuous:
            .continuous
        case .interrupted:
            .interrupted
        }
    }

    public var source: NetworkCoverageEndpoint {
        switch self {
        case let .continuous(source, _),
             let .interrupted(source, _, _):
            source
        }
    }

    public var target: NetworkCoverageEndpoint {
        switch self {
        case let .continuous(_, target),
             let .interrupted(_, target, _):
            target
        }
    }

    public var observationGap: SessionBoundaryObservationGap? {
        guard case let .interrupted(_, _, gap) = self else {
            return nil
        }
        return gap
    }
}

/// Closed typed representation of one Device Ledger v0 coverage-interval
/// payload.
///
/// The runtime producer does not accept coverage semantics from its caller. It
/// derives either one same-session continuous relation or one cross-session
/// interrupted relation from already finalized endpoint and lifecycle records,
/// then uses this type to materialize the exact schema-coupled payload.
public struct NetworkCoverageIntervalPayload: Sendable, Equatable {
    public let intervalID: LedgerIdentifier
    public let relation: NetworkCoverageRelation

    init(
        intervalID: LedgerIdentifier,
        relation: NetworkCoverageRelation
    ) throws {
        let source = relation.source
        let target = relation.target

        guard source.snapshotReference.sequenceIndex <
                target.snapshotReference.sequenceIndex else {
            throw NetworkCoverageIntervalPayloadError.endpointOrderInvalid
        }

        switch relation {
        case .continuous:
            guard source.sessionID == target.sessionID,
                  source.clockEpochID == target.clockEpochID else {
                throw NetworkCoverageIntervalPayloadError
                    .continuousEndpointScopeMismatch
            }

        case let .interrupted(_, _, gap):
            guard source.sessionID == gap.sourceSessionID,
                  source.clockEpochID == gap.sourceClockEpochID,
                  target.sessionID == gap.targetSessionID,
                  target.clockEpochID == gap.targetClockEpochID else {
                throw NetworkCoverageIntervalPayloadError
                    .interruptedEndpointScopeMismatch
            }

            guard source.snapshotReference.sequenceIndex <
                    gap.gapStartBoundary.sequenceIndex,
                  gap.gapStartBoundary.sequenceIndex <
                    gap.gapEndBoundary.sequenceIndex,
                  gap.gapEndBoundary.sequenceIndex <
                    target.snapshotReference.sequenceIndex else {
                throw NetworkCoverageIntervalPayloadError
                    .interruptedBoundaryOrderInvalid
            }
        }

        self.intervalID = intervalID
        self.relation = relation
    }

    /// Returns the exact canonical coverage payload stored in the ledger.
    public func canonicalValue() -> CanonicalJSONValue {
        let values = canonicalRelationValues()

        return try! .object([
            member(
                "boundary_basis",
                string(values.boundaryBasis)
            ),
            member(
                "coverage_status",
                string(relation.status.rawValue)
            ),
            member(
                "gap_end_boundary",
                values.gapEndBoundary?.canonicalValue() ?? .null
            ),
            member(
                "gap_start_boundary",
                values.gapStartBoundary?.canonicalValue() ?? .null
            ),
            member(
                "intermediate_path_status",
                string(values.intermediatePathStatus)
            ),
            member(
                "interval_id",
                intervalID.canonicalValue
            ),
            member(
                "network_freshness_rule",
                string(values.networkFreshnessRule)
            ),
            member(
                "observer_execution_status",
                string(values.observerExecutionStatus)
            ),
            member(
                "payload_type",
                string(LedgerRecordType.coverageInterval.rawValue)
            ),
            member(
                "source_clock_epoch_id",
                relation.source.clockEpochID.canonicalValue
            ),
            member(
                "source_session_id",
                relation.source.sessionID.canonicalValue
            ),
            member(
                "source_snapshot",
                relation.source.snapshotReference.canonicalValue()
            ),
            member(
                "target_clock_epoch_id",
                relation.target.clockEpochID.canonicalValue
            ),
            member(
                "target_session_id",
                relation.target.sessionID.canonicalValue
            ),
            member(
                "target_snapshot",
                relation.target.snapshotReference.canonicalValue()
            ),
        ])
    }

    /// Returns the exact canonical bytes embedded in a coverage record.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    /// Builds the ledger-wide record draft corresponding to this coverage
    /// relation.
    func recordDraft(
        recordID: LedgerIdentifier,
        recordedWallTimeUnixNS: Int64
    ) -> LedgerRecordDraft {
        LedgerRecordDraft(
            payload: canonicalValue(),
            recordID: recordID,
            recordType: .coverageInterval,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            scope: .ledgerWide
        )
    }

    private func canonicalRelationValues() -> (
        boundaryBasis: String,
        gapStartBoundary: LedgerRecordReference?,
        gapEndBoundary: LedgerRecordReference?,
        intermediatePathStatus: String,
        networkFreshnessRule: String,
        observerExecutionStatus: String
    ) {
        switch relation {
        case .continuous:
            return (
                boundaryBasis: "same_session_consecutive_bound_endpoints",
                gapStartBoundary: nil,
                gapEndBoundary: nil,
                intermediatePathStatus: "observed_continuous",
                networkFreshnessRule: "same_session_event_projection_bound",
                observerExecutionStatus: "observed_active"
            )

        case let .interrupted(_, _, gap):
            return (
                boundaryBasis:
                    "last_bound_before_close_to_first_fresh_bound_after_reopen",
                gapStartBoundary: gap.gapStartBoundary,
                gapEndBoundary: gap.gapEndBoundary,
                intermediatePathStatus: "unobserved",
                networkFreshnessRule:
                    "fresh_post_reopen_callback_required_before_target_snapshot",
                observerExecutionStatus: "execution_unavailable_between_bounds"
            )
        }
    }

    private func member(
        _ key: String,
        _ value: CanonicalJSONValue
    ) -> CanonicalJSONObjectMember {
        try! CanonicalJSONObjectMember(
            key: key,
            value: value
        )
    }

    private func string(
        _ value: String
    ) -> CanonicalJSONValue {
        .string(
            try! CanonicalJSONString(value)
        )
    }
}
