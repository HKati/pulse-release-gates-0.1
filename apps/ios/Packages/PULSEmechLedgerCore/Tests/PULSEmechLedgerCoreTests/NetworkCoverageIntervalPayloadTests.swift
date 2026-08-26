import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NetworkCoverageIntervalPayloadTests: XCTestCase {
    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private func digest(
        _ rawValue: String
    ) -> SHA256HexDigest {
        try! SHA256HexDigest(rawValue)
    }

    private func reference(
        recordID: String,
        sha256: String,
        sequence: Int64
    ) -> LedgerRecordReference {
        try! LedgerRecordReference(
            recordID: identifier(recordID),
            recordSHA256: digest(sha256),
            sequenceIndex: sequence
        )
    }

    private func wifiA() -> NetworkCoverageEndpoint {
        NetworkCoverageEndpoint(
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            snapshotReference: reference(
                recordID: "record:002-snapshot-wifi-a",
                sha256:
                    "ca0ff596004618e8cb4b1e3f08198f3496548da142a4696745e9677700f175c9",
                sequence: 2
            )
        )
    }

    private func cellularA() -> NetworkCoverageEndpoint {
        NetworkCoverageEndpoint(
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            snapshotReference: reference(
                recordID: "record:004-snapshot-cellular-a",
                sha256:
                    "0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d",
                sequence: 4
            )
        )
    }

    private func wifiB() -> NetworkCoverageEndpoint {
        NetworkCoverageEndpoint(
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            snapshotReference: reference(
                recordID: "record:010-snapshot-wifi-b",
                sha256:
                    "6e6af21f6590c2ac508d0119a8c32477d87e9a3fd2a2df6b4f6909eac7b788fd",
                sequence: 10
            )
        )
    }

    private func referenceGap() -> SessionBoundaryObservationGap {
        SessionBoundaryObservationGap(
            sourceSessionID: identifier("session:synthetic-a"),
            sourceClockEpochID: identifier("clock-epoch:synthetic-a"),
            targetSessionID: identifier("session:synthetic-b"),
            targetClockEpochID: identifier("clock-epoch:synthetic-b"),
            gapStartBoundary: reference(
                recordID: "record:007-session-close-a",
                sha256:
                    "c8a19d0980a17921747507be3ca901dea23e716cffb03b595f93d6ffa98c652d",
                sequence: 7
            ),
            gapEndBoundary: reference(
                recordID: "record:008-session-open-b",
                sha256:
                    "e2124b6cecf0549f19e2e804ffaf05c64a745b354828344c178793e8c324841b",
                sequence: 8
            )
        )
    }

    func testContinuousPayloadMatchesExactPythonReferenceBytes() throws {
        let payload = try NetworkCoverageIntervalPayload(
            intervalID: identifier("coverage:continuous-a"),
            relation: .continuous(
                source: wifiA(),
                target: cellularA()
            )
        )
        let expected =
            #"{"boundary_basis":"same_session_consecutive_bound_endpoints","coverage_status":"continuous","gap_end_boundary":null,"gap_start_boundary":null,"intermediate_path_status":"observed_continuous","interval_id":"coverage:continuous-a","network_freshness_rule":"same_session_event_projection_bound","observer_execution_status":"observed_active","payload_type":"coverage_interval","source_clock_epoch_id":"clock-epoch:synthetic-a","source_session_id":"session:synthetic-a","source_snapshot":{"record_id":"record:002-snapshot-wifi-a","record_sha256":"ca0ff596004618e8cb4b1e3f08198f3496548da142a4696745e9677700f175c9","sequence_index":2},"target_clock_epoch_id":"clock-epoch:synthetic-a","target_session_id":"session:synthetic-a","target_snapshot":{"record_id":"record:004-snapshot-cellular-a","record_sha256":"0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d","sequence_index":4}}"#

        XCTAssertEqual(payload.relation.status, .continuous)
        XCTAssertEqual(payload.canonicalBytes(), Data(expected.utf8))
        XCTAssertFalse(payload.canonicalBytes().endsWithNewline)
    }

    func testInterruptedPayloadMatchesExactPythonReferenceBytes() throws {
        let payload = try NetworkCoverageIntervalPayload(
            intervalID: identifier("coverage:interrupted-a-to-b"),
            relation: .interrupted(
                source: cellularA(),
                target: wifiB(),
                gap: referenceGap()
            )
        )
        let expected =
            #"{"boundary_basis":"last_bound_before_close_to_first_fresh_bound_after_reopen","coverage_status":"interrupted","gap_end_boundary":{"record_id":"record:008-session-open-b","record_sha256":"e2124b6cecf0549f19e2e804ffaf05c64a745b354828344c178793e8c324841b","sequence_index":8},"gap_start_boundary":{"record_id":"record:007-session-close-a","record_sha256":"c8a19d0980a17921747507be3ca901dea23e716cffb03b595f93d6ffa98c652d","sequence_index":7},"intermediate_path_status":"unobserved","interval_id":"coverage:interrupted-a-to-b","network_freshness_rule":"fresh_post_reopen_callback_required_before_target_snapshot","observer_execution_status":"execution_unavailable_between_bounds","payload_type":"coverage_interval","source_clock_epoch_id":"clock-epoch:synthetic-a","source_session_id":"session:synthetic-a","source_snapshot":{"record_id":"record:004-snapshot-cellular-a","record_sha256":"0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d","sequence_index":4},"target_clock_epoch_id":"clock-epoch:synthetic-b","target_session_id":"session:synthetic-b","target_snapshot":{"record_id":"record:010-snapshot-wifi-b","record_sha256":"6e6af21f6590c2ac508d0119a8c32477d87e9a3fd2a2df6b4f6909eac7b788fd","sequence_index":10}}"#

        XCTAssertEqual(payload.relation.status, .interrupted)
        XCTAssertEqual(payload.canonicalBytes(), Data(expected.utf8))
        XCTAssertFalse(payload.canonicalBytes().endsWithNewline)
    }

    func testCoverageDraftIsLedgerWideAndSchemaTyped() throws {
        let payload = try NetworkCoverageIntervalPayload(
            intervalID: identifier("coverage:continuous-a"),
            relation: .continuous(
                source: wifiA(),
                target: cellularA()
            )
        )
        let draft = payload.recordDraft(
            recordID: identifier("record:005-coverage-continuous"),
            recordedWallTimeUnixNS: 1_700_000_000_005_000_000
        )

        XCTAssertEqual(draft.recordType, .coverageInterval)
        XCTAssertEqual(draft.scope, .ledgerWide)
        XCTAssertEqual(draft.payload, payload.canonicalValue())
    }

    func testContinuousCoverageRejectsDifferentSessionOrEpoch() {
        let target = NetworkCoverageEndpoint(
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            snapshotReference: wifiB().snapshotReference
        )

        XCTAssertThrowsError(
            try NetworkCoverageIntervalPayload(
                intervalID: identifier("coverage:invalid"),
                relation: .continuous(
                    source: wifiA(),
                    target: target
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkCoverageIntervalPayloadError,
                .continuousEndpointScopeMismatch
            )
        }
    }

    func testCoverageRejectsReversedEndpointOrder() {
        XCTAssertThrowsError(
            try NetworkCoverageIntervalPayload(
                intervalID: identifier("coverage:invalid"),
                relation: .continuous(
                    source: cellularA(),
                    target: wifiA()
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkCoverageIntervalPayloadError,
                .endpointOrderInvalid
            )
        }
    }

    func testInterruptedCoverageRejectsGapScopeMismatch() {
        let mismatched = SessionBoundaryObservationGap(
            sourceSessionID: identifier("session:wrong"),
            sourceClockEpochID: identifier("clock-epoch:synthetic-a"),
            targetSessionID: identifier("session:synthetic-b"),
            targetClockEpochID: identifier("clock-epoch:synthetic-b"),
            gapStartBoundary: referenceGap().gapStartBoundary,
            gapEndBoundary: referenceGap().gapEndBoundary
        )

        XCTAssertThrowsError(
            try NetworkCoverageIntervalPayload(
                intervalID: identifier("coverage:invalid"),
                relation: .interrupted(
                    source: cellularA(),
                    target: wifiB(),
                    gap: mismatched
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkCoverageIntervalPayloadError,
                .interruptedEndpointScopeMismatch
            )
        }
    }

    func testInterruptedCoverageRejectsBoundaryOrderOutsideEndpoints() {
        let invalid = SessionBoundaryObservationGap(
            sourceSessionID: identifier("session:synthetic-a"),
            sourceClockEpochID: identifier("clock-epoch:synthetic-a"),
            targetSessionID: identifier("session:synthetic-b"),
            targetClockEpochID: identifier("clock-epoch:synthetic-b"),
            gapStartBoundary: reference(
                recordID: "record:011-too-late",
                sha256: String(repeating: "1", count: 64),
                sequence: 11
            ),
            gapEndBoundary: referenceGap().gapEndBoundary
        )

        XCTAssertThrowsError(
            try NetworkCoverageIntervalPayload(
                intervalID: identifier("coverage:invalid"),
                relation: .interrupted(
                    source: cellularA(),
                    target: wifiB(),
                    gap: invalid
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? NetworkCoverageIntervalPayloadError,
                .interruptedBoundaryOrderInvalid
            )
        }
    }
}

private extension Data {
    var endsWithNewline: Bool {
        last == 0x0A || last == 0x0D
    }
}
