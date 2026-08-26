import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NetworkTransitionPayloadTests: XCTestCase {
    private func identifier(_ value: String) -> LedgerIdentifier {
        try! LedgerIdentifier(value)
    }

    private func digest(_ value: String) -> SHA256HexDigest {
        try! SHA256HexDigest(value)
    }

    private func reference(
        id: String,
        sha256: String,
        sequence: Int64
    ) -> LedgerRecordReference {
        try! LedgerRecordReference(
            recordID: identifier(id),
            recordSHA256: digest(sha256),
            sequenceIndex: sequence
        )
    }

    private func wifiState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [.wifi, .cellular],
            isConstrained: false,
            isExpensive: false,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [.wifi]
        )
    }

    private func cellularState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [.wifi, .cellular],
            isConstrained: false,
            isExpensive: true,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [.cellular]
        )
    }

    private func eventBoundRelation() throws -> NetworkTransitionRelation {
        let source = NetworkTransitionEndpoint(
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            snapshotReference: reference(
                id: "record:002-snapshot-wifi-a",
                sha256: "ca0ff596004618e8cb4b1e3f08198f3496548da142a4696745e9677700f175c9",
                sequence: 2
            ),
            sourceEventReference: reference(
                id: "record:001-path-wifi-a",
                sha256: "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980",
                sequence: 1
            ),
            networkPathState: try wifiState()
        )
        let target = NetworkTransitionEndpoint(
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            snapshotReference: reference(
                id: "record:004-snapshot-cellular-a",
                sha256: "0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d",
                sequence: 4
            ),
            sourceEventReference: reference(
                id: "record:003-path-cellular-a",
                sha256: "b83cb83c6f4ad05d799b502d0f8a1df4b39a89ece07dac7faa34e22589e58ae8",
                sequence: 3
            ),
            networkPathState: try cellularState()
        )
        let coverage = NetworkCoverageRelation.continuous(
            source: source.coverageEndpoint,
            target: target.coverageEndpoint
        )
        return .eventBound(
            source: source,
            target: target,
            coverageRelation: coverage,
            coverageReference: reference(
                id: "record:005-coverage-continuous",
                sha256: "5d5de19bdd2eddfc5f23791ede88b7afc13077f4c54810cef451e7602ec4df38",
                sequence: 5
            )
        )
    }

    private func endpointDifferenceRelation() throws -> NetworkTransitionRelation {
        let source = NetworkTransitionEndpoint(
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            snapshotReference: reference(
                id: "record:004-snapshot-cellular-a",
                sha256: "0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d",
                sequence: 4
            ),
            sourceEventReference: reference(
                id: "record:003-path-cellular-a",
                sha256: "b83cb83c6f4ad05d799b502d0f8a1df4b39a89ece07dac7faa34e22589e58ae8",
                sequence: 3
            ),
            networkPathState: try cellularState()
        )
        let target = NetworkTransitionEndpoint(
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            snapshotReference: reference(
                id: "record:010-snapshot-wifi-b",
                sha256: "6e6af21f6590c2ac508d0119a8c32477d87e9a3fd2a2df6b4f6909eac7b788fd",
                sequence: 10
            ),
            sourceEventReference: reference(
                id: "record:009-path-wifi-b",
                sha256: "a8ddd09176678809732c26edfd58acae5681e4e4f0b0e3c2fff78fccf814fbc0",
                sequence: 9
            ),
            networkPathState: try wifiState()
        )
        let gap = SessionBoundaryObservationGap(
            sourceSessionID: source.sessionID,
            sourceClockEpochID: source.clockEpochID,
            targetSessionID: target.sessionID,
            targetClockEpochID: target.clockEpochID,
            gapStartBoundary: reference(
                id: "record:007-session-close-a",
                sha256: "c8a19d0980a17921747507be3ca901dea23e716cffb03b595f93d6ffa98c652d",
                sequence: 7
            ),
            gapEndBoundary: reference(
                id: "record:008-session-open-b",
                sha256: "e2124b6cecf0549f19e2e804ffaf05c64a745b354828344c178793e8c324841b",
                sequence: 8
            )
        )
        let coverage = NetworkCoverageRelation.interrupted(
            source: source.coverageEndpoint,
            target: target.coverageEndpoint,
            gap: gap
        )
        return .endpointDifferenceOnly(
            source: source,
            target: target,
            coverageRelation: coverage,
            coverageReference: reference(
                id: "record:011-coverage-interrupted",
                sha256: "220fcd76f0ad3f6f9aa6483968ee7fd7639fb54115215722571393f181fc1bcd",
                sequence: 11
            )
        )
    }

    func testEventBoundPayloadMatchesExactPythonReferenceBytes() throws {
        let payload = try NetworkTransitionPayload(
            transitionID: identifier(
                "transition:event-bound-wifi-to-cellular"
            ),
            relation: eventBoundRelation()
        )
        let expected = #"{"axes":{"alternative_path_closure_status":"not_evaluated","causal_necessity_status":"not_established","causal_sufficiency_status":"not_established","endpoint_binding_status":"verified","endpoint_observation_source_binding_status":"all_bound","observation_coverage_status":"continuous","relation_change_observation_status":"all_event_observed","time_order_status":"monotonic_and_sequence_verified","transition_path_verification_status":"observation_event_bound"},"coverage_binding":{"record_id":"record:005-coverage-continuous","record_sha256":"5d5de19bdd2eddfc5f23791ede88b7afc13077f4c54810cef451e7602ec4df38","sequence_index":5},"endpoint_selection_rule":"immediate_eligible_network_snapshots_around_event","event_binding":{"record_id":"record:003-path-cellular-a","record_sha256":"b83cb83c6f4ad05d799b502d0f8a1df4b39a89ece07dac7faa34e22589e58ae8","sequence_index":3},"event_consumption_rule":"one_transition_per_event_no_intervening_network_event","initiating_event_unix_ns":null,"initiating_source_identity":null,"initiating_source_status":"unavailable_from_platform","payload_type":"transition","relation_changes":[{"after":true,"before":false,"field_path":"/network_path/is_expensive","observation_status":"event_observed","surface_id":"network_path"},{"after":["cellular"],"before":["wifi"],"field_path":"/network_path/used_interface_types","observation_status":"event_observed","surface_id":"network_path"}],"source_snapshot":{"record_id":"record:002-snapshot-wifi-a","record_sha256":"ca0ff596004618e8cb4b1e3f08198f3496548da142a4696745e9677700f175c9","sequence_index":2},"target_snapshot":{"record_id":"record:004-snapshot-cellular-a","record_sha256":"0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d","sequence_index":4},"transition_class":"event_bound","transition_id":"transition:event-bound-wifi-to-cellular"}"#

        XCTAssertEqual(payload.canonicalBytes(), Data(expected.utf8))
        XCTAssertEqual(payload.canonicalBytes().count, 1_837)
        XCTAssertEqual(
            payload.relation.changedFields,
            [.isExpensive, .usedInterfaceTypes]
        )
    }

    func testEndpointDifferencePayloadMatchesExactPythonReferenceBytes() throws {
        let payload = try NetworkTransitionPayload(
            transitionID: identifier(
                "transition:endpoint-difference-cellular-to-wifi"
            ),
            relation: endpointDifferenceRelation()
        )
        let expected = #"{"axes":{"alternative_path_closure_status":"open","causal_necessity_status":"not_established","causal_sufficiency_status":"not_established","endpoint_binding_status":"verified","endpoint_observation_source_binding_status":"all_bound","observation_coverage_status":"gap_between_endpoints","relation_change_observation_status":"all_endpoint_difference_observed","time_order_status":"sequence_verified","transition_path_verification_status":"endpoint_difference_only"},"coverage_binding":{"record_id":"record:011-coverage-interrupted","record_sha256":"220fcd76f0ad3f6f9aa6483968ee7fd7639fb54115215722571393f181fc1bcd","sequence_index":11},"endpoint_selection_rule":"last_bound_before_gap_and_first_fresh_bound_after_reopen","event_binding":null,"event_consumption_rule":"no_event_binding_permitted","initiating_event_unix_ns":null,"initiating_source_identity":null,"initiating_source_status":"unavailable_from_platform","payload_type":"transition","relation_changes":[{"after":false,"before":true,"field_path":"/network_path/is_expensive","observation_status":"endpoint_difference_observed","surface_id":"network_path"},{"after":["wifi"],"before":["cellular"],"field_path":"/network_path/used_interface_types","observation_status":"endpoint_difference_observed","surface_id":"network_path"}],"source_snapshot":{"record_id":"record:004-snapshot-cellular-a","record_sha256":"0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d","sequence_index":4},"target_snapshot":{"record_id":"record:010-snapshot-wifi-b","record_sha256":"6e6af21f6590c2ac508d0119a8c32477d87e9a3fd2a2df6b4f6909eac7b788fd","sequence_index":10},"transition_class":"endpoint_difference_only","transition_id":"transition:endpoint-difference-cellular-to-wifi"}"#

        XCTAssertEqual(payload.canonicalBytes(), Data(expected.utf8))
        XCTAssertEqual(payload.canonicalBytes().count, 1_732)
        XCTAssertNil(payload.relation.eventReference)
    }

    func testTransitionDraftScopeIsDerivedFromTransitionClass() throws {
        let eventPayload = try NetworkTransitionPayload(
            transitionID: identifier("transition:event"),
            relation: eventBoundRelation()
        )
        let eventDraft = try eventPayload.recordDraft(
            recordID: identifier("record:event-transition"),
            recordedWallTimeUnixNS: 6,
            eventBoundMonotonicTimeNS: 6_000
        )
        XCTAssertEqual(
            eventDraft.scope,
            .session(
                sessionID: identifier("session:synthetic-a"),
                clockEpochID: identifier("clock-epoch:synthetic-a"),
                monotonicTimeNS: 6_000
            )
        )

        let endpointPayload = try NetworkTransitionPayload(
            transitionID: identifier("transition:endpoint"),
            relation: endpointDifferenceRelation()
        )
        let endpointDraft = try endpointPayload.recordDraft(
            recordID: identifier("record:endpoint-transition"),
            recordedWallTimeUnixNS: 12,
            eventBoundMonotonicTimeNS: nil
        )
        XCTAssertEqual(endpointDraft.scope, .ledgerWide)
    }

    func testTransitionDraftRejectsWrongMonotonicShape() throws {
        let eventPayload = try NetworkTransitionPayload(
            transitionID: identifier("transition:event"),
            relation: eventBoundRelation()
        )
        XCTAssertThrowsError(
            try eventPayload.recordDraft(
                recordID: identifier("record:event-transition"),
                recordedWallTimeUnixNS: 6,
                eventBoundMonotonicTimeNS: nil
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkTransitionPayloadError,
                .eventBoundMonotonicTimeRequired
            )
        }

        let endpointPayload = try NetworkTransitionPayload(
            transitionID: identifier("transition:endpoint"),
            relation: endpointDifferenceRelation()
        )
        XCTAssertThrowsError(
            try endpointPayload.recordDraft(
                recordID: identifier("record:endpoint-transition"),
                recordedWallTimeUnixNS: 12,
                eventBoundMonotonicTimeNS: 1
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkTransitionPayloadError,
                .endpointDifferenceMonotonicTimeForbidden
            )
        }
    }

    func testEqualEndpointsCannotMaterializeTransition() throws {
        let source = try eventBoundRelation().source
        let target = NetworkTransitionEndpoint(
            sessionID: source.sessionID,
            clockEpochID: source.clockEpochID,
            snapshotReference: reference(
                id: "record:004-equal",
                sha256: String(repeating: "a", count: 64),
                sequence: 4
            ),
            sourceEventReference: reference(
                id: "record:003-equal-event",
                sha256: String(repeating: "b", count: 64),
                sequence: 3
            ),
            networkPathState: source.networkPathState
        )
        let coverage = NetworkCoverageRelation.continuous(
            source: source.coverageEndpoint,
            target: target.coverageEndpoint
        )
        let relation = NetworkTransitionRelation.eventBound(
            source: source,
            target: target,
            coverageRelation: coverage,
            coverageReference: reference(
                id: "record:005-equal-coverage",
                sha256: String(repeating: "c", count: 64),
                sequence: 5
            )
        )

        XCTAssertThrowsError(
            try NetworkTransitionPayload(
                transitionID: identifier("transition:forbidden-equal"),
                relation: relation
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkTransitionPayloadError,
                .noChangedProperties
            )
        }
    }
}
