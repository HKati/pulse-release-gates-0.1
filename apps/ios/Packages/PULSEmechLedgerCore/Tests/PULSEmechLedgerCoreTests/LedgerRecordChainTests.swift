import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class LedgerRecordChainTests: XCTestCase {
    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private func string(
        _ value: String
    ) -> CanonicalJSONValue {
        try! .string(value)
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

    private func object(
        _ members: [CanonicalJSONObjectMember]
    ) -> CanonicalJSONValue {
        try! .object(members)
    }

    private func minimalPayload(
        for recordType: LedgerRecordType,
        transitionClass: String? = nil
    ) -> CanonicalJSONValue {
        var members = [
            member(
                "payload_type",
                string(recordType.rawValue)
            ),
        ]

        if let transitionClass {
            members.append(
                member(
                    "transition_class",
                    string(transitionClass)
                )
            )
        }

        return object(members)
    }

    private func sessionScope(
        sessionID: String = "session:test-a",
        clockEpochID: String = "clock-epoch:test-a",
        monotonicTimeNS: Int64
    ) -> LedgerRecordScope {
        .session(
            sessionID: identifier(sessionID),
            clockEpochID: identifier(clockEpochID),
            monotonicTimeNS: monotonicTimeNS
        )
    }

    private func makeChain(
        recordStatus: LedgerRecordStatus = .observed
    ) -> LedgerRecordChain {
        LedgerRecordChain(
            ledgerID: identifier("device-ledger:test"),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: recordStatus
        )
    }

    private func draft(
        recordID: String,
        recordType: LedgerRecordType,
        recordedWallTimeUnixNS: Int64,
        scope: LedgerRecordScope,
        payload: CanonicalJSONValue? = nil
    ) -> LedgerRecordDraft {
        LedgerRecordDraft(
            payload: payload ?? minimalPayload(for: recordType),
            recordID: identifier(recordID),
            recordType: recordType,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            scope: scope
        )
    }

    private func firstReferencePayload() -> CanonicalJSONValue {
        object([
            member(
                "boundary_id",
                string("boundary:open-a")
            ),
            member(
                "boundary_kind",
                string("opened")
            ),
            member(
                "duplicate_boundary_rule",
                string("not_applicable_new_session")
            ),
            member(
                "lifecycle_event",
                string("scene_did_become_active")
            ),
            member(
                "network_surface_after_boundary",
                string("unavailable_until_fresh_path_update")
            ),
            member(
                "observation_window_state",
                string("open")
            ),
            member(
                "payload_type",
                string("session_boundary")
            ),
            member(
                "previous_session_id",
                .null
            ),
            member(
                "session_terminal",
                .boolean(false)
            ),
        ])
    }

    private func wifiNetworkState() -> CanonicalJSONValue {
        object([
            member(
                "available_interface_types",
                .array([
                    string("wifi"),
                    string("cellular"),
                ])
            ),
            member(
                "is_constrained",
                .boolean(false)
            ),
            member(
                "is_expensive",
                .boolean(false)
            ),
            member(
                "status",
                string("satisfied")
            ),
            member(
                "supports_dns",
                .boolean(true)
            ),
            member(
                "supports_ipv4",
                .boolean(true)
            ),
            member(
                "supports_ipv6",
                .boolean(true)
            ),
            member(
                "used_interface_types",
                .array([
                    string("wifi"),
                ])
            ),
        ])
    }

    private func secondReferencePayload() -> CanonicalJSONValue {
        object([
            member(
                "accepted_while_window_open",
                .boolean(true)
            ),
            member(
                "event_id",
                string("event:path-wifi-a")
            ),
            member(
                "event_role",
                string("surface_observation")
            ),
            member(
                "event_type",
                string("path_update_received")
            ),
            member(
                "initiating_cause_claim",
                string("none")
            ),
            member(
                "payload_type",
                string("observation_event")
            ),
            member(
                "platform_event_time_unix_ns",
                .null
            ),
            member(
                "source_interface",
                string(
                    "Network.framework NWPathMonitor.pathUpdateHandler"
                )
            ),
            member(
                "surface_id",
                string("network_path")
            ),
            member(
                "target_projection",
                wifiNetworkState()
            ),
        ])
    }

    private func makeReferenceChain() -> LedgerRecordChain {
        LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: .syntheticReference
        )
    }

    private func firstReferenceDraft() -> LedgerRecordDraft {
        draft(
            recordID: "record:000-session-open-a",
            recordType: .sessionBoundary,
            recordedWallTimeUnixNS: 1_700_000_000_000_000_000,
            scope: sessionScope(
                sessionID: "session:synthetic-a",
                clockEpochID: "clock-epoch:synthetic-a",
                monotonicTimeNS: 1_000
            ),
            payload: firstReferencePayload()
        )
    }

    private func secondReferenceDraft() -> LedgerRecordDraft {
        draft(
            recordID: "record:001-path-wifi-a",
            recordType: .observationEvent,
            recordedWallTimeUnixNS: 1_700_000_000_001_000_000,
            scope: sessionScope(
                sessionID: "session:synthetic-a",
                clockEpochID: "clock-epoch:synthetic-a",
                monotonicTimeNS: 2_000
            ),
            payload: secondReferencePayload()
        )
    }

    func testEmptySnapshotExposesConfiguredIdentityAndNextSequenceZero() async {
        let chain = makeChain(
            recordStatus: .syntheticReference
        )
        let snapshot = await chain.snapshot()

        XCTAssertEqual(
            chain.ledgerID,
            identifier("device-ledger:test")
        )
        XCTAssertEqual(
            chain.observerPublicKeyFingerprintSHA256,
            observerFingerprint
        )
        XCTAssertEqual(
            chain.recordStatus,
            .syntheticReference
        )
        XCTAssertEqual(
            snapshot.ledgerID,
            chain.ledgerID
        )
        XCTAssertEqual(
            snapshot.observerPublicKeyFingerprintSHA256,
            observerFingerprint
        )
        XCTAssertEqual(
            snapshot.recordStatus,
            .syntheticReference
        )
        XCTAssertEqual(
            snapshot.state,
            .acceptingRecords
        )
        XCTAssertEqual(
            snapshot.recordCount,
            0
        )
        XCTAssertEqual(
            snapshot.nextSequenceIndex,
            0
        )
        XCTAssertNil(snapshot.firstRecordReference)
        XCTAssertNil(snapshot.latestRecordReference)
        XCTAssertTrue(snapshot.records.isEmpty)
        XCTAssertTrue(snapshot.canonicalRecordValues.isEmpty)
        XCTAssertEqual(
            LedgerRecordChain.maximumRecordCount,
            100_000
        )
    }

    func testFirstTwoReferenceRecordsMatchPythonProducerParity() async throws {
        let chain = makeReferenceChain()

        let first = try await chain.append(
            firstReferenceDraft()
        )
        let second = try await chain.append(
            secondReferenceDraft()
        )
        let snapshot = await chain.snapshot()

        XCTAssertEqual(
            first.digestSubject.sequenceIndex,
            0
        )
        XCTAssertNil(
            first.digestSubject.previousRecordSHA256
        )
        XCTAssertEqual(
            first.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )

        XCTAssertEqual(
            second.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            second.digestSubject.previousRecordSHA256,
            first.recordSHA256
        )
        XCTAssertEqual(
            second.recordSHA256.rawValue,
            "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980"
        )

        for record in snapshot.records {
            XCTAssertEqual(
                record.digestSubject.ledgerID,
                chain.ledgerID
            )
            XCTAssertEqual(
                record.digestSubject.observerPublicKeyFingerprintSHA256,
                observerFingerprint
            )
            XCTAssertEqual(
                record.digestSubject.recordStatus,
                .syntheticReference
            )
        }

        XCTAssertEqual(
            snapshot.records,
            [first, second]
        )
        XCTAssertEqual(
            snapshot.recordCount,
            2
        )
        XCTAssertEqual(
            snapshot.nextSequenceIndex,
            2
        )
        XCTAssertEqual(
            snapshot.firstRecordReference,
            first.reference
        )
        XCTAssertEqual(
            snapshot.latestRecordReference,
            second.reference
        )
        XCTAssertEqual(
            snapshot.canonicalRecordValues,
            [
                first.canonicalValue(),
                second.canonicalValue(),
            ]
        )
    }

    func testDuplicateRecordIDIsRejectedWithoutStateMutation() async throws {
        let chain = makeChain()
        let first = try await chain.append(
            draft(
                recordID: "record:a",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 10,
                scope: sessionScope(
                    monotonicTimeNS: 100
                )
            )
        )
        let before = await chain.snapshot()

        do {
            _ = try await chain.append(
                draft(
                    recordID: "record:a",
                    recordType: .observationEvent,
                    recordedWallTimeUnixNS: 11,
                    scope: sessionScope(
                        monotonicTimeNS: 200
                    )
                )
            )
            XCTFail("Expected duplicate record ID rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordChainError,
                .duplicateRecordID(
                    identifier("record:a")
                )
            )
        }

        let afterDuplicateFailure = await chain.snapshot()
        XCTAssertEqual(
            afterDuplicateFailure,
            before
        )

        let second = try await chain.append(
            draft(
                recordID: "record:b",
                recordType: .observationEvent,
                recordedWallTimeUnixNS: 12,
                scope: sessionScope(
                    monotonicTimeNS: 200
                )
            )
        )

        XCTAssertEqual(
            second.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            second.digestSubject.previousRecordSHA256,
            first.recordSHA256
        )
    }

    func testEnvelopeValidationFailureLeavesStateAndRecordIDReusable() async throws {
        let chain = makeChain()
        let retryID = "record:retry"
        let invalidPayload = minimalPayload(
            for: .stateSnapshot
        )

        do {
            _ = try await chain.append(
                draft(
                    recordID: retryID,
                    recordType: .sessionBoundary,
                    recordedWallTimeUnixNS: 1,
                    scope: sessionScope(
                        monotonicTimeNS: 1
                    ),
                    payload: invalidPayload
                )
            )
            XCTFail("Expected payload-type mismatch")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .payloadTypeMismatch(
                    expected: "session_boundary",
                    actual: "state_snapshot"
                )
            )
        }

        let afterFailure = await chain.snapshot()
        XCTAssertEqual(
            afterFailure.recordCount,
            0
        )
        XCTAssertEqual(
            afterFailure.nextSequenceIndex,
            0
        )

        let accepted = try await chain.append(
            draft(
                recordID: retryID,
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 2,
                scope: sessionScope(
                    monotonicTimeNS: 2
                )
            )
        )

        XCTAssertEqual(
            accepted.digestSubject.sequenceIndex,
            0
        )
        XCTAssertNil(
            accepted.digestSubject.previousRecordSHA256
        )
    }

    func testSessionCannotChangeClockEpochAndFailedIDRemainsReusable() async throws {
        let chain = makeChain()
        let sessionID = "session:stable"
        let epochA = "clock-epoch:a"
        let epochB = "clock-epoch:b"

        let first = try await chain.append(
            draft(
                recordID: "record:first",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 1,
                scope: sessionScope(
                    sessionID: sessionID,
                    clockEpochID: epochA,
                    monotonicTimeNS: 100
                )
            )
        )

        do {
            _ = try await chain.append(
                draft(
                    recordID: "record:retry",
                    recordType: .observationEvent,
                    recordedWallTimeUnixNS: 2,
                    scope: sessionScope(
                        sessionID: sessionID,
                        clockEpochID: epochB,
                        monotonicTimeNS: 200
                    )
                )
            )
            XCTFail("Expected session clock-epoch change rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordChainError,
                .sessionClockEpochChanged(
                    sessionID: identifier(sessionID),
                    expected: identifier(epochA),
                    actual: identifier(epochB)
                )
            )
        }

        let accepted = try await chain.append(
            draft(
                recordID: "record:retry",
                recordType: .observationEvent,
                recordedWallTimeUnixNS: 3,
                scope: sessionScope(
                    sessionID: sessionID,
                    clockEpochID: epochA,
                    monotonicTimeNS: 200
                )
            )
        )

        XCTAssertEqual(
            accepted.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            accepted.digestSubject.previousRecordSHA256,
            first.recordSHA256
        )
    }

    func testClockEpochCannotBeReusedByDifferentSession() async throws {
        let chain = makeChain()
        let sharedEpoch = "clock-epoch:shared"

        _ = try await chain.append(
            draft(
                recordID: "record:session-a",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 1,
                scope: sessionScope(
                    sessionID: "session:a",
                    clockEpochID: sharedEpoch,
                    monotonicTimeNS: 100
                )
            )
        )

        do {
            _ = try await chain.append(
                draft(
                    recordID: "record:session-b",
                    recordType: .sessionBoundary,
                    recordedWallTimeUnixNS: 2,
                    scope: sessionScope(
                        sessionID: "session:b",
                        clockEpochID: sharedEpoch,
                        monotonicTimeNS: 200
                    )
                )
            )
            XCTFail("Expected clock-epoch reuse rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordChainError,
                .clockEpochReused(
                    clockEpochID: identifier(sharedEpoch),
                    existingSessionID: identifier("session:a"),
                    proposedSessionID: identifier("session:b")
                )
            )
        }

        let accepted = try await chain.append(
            draft(
                recordID: "record:session-b",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 3,
                scope: sessionScope(
                    sessionID: "session:b",
                    clockEpochID: "clock-epoch:b",
                    monotonicTimeNS: 1
                )
            )
        )

        XCTAssertEqual(
            accepted.digestSubject.sequenceIndex,
            1
        )
    }

    func testMonotonicTimeMustIncreaseWithinEpochButMayRestartInNewEpoch() async throws {
        let chain = makeChain()
        let sessionA = "session:a"
        let epochA = "clock-epoch:a"

        _ = try await chain.append(
            draft(
                recordID: "record:a0",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 100,
                scope: sessionScope(
                    sessionID: sessionA,
                    clockEpochID: epochA,
                    monotonicTimeNS: 100
                )
            )
        )

        for proposed in [Int64(100), 99] {
            do {
                _ = try await chain.append(
                    draft(
                        recordID: "record:retry",
                        recordType: .observationEvent,
                        recordedWallTimeUnixNS: 90,
                        scope: sessionScope(
                            sessionID: sessionA,
                            clockEpochID: epochA,
                            monotonicTimeNS: proposed
                        )
                    )
                )
                XCTFail("Expected non-increasing monotonic time rejection")
            } catch {
                XCTAssertEqual(
                    error as? LedgerRecordChainError,
                    .monotonicTimeNotStrictlyIncreasing(
                        clockEpochID: identifier(epochA),
                        previous: 100,
                        proposed: proposed
                    )
                )
            }
        }

        let sameEpochAccepted = try await chain.append(
            draft(
                recordID: "record:retry",
                recordType: .observationEvent,
                recordedWallTimeUnixNS: 80,
                scope: sessionScope(
                    sessionID: sessionA,
                    clockEpochID: epochA,
                    monotonicTimeNS: 101
                )
            )
        )
        let newEpochAccepted = try await chain.append(
            draft(
                recordID: "record:b0",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 70,
                scope: sessionScope(
                    sessionID: "session:b",
                    clockEpochID: "clock-epoch:b",
                    monotonicTimeNS: 1
                )
            )
        )

        XCTAssertEqual(
            sameEpochAccepted.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            newEpochAccepted.digestSubject.sequenceIndex,
            2
        )
        XCTAssertEqual(
            sameEpochAccepted.digestSubject.recordedWallTimeUnixNS,
            80
        )
        XCTAssertEqual(
            newEpochAccepted.digestSubject.recordedWallTimeUnixNS,
            70
        )
    }

    func testLedgerWideRecordDoesNotAlterSessionMonotonicContinuity() async throws {
        let chain = makeChain()
        let first = try await chain.append(
            draft(
                recordID: "record:first",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 1,
                scope: sessionScope(
                    monotonicTimeNS: 100
                )
            )
        )
        let coverage = try await chain.append(
            draft(
                recordID: "record:coverage",
                recordType: .coverageInterval,
                recordedWallTimeUnixNS: 2,
                scope: .ledgerWide
            )
        )
        let secondSessionRecord = try await chain.append(
            draft(
                recordID: "record:second",
                recordType: .observationEvent,
                recordedWallTimeUnixNS: 3,
                scope: sessionScope(
                    monotonicTimeNS: 101
                )
            )
        )

        XCTAssertEqual(
            coverage.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            coverage.digestSubject.previousRecordSHA256,
            first.recordSHA256
        )
        XCTAssertEqual(
            secondSessionRecord.digestSubject.sequenceIndex,
            2
        )
        XCTAssertEqual(
            secondSessionRecord.digestSubject.previousRecordSHA256,
            coverage.recordSHA256
        )
    }

    func testCheckpointCannotBeFirstAndRejectedIDIsNotReserved() async throws {
        let chain = makeChain()
        let sharedID = "record:initial"

        do {
            _ = try await chain.append(
                draft(
                    recordID: sharedID,
                    recordType: .checkpoint,
                    recordedWallTimeUnixNS: 1,
                    scope: .ledgerWide
                )
            )
            XCTFail("Expected checkpoint-first rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordChainError,
                .checkpointRequiresPriorRecord
            )
        }

        let afterFailure = await chain.snapshot()
        XCTAssertEqual(
            afterFailure.recordCount,
            0
        )
        XCTAssertEqual(
            afterFailure.state,
            .acceptingRecords
        )

        let accepted = try await chain.append(
            draft(
                recordID: sharedID,
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 2,
                scope: sessionScope(
                    monotonicTimeNS: 1
                )
            )
        )

        XCTAssertEqual(
            accepted.digestSubject.sequenceIndex,
            0
        )
    }

    func testCheckpointClosesChainAndRejectsEveryLaterAppend() async throws {
        let chain = makeChain()
        let first = try await chain.append(
            draft(
                recordID: "record:first",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 1,
                scope: sessionScope(
                    monotonicTimeNS: 1
                )
            )
        )
        let checkpoint = try await chain.append(
            draft(
                recordID: "record:checkpoint",
                recordType: .checkpoint,
                recordedWallTimeUnixNS: 2,
                scope: .ledgerWide
            )
        )
        let closed = await chain.snapshot()

        XCTAssertEqual(
            checkpoint.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            checkpoint.digestSubject.previousRecordSHA256,
            first.recordSHA256
        )
        XCTAssertEqual(
            closed.state,
            .checkpointed
        )
        XCTAssertEqual(
            closed.recordCount,
            2
        )
        XCTAssertNil(closed.nextSequenceIndex)
        XCTAssertEqual(
            closed.firstRecordReference,
            first.reference
        )
        XCTAssertEqual(
            closed.latestRecordReference,
            checkpoint.reference
        )

        do {
            _ = try await chain.append(
                draft(
                    recordID: "record:after",
                    recordType: .coverageInterval,
                    recordedWallTimeUnixNS: 3,
                    scope: .ledgerWide
                )
            )
            XCTFail("Expected append-after-checkpoint rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordChainError,
                .chainAlreadyCheckpointed
            )
        }

        let afterRejectedAppend = await chain.snapshot()
        XCTAssertEqual(
            afterRejectedAppend,
            closed
        )
    }

    func testSnapshotsRemainImmutableAcrossLaterAppends() async throws {
        let chain = makeChain()
        let first = try await chain.append(
            draft(
                recordID: "record:first",
                recordType: .sessionBoundary,
                recordedWallTimeUnixNS: 1,
                scope: sessionScope(
                    monotonicTimeNS: 1
                )
            )
        )
        let firstSnapshot = await chain.snapshot()

        let second = try await chain.append(
            draft(
                recordID: "record:second",
                recordType: .coverageInterval,
                recordedWallTimeUnixNS: 2,
                scope: .ledgerWide
            )
        )
        let secondSnapshot = await chain.snapshot()

        XCTAssertEqual(
            firstSnapshot.recordCount,
            1
        )
        XCTAssertEqual(
            firstSnapshot.records,
            [first]
        )
        XCTAssertEqual(
            firstSnapshot.latestRecordReference,
            first.reference
        )
        XCTAssertEqual(
            firstSnapshot.nextSequenceIndex,
            1
        )

        XCTAssertEqual(
            secondSnapshot.recordCount,
            2
        )
        XCTAssertEqual(
            secondSnapshot.records,
            [first, second]
        )
        XCTAssertEqual(
            secondSnapshot.latestRecordReference,
            second.reference
        )
        XCTAssertEqual(
            secondSnapshot.nextSequenceIndex,
            2
        )
    }
}
