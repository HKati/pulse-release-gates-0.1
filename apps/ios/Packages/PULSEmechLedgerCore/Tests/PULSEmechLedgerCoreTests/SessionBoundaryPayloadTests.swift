import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class SessionBoundaryPayloadTests: XCTestCase {
    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    func testOpenedBoundaryDerivesExactClosedFieldTuple() {
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )

        XCTAssertEqual(payload.boundaryID, identifier("boundary:open-a"))
        XCTAssertEqual(payload.kind, .opened)
        XCTAssertEqual(payload.lifecycleEvent, .sceneDidBecomeActive)
        XCTAssertEqual(payload.duplicateBoundaryRule, .notApplicableNewSession)
        XCTAssertEqual(
            payload.networkSurfaceAfterBoundary,
            .unavailableUntilFreshPathUpdate
        )
        XCTAssertEqual(payload.observationWindowState, .open)
        XCTAssertNil(payload.previousSessionID)
        XCTAssertFalse(payload.sessionTerminal)
        XCTAssertEqual(
            payload.canonicalBytes(),
            Data(
                #"{"boundary_id":"boundary:open-a","boundary_kind":"opened","duplicate_boundary_rule":"not_applicable_new_session","lifecycle_event":"scene_did_become_active","network_surface_after_boundary":"unavailable_until_fresh_path_update","observation_window_state":"open","payload_type":"session_boundary","previous_session_id":null,"session_terminal":false}"#.utf8
            )
        )
    }

    func testObservationWindowCloseDerivesExactClosedFieldTuple() {
        let payload = SessionBoundaryPayload.observationWindowClosed(
            boundaryID: identifier("boundary:close-a"),
            sessionID: identifier("session:synthetic-a")
        )

        XCTAssertEqual(payload.boundaryID, identifier("boundary:close-a"))
        XCTAssertEqual(payload.kind, .observationWindowClosed)
        XCTAssertEqual(payload.lifecycleEvent, .sceneWillResignActive)
        XCTAssertEqual(
            payload.duplicateBoundaryRule,
            .idempotentNoSecondGapStart
        )
        XCTAssertEqual(
            payload.networkSurfaceAfterBoundary,
            .lastBoundValueRetainedForGapSourceOnly
        )
        XCTAssertEqual(payload.observationWindowState, .closed)
        XCTAssertEqual(
            payload.previousSessionID,
            identifier("session:synthetic-a")
        )
        XCTAssertFalse(payload.sessionTerminal)
        XCTAssertEqual(
            payload.canonicalBytes(),
            Data(
                #"{"boundary_id":"boundary:close-a","boundary_kind":"observation_window_closed","duplicate_boundary_rule":"idempotent_no_second_gap_start","lifecycle_event":"scene_will_resign_active","network_surface_after_boundary":"last_bound_value_retained_for_gap_source_only","observation_window_state":"closed","payload_type":"session_boundary","previous_session_id":"session:synthetic-a","session_terminal":false}"#.utf8
            )
        )
    }

    func testSessionTerminationDerivesExactClosedFieldTuple() {
        let payload = SessionBoundaryPayload.sessionTerminated(
            boundaryID: identifier("boundary:disconnect-a"),
            sessionID: identifier("session:synthetic-a")
        )

        XCTAssertEqual(
            payload.boundaryID,
            identifier("boundary:disconnect-a")
        )
        XCTAssertEqual(payload.kind, .sessionTerminated)
        XCTAssertEqual(payload.lifecycleEvent, .sceneDidDisconnect)
        XCTAssertEqual(
            payload.duplicateBoundaryRule,
            .terminalOnceNoFutureEvents
        )
        XCTAssertEqual(
            payload.networkSurfaceAfterBoundary,
            .unavailableTerminal
        )
        XCTAssertEqual(payload.observationWindowState, .terminal)
        XCTAssertEqual(
            payload.previousSessionID,
            identifier("session:synthetic-a")
        )
        XCTAssertTrue(payload.sessionTerminal)
        XCTAssertEqual(
            payload.canonicalBytes(),
            Data(
                #"{"boundary_id":"boundary:disconnect-a","boundary_kind":"session_terminated","duplicate_boundary_rule":"terminal_once_no_future_events","lifecycle_event":"scene_did_disconnect","network_surface_after_boundary":"unavailable_terminal","observation_window_state":"terminal","payload_type":"session_boundary","previous_session_id":"session:synthetic-a","session_terminal":true}"#.utf8
            )
        )
    }

    func testLaterOpenedBoundaryPreservesPreviousSessionAndBuildsTypedDraft() throws {
        let previousSession = identifier("session:synthetic-a")
        let currentSession = identifier("session:synthetic-b")
        let epoch = identifier("clock-epoch:synthetic-b")
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-b"),
            previousSessionID: previousSession
        )

        let draft = try payload.recordDraft(
            recordID: identifier("record:008-session-open-b"),
            recordedWallTimeUnixNS: 1_700_000_000_008_000_000,
            sessionID: currentSession,
            clockEpochID: epoch,
            monotonicTimeNS: 1_000
        )

        XCTAssertEqual(payload.previousSessionID, previousSession)
        XCTAssertEqual(draft.payload, payload.canonicalValue())
        XCTAssertEqual(
            draft.recordID,
            identifier("record:008-session-open-b")
        )
        XCTAssertEqual(draft.recordType, .sessionBoundary)
        XCTAssertEqual(
            draft.recordedWallTimeUnixNS,
            1_700_000_000_008_000_000
        )
        XCTAssertEqual(
            draft.scope,
            .session(
                sessionID: currentSession,
                clockEpochID: epoch,
                monotonicTimeNS: 1_000
            )
        )
        XCTAssertEqual(
            payload.canonicalBytes(),
            Data(
                #"{"boundary_id":"boundary:open-b","boundary_kind":"opened","duplicate_boundary_rule":"not_applicable_new_session","lifecycle_event":"scene_did_become_active","network_surface_after_boundary":"unavailable_until_fresh_path_update","observation_window_state":"open","payload_type":"session_boundary","previous_session_id":"session:synthetic-a","session_terminal":false}"#.utf8
            )
        )
    }

    func testOpenedBoundaryRejectsCurrentSessionAsItsPredecessor() {
        let sessionID = identifier("session:same")
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open"),
            previousSessionID: sessionID
        )

        XCTAssertThrowsError(
            try payload.recordDraft(
                recordID: identifier("record:open"),
                recordedWallTimeUnixNS: 1,
                sessionID: sessionID,
                clockEpochID: identifier("clock-epoch:new"),
                monotonicTimeNS: 1
            )
        ) { error in
            XCTAssertEqual(
                error as? SessionBoundaryPayloadError,
                .openedPreviousSessionMatchesCurrentSession(sessionID)
            )
        }
    }

    func testWindowCloseRejectsMismatchedRecordScopeSession() {
        let expectedSession = identifier("session:expected")
        let actualSession = identifier("session:actual")
        let payload = SessionBoundaryPayload.observationWindowClosed(
            boundaryID: identifier("boundary:close"),
            sessionID: expectedSession
        )

        XCTAssertThrowsError(
            try payload.recordDraft(
                recordID: identifier("record:close"),
                recordedWallTimeUnixNS: 1,
                sessionID: actualSession,
                clockEpochID: identifier("clock-epoch:actual"),
                monotonicTimeNS: 1
            )
        ) { error in
            XCTAssertEqual(
                error as? SessionBoundaryPayloadError,
                .boundarySessionMismatch(
                    kind: .observationWindowClosed,
                    expected: expectedSession,
                    actual: actualSession
                )
            )
        }
    }

    func testTerminationRejectsMismatchedRecordScopeSession() {
        let expectedSession = identifier("session:expected")
        let actualSession = identifier("session:actual")
        let payload = SessionBoundaryPayload.sessionTerminated(
            boundaryID: identifier("boundary:disconnect"),
            sessionID: expectedSession
        )

        XCTAssertThrowsError(
            try payload.recordDraft(
                recordID: identifier("record:disconnect"),
                recordedWallTimeUnixNS: 1,
                sessionID: actualSession,
                clockEpochID: identifier("clock-epoch:actual"),
                monotonicTimeNS: 1
            )
        ) { error in
            XCTAssertEqual(
                error as? SessionBoundaryPayloadError,
                .boundarySessionMismatch(
                    kind: .sessionTerminated,
                    expected: expectedSession,
                    actual: actualSession
                )
            )
        }
    }

    func testClosingAndTerminalBoundariesBuildSessionScopedDrafts() throws {
        let sessionID = identifier("session:synthetic-a")
        let epochID = identifier("clock-epoch:synthetic-a")
        let cases: [(SessionBoundaryPayload, LedgerIdentifier, Int64)] = [
            (
                .observationWindowClosed(
                    boundaryID: identifier("boundary:close-a"),
                    sessionID: sessionID
                ),
                identifier("record:007-session-close-a"),
                8_000
            ),
            (
                .sessionTerminated(
                    boundaryID: identifier("boundary:disconnect-a"),
                    sessionID: sessionID
                ),
                identifier("record:008-session-disconnect-a"),
                9_000
            ),
        ]

        for (payload, recordID, monotonicTimeNS) in cases {
            let draft = try payload.recordDraft(
                recordID: recordID,
                recordedWallTimeUnixNS: 10,
                sessionID: sessionID,
                clockEpochID: epochID,
                monotonicTimeNS: monotonicTimeNS
            )

            XCTAssertEqual(draft.payload, payload.canonicalValue())
            XCTAssertEqual(draft.recordID, recordID)
            XCTAssertEqual(draft.recordType, .sessionBoundary)
            XCTAssertEqual(
                draft.scope,
                .session(
                    sessionID: sessionID,
                    clockEpochID: epochID,
                    monotonicTimeNS: monotonicTimeNS
                )
            )
        }
    }

    func testFirstReferenceBoundaryAppendedThroughChainMatchesPythonRecord() async throws {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: .syntheticReference
        )
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )
        let draft = try payload.recordDraft(
            recordID: identifier("record:000-session-open-a"),
            recordedWallTimeUnixNS: 1_700_000_000_000_000_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 1_000
        )

        let record = try await chain.append(draft)

        XCTAssertEqual(record.digestSubject.sequenceIndex, 0)
        XCTAssertNil(record.digestSubject.previousRecordSHA256)
        XCTAssertEqual(
            record.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(record.canonicalBytes().count, 1_495)
        XCTAssertEqual(
            record.reference.recordID,
            identifier("record:000-session-open-a")
        )
    }

    func testCanonicalEncodingIsDeterministicAndHasNoAddedBoundaryBytes() {
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )
        let expected = payload.canonicalBytes()

        XCTAssertFalse(expected.starts(with: [0xEF, 0xBB, 0xBF]))
        XCTAssertEqual(expected.first, 0x7B)
        XCTAssertEqual(expected.last, 0x7D)
        XCTAssertFalse(expected.contains(0x0A))
        XCTAssertFalse(expected.contains(0x0D))

        for _ in 0..<100 {
            XCTAssertEqual(payload.canonicalBytes(), expected)
        }
    }
}
