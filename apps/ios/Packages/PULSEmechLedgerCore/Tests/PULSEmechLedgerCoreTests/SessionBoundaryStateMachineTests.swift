import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class SessionBoundaryStateMachineTests: XCTestCase {
    private enum TestFailure: Error {
        case expectedRecordedResult
        case expectedIgnoredDuplicateResult
    }

    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    private let baseWallTime: Int64 = 1_700_000_000_000_000_000

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private func makeMachine(
        recordStatus: LedgerRecordStatus = .syntheticReference
    ) -> SessionBoundaryStateMachine {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: recordStatus
        )
        return SessionBoundaryStateMachine(
            chain: chain
        )
    }

    private func requireRecorded(
        _ result: SessionBoundaryLifecycleResult,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws -> (
        record: LedgerRecordEnvelope,
        completedGap: SessionBoundaryObservationGap?
    ) {
        guard case let .recorded(record, completedGap) = result else {
            XCTFail(
                "Expected a recorded lifecycle result",
                file: file,
                line: line
            )
            throw TestFailure.expectedRecordedResult
        }

        return (
            record,
            completedGap
        )
    }

    private func requireIgnoredDuplicate(
        _ result: SessionBoundaryLifecycleResult,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws -> (
        event: SessionBoundaryLifecycleEvent,
        sessionID: LedgerIdentifier,
        existingBoundary: LedgerRecordReference
    ) {
        guard case let .ignoredDuplicate(
            event,
            sessionID,
            existingBoundary
        ) = result else {
            XCTFail(
                "Expected an ignored duplicate lifecycle result",
                file: file,
                line: line
            )
            throw TestFailure.expectedIgnoredDuplicateResult
        }

        return (
            event,
            sessionID,
            existingBoundary
        )
    }

    private func openSessionA(
        on machine: SessionBoundaryStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-a"),
            recordID: identifier("record:000-session-open-a"),
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime,
            monotonicTimeNS: 1_000
        )
        return try requireRecorded(result).record
    }

    private func closeSessionA(
        on machine: SessionBoundaryStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneWillResignActive(
            boundaryID: identifier("boundary:close-a"),
            recordID: identifier("record:001-session-close-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000,
            monotonicTimeNS: 2_000
        )
        return try requireRecorded(result).record
    }

    private func openSessionB(
        on machine: SessionBoundaryStateMachine,
        recordID: String = "record:002-session-open-b",
        wallTimeOffset: Int64 = 2_000_000
    ) async throws -> (
        record: LedgerRecordEnvelope,
        completedGap: SessionBoundaryObservationGap?
    ) {
        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-b"),
            recordID: identifier(recordID),
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            recordedWallTimeUnixNS: baseWallTime + wallTimeOffset,
            monotonicTimeNS: 1_000
        )
        return try requireRecorded(result)
    }

    func testInitialSnapshotIsAwaitingFirstSessionWithEmptyChain() async throws {
        let machine = makeMachine()
        let snapshot = try await machine.snapshot()

        XCTAssertEqual(
            snapshot.state,
            .awaitingFirstSession
        )
        XCTAssertEqual(
            snapshot.chain.ledgerID,
            identifier("device-ledger:iphone-synthetic-reference-v0")
        )
        XCTAssertEqual(
            snapshot.chain.observerPublicKeyFingerprintSHA256,
            observerFingerprint
        )
        XCTAssertEqual(
            snapshot.chain.recordStatus,
            .syntheticReference
        )
        XCTAssertEqual(
            snapshot.chain.recordCount,
            0
        )
        XCTAssertEqual(
            snapshot.chain.nextSequenceIndex,
            0
        )
        XCTAssertNil(snapshot.chain.firstRecordReference)
        XCTAssertNil(snapshot.chain.latestRecordReference)
    }

    func testFirstOpenMatchesExactSyntheticReferenceRecord() async throws {
        let machine = makeMachine()
        let record = try await openSessionA(
            on: machine
        )

        XCTAssertEqual(
            record.digestSubject.sequenceIndex,
            0
        )
        XCTAssertNil(
            record.digestSubject.previousRecordSHA256
        )
        XCTAssertEqual(
            record.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(
            record.canonicalBytes().count,
            1_495
        )

        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = record.digestSubject.scope else {
            return XCTFail(
                "Expected a session-scoped opening record"
            )
        }

        XCTAssertEqual(
            sessionID,
            identifier("session:synthetic-a")
        )
        XCTAssertEqual(
            clockEpochID,
            identifier("clock-epoch:synthetic-a")
        )
        XCTAssertEqual(
            monotonicTimeNS,
            1_000
        )

        let snapshot = try await machine.snapshot()
        guard case let .observationWindowOpen(
            currentSessionID,
            currentClockEpochID,
            openBoundary,
            previousSessionID,
            precedingObservationGap
        ) = snapshot.state else {
            return XCTFail(
                "Expected an open observation window"
            )
        }

        XCTAssertEqual(currentSessionID, sessionID)
        XCTAssertEqual(currentClockEpochID, clockEpochID)
        XCTAssertEqual(openBoundary, record.reference)
        XCTAssertNil(previousSessionID)
        XCTAssertNil(precedingObservationGap)
        XCTAssertEqual(snapshot.chain.recordCount, 1)
        XCTAssertEqual(snapshot.chain.nextSequenceIndex, 1)
        XCTAssertEqual(
            snapshot.state.currentOpenBoundary,
            record.reference
        )
        XCTAssertNil(snapshot.state.observationGapStartBoundary)
        XCTAssertNil(snapshot.state.completedObservationGap)
        XCTAssertEqual(
            snapshot.state.latestBoundaryReference,
            record.reference
        )
    }

    func testDuplicateActiveCallbackIsIgnoredWithoutConsumingRecordIdentity() async throws {
        let machine = makeMachine()
        let openRecord = try await openSessionA(
            on: machine
        )

        let duplicate = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:duplicate-open-a"),
            recordID: identifier("record:001-session-close-a"),
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 500_000,
            monotonicTimeNS: 1_500
        )
        let ignored = try requireIgnoredDuplicate(
            duplicate
        )

        XCTAssertEqual(
            ignored.event,
            .sceneDidBecomeActive
        )
        XCTAssertEqual(
            ignored.sessionID,
            identifier("session:synthetic-a")
        )
        XCTAssertEqual(
            ignored.existingBoundary,
            openRecord.reference
        )

        let afterDuplicate = try await machine.snapshot()
        XCTAssertEqual(afterDuplicate.chain.recordCount, 1)
        XCTAssertEqual(afterDuplicate.chain.nextSequenceIndex, 1)

        let closeRecord = try await closeSessionA(
            on: machine
        )
        XCTAssertEqual(
            closeRecord.digestSubject.recordID,
            identifier("record:001-session-close-a")
        )
        XCTAssertEqual(
            closeRecord.digestSubject.sequenceIndex,
            1
        )
    }

    func testConflictingActiveSessionIsRejectedWithoutStateChange() async throws {
        let machine = makeMachine()
        let openRecord = try await openSessionA(
            on: machine
        )

        do {
            _ = try await machine.sceneDidBecomeActive(
                boundaryID: identifier("boundary:open-b"),
                recordID: identifier("record:001-session-open-b"),
                sessionID: identifier("session:synthetic-b"),
                clockEpochID: identifier("clock-epoch:synthetic-b"),
                recordedWallTimeUnixNS: baseWallTime + 1_000_000,
                monotonicTimeNS: 1_000
            )
            XCTFail("Expected active-session conflict")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .activeSessionConflict(
                    currentSessionID: identifier("session:synthetic-a"),
                    currentClockEpochID: identifier("clock-epoch:synthetic-a"),
                    proposedSessionID: identifier("session:synthetic-b"),
                    proposedClockEpochID: identifier("clock-epoch:synthetic-b")
                )
            )
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 1)
        XCTAssertEqual(
            snapshot.state.latestBoundaryReference,
            openRecord.reference
        )
        XCTAssertEqual(
            snapshot.state.observationWindowState,
            .open
        )
    }

    func testCloseAndDisconnectBeforeFirstSessionAreRejected() async throws {
        let machine = makeMachine()

        do {
            _ = try await machine.sceneWillResignActive(
                boundaryID: identifier("boundary:close-none"),
                recordID: identifier("record:close-none"),
                sessionID: identifier("session:none"),
                recordedWallTimeUnixNS: baseWallTime,
                monotonicTimeNS: 1
            )
            XCTFail("Expected no-current-session close rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .noCurrentSession(
                    event: .sceneWillResignActive
                )
            )
        }

        do {
            _ = try await machine.sceneDidDisconnect(
                boundaryID: identifier("boundary:disconnect-none"),
                recordID: identifier("record:disconnect-none"),
                sessionID: identifier("session:none"),
                recordedWallTimeUnixNS: baseWallTime,
                monotonicTimeNS: 1
            )
            XCTFail("Expected no-current-session disconnect rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .noCurrentSession(
                    event: .sceneDidDisconnect
                )
            )
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.state, .awaitingFirstSession)
        XCTAssertEqual(snapshot.chain.recordCount, 0)
    }

    func testFailedOpeningLeavesStateAndSingleUseIdentitiesUnchanged() async throws {
        let machine = makeMachine()
        let sessionID = identifier("session:synthetic-a")
        let clockEpochID = identifier("clock-epoch:synthetic-a")
        let recordID = identifier("record:000-session-open-a")

        do {
            _ = try await machine.sceneDidBecomeActive(
                boundaryID: identifier("boundary:open-a"),
                recordID: recordID,
                sessionID: sessionID,
                clockEpochID: clockEpochID,
                recordedWallTimeUnixNS: -1,
                monotonicTimeNS: 1_000
            )
            XCTFail("Expected negative wall-time rejection")
        } catch {
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .negativeRecordedWallTime
            )
        }

        let afterFailure = try await machine.snapshot()
        XCTAssertEqual(afterFailure.state, .awaitingFirstSession)
        XCTAssertEqual(afterFailure.chain.recordCount, 0)

        let corrected = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-a"),
            recordID: recordID,
            sessionID: sessionID,
            clockEpochID: clockEpochID,
            recordedWallTimeUnixNS: baseWallTime,
            monotonicTimeNS: 1_000
        )
        let recorded = try requireRecorded(corrected)

        XCTAssertEqual(recorded.record.digestSubject.sequenceIndex, 0)
        XCTAssertEqual(recorded.record.digestSubject.recordID, recordID)
        XCTAssertEqual(
            recorded.record.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
    }

    func testWindowCloseRecordsOnceAndDuplicateCloseIsIgnored() async throws {
        let machine = makeMachine()
        let openRecord = try await openSessionA(
            on: machine
        )
        let closeRecord = try await closeSessionA(
            on: machine
        )

        XCTAssertEqual(closeRecord.digestSubject.sequenceIndex, 1)
        XCTAssertEqual(
            closeRecord.digestSubject.previousRecordSHA256,
            openRecord.recordSHA256
        )
        XCTAssertEqual(
            closeRecord.recordSHA256.rawValue,
            "a2a218c7aff9d2843819c9596ed63d4dfe6051b2a1a0dcf9da4ae1c8d561401e"
        )

        let duplicate = try await machine.sceneWillResignActive(
            boundaryID: identifier("boundary:duplicate-close-a"),
            recordID: identifier("record:duplicate-close-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 2_000_000,
            monotonicTimeNS: 3_000
        )
        let ignored = try requireIgnoredDuplicate(
            duplicate
        )

        XCTAssertEqual(
            ignored.event,
            .sceneWillResignActive
        )
        XCTAssertEqual(
            ignored.existingBoundary,
            closeRecord.reference
        )

        let snapshot = try await machine.snapshot()
        guard case let .observationWindowClosed(
            sessionID,
            clockEpochID,
            storedOpenBoundary,
            storedCloseBoundary
        ) = snapshot.state else {
            return XCTFail(
                "Expected a closed observation window"
            )
        }

        XCTAssertEqual(sessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(clockEpochID, identifier("clock-epoch:synthetic-a"))
        XCTAssertEqual(storedOpenBoundary, openRecord.reference)
        XCTAssertEqual(storedCloseBoundary, closeRecord.reference)
        XCTAssertEqual(
            snapshot.state.observationGapStartBoundary,
            closeRecord.reference
        )
        XCTAssertEqual(snapshot.chain.recordCount, 2)
    }

    func testStaleCloseAndDisconnectCallbacksAreRejectedWithoutConsumingRecordID() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(
            on: machine
        )
        let reusableRecordID = identifier("record:001-session-close-a")

        for event in [
            SessionBoundaryLifecycleEvent.sceneWillResignActive,
            .sceneDidDisconnect,
        ] {
            do {
                switch event {
                case .sceneWillResignActive:
                    _ = try await machine.sceneWillResignActive(
                        boundaryID: identifier("boundary:stale-close"),
                        recordID: reusableRecordID,
                        sessionID: identifier("session:stale"),
                        recordedWallTimeUnixNS: baseWallTime + 1_000_000,
                        monotonicTimeNS: 2_000
                    )
                case .sceneDidDisconnect:
                    _ = try await machine.sceneDidDisconnect(
                        boundaryID: identifier("boundary:stale-disconnect"),
                        recordID: reusableRecordID,
                        sessionID: identifier("session:stale"),
                        recordedWallTimeUnixNS: baseWallTime + 1_000_000,
                        monotonicTimeNS: 2_000
                    )
                case .sceneDidBecomeActive:
                    XCTFail("Unexpected lifecycle event in stale-callback test")
                }
                XCTFail("Expected stale callback rejection")
            } catch {
                XCTAssertEqual(
                    error as? SessionBoundaryStateMachineError,
                    .callbackSessionMismatch(
                        event: event,
                        expectedSessionID: identifier("session:synthetic-a"),
                        actualSessionID: identifier("session:stale")
                    )
                )
            }
        }

        let beforeValidClose = try await machine.snapshot()
        XCTAssertEqual(beforeValidClose.chain.recordCount, 1)
        XCTAssertEqual(beforeValidClose.state.observationWindowState, .open)

        let close = try await machine.sceneWillResignActive(
            boundaryID: identifier("boundary:close-a"),
            recordID: reusableRecordID,
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000,
            monotonicTimeNS: 2_000
        )
        let recorded = try requireRecorded(close)

        XCTAssertEqual(recorded.record.digestSubject.recordID, reusableRecordID)
        XCTAssertEqual(recorded.record.digestSubject.sequenceIndex, 1)
    }

    func testCloseThenNewSessionMaterializesExactObservationGapAndParityChain() async throws {
        let machine = makeMachine()
        let openA = try await openSessionA(
            on: machine
        )
        let closeA = try await closeSessionA(
            on: machine
        )
        let openBResult = try await openSessionB(
            on: machine
        )
        let openB = openBResult.record
        let gap = try XCTUnwrap(
            openBResult.completedGap
        )

        XCTAssertEqual(openA.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5")
        XCTAssertEqual(closeA.recordSHA256.rawValue,
            "a2a218c7aff9d2843819c9596ed63d4dfe6051b2a1a0dcf9da4ae1c8d561401e")
        XCTAssertEqual(openB.recordSHA256.rawValue,
            "8e387a16b58c120d75fb9bd14adac14ca1b5afe4b4264cd040ddea0ba4f3c4cf")
        XCTAssertEqual(openB.digestSubject.sequenceIndex, 2)
        XCTAssertEqual(openB.digestSubject.previousRecordSHA256, closeA.recordSHA256)

        XCTAssertEqual(gap.sourceSessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(gap.sourceClockEpochID, identifier("clock-epoch:synthetic-a"))
        XCTAssertEqual(gap.targetSessionID, identifier("session:synthetic-b"))
        XCTAssertEqual(gap.targetClockEpochID, identifier("clock-epoch:synthetic-b"))
        XCTAssertEqual(gap.gapStartBoundary, closeA.reference)
        XCTAssertEqual(gap.gapEndBoundary, openB.reference)

        let snapshot = try await machine.snapshot()
        guard case let .observationWindowOpen(
            sessionID,
            clockEpochID,
            openBoundary,
            previousSessionID,
            precedingGap
        ) = snapshot.state else {
            return XCTFail(
                "Expected the second observation window to be open"
            )
        }

        XCTAssertEqual(sessionID, identifier("session:synthetic-b"))
        XCTAssertEqual(clockEpochID, identifier("clock-epoch:synthetic-b"))
        XCTAssertEqual(openBoundary, openB.reference)
        XCTAssertEqual(previousSessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(precedingGap, gap)
        XCTAssertEqual(snapshot.state.completedObservationGap, gap)
        XCTAssertEqual(snapshot.state.observationGapStartBoundary, closeA.reference)
        XCTAssertEqual(snapshot.chain.recordCount, 3)
        XCTAssertEqual(snapshot.chain.nextSequenceIndex, 3)
    }

    func testSessionAndClockEpochIDsAreSingleUseAndRejectedOpeningsAreAtomic() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(on: machine)
        _ = try await closeSessionA(on: machine)
        let reusableRecordID = identifier("record:002-session-open-b")

        do {
            _ = try await machine.sceneDidBecomeActive(
                boundaryID: identifier("boundary:reuse-session-a"),
                recordID: reusableRecordID,
                sessionID: identifier("session:synthetic-a"),
                clockEpochID: identifier("clock-epoch:synthetic-b"),
                recordedWallTimeUnixNS: baseWallTime + 2_000_000,
                monotonicTimeNS: 1_000
            )
            XCTFail("Expected reused session ID rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .sessionIDReused(identifier("session:synthetic-a"))
            )
        }

        do {
            _ = try await machine.sceneDidBecomeActive(
                boundaryID: identifier("boundary:reuse-epoch-a"),
                recordID: reusableRecordID,
                sessionID: identifier("session:synthetic-b"),
                clockEpochID: identifier("clock-epoch:synthetic-a"),
                recordedWallTimeUnixNS: baseWallTime + 2_000_000,
                monotonicTimeNS: 1_000
            )
            XCTFail("Expected reused clock epoch rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .clockEpochIDReused(identifier("clock-epoch:synthetic-a"))
            )
        }

        let beforeCorrectedOpen = try await machine.snapshot()
        XCTAssertEqual(beforeCorrectedOpen.chain.recordCount, 2)
        XCTAssertEqual(beforeCorrectedOpen.state.observationWindowState, .closed)

        let corrected = try await openSessionB(
            on: machine,
            recordID: reusableRecordID.rawValue
        )

        XCTAssertEqual(corrected.record.digestSubject.recordID, reusableRecordID)
        XCTAssertEqual(corrected.record.digestSubject.sequenceIndex, 2)
        XCTAssertNotNil(corrected.completedGap)
    }

    func testDisconnectFromOpenSessionTerminatesOnceAndRejectsOtherLaterEvents() async throws {
        let machine = makeMachine()
        let open = try await openSessionA(on: machine)

        let disconnect = try await machine.sceneDidDisconnect(
            boundaryID: identifier("boundary:disconnect-a"),
            recordID: identifier("record:001-session-disconnect-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000,
            monotonicTimeNS: 2_000
        )
        let terminal = try requireRecorded(disconnect).record

        let duplicateDisconnect = try await machine.sceneDidDisconnect(
            boundaryID: identifier("boundary:duplicate-disconnect-a"),
            recordID: identifier("record:duplicate-disconnect-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 2_000_000,
            monotonicTimeNS: 3_000
        )
        let ignored = try requireIgnoredDuplicate(duplicateDisconnect)

        XCTAssertEqual(ignored.event, .sceneDidDisconnect)
        XCTAssertEqual(ignored.existingBoundary, terminal.reference)

        do {
            _ = try await machine.sceneWillResignActive(
                boundaryID: identifier("boundary:late-close-a"),
                recordID: identifier("record:late-close-a"),
                sessionID: identifier("session:synthetic-a"),
                recordedWallTimeUnixNS: baseWallTime + 2_000_000,
                monotonicTimeNS: 3_000
            )
            XCTFail("Expected close-after-terminal rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .eventAfterTerminalSession(
                    event: .sceneWillResignActive,
                    sessionID: identifier("session:synthetic-a")
                )
            )
        }

        do {
            _ = try await machine.sceneDidBecomeActive(
                boundaryID: identifier("boundary:reopen-a"),
                recordID: identifier("record:reopen-a"),
                sessionID: identifier("session:synthetic-a"),
                clockEpochID: identifier("clock-epoch:synthetic-a"),
                recordedWallTimeUnixNS: baseWallTime + 2_000_000,
                monotonicTimeNS: 3_000
            )
            XCTFail("Expected same-session reopen rejection")
        } catch {
            XCTAssertEqual(
                error as? SessionBoundaryStateMachineError,
                .eventAfterTerminalSession(
                    event: .sceneDidBecomeActive,
                    sessionID: identifier("session:synthetic-a")
                )
            )
        }

        let snapshot = try await machine.snapshot()
        guard case let .sessionTerminated(
            sessionID,
            clockEpochID,
            openBoundary,
            closeBoundary,
            terminalBoundary
        ) = snapshot.state else {
            return XCTFail("Expected terminated session state")
        }

        XCTAssertEqual(sessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(clockEpochID, identifier("clock-epoch:synthetic-a"))
        XCTAssertEqual(openBoundary, open.reference)
        XCTAssertNil(closeBoundary)
        XCTAssertEqual(terminalBoundary, terminal.reference)
        XCTAssertEqual(snapshot.state.observationGapStartBoundary, terminal.reference)
        XCTAssertEqual(snapshot.chain.recordCount, 2)
    }

    func testDisconnectAfterClosePreservesCloseBoundaryAsLaterGapStart() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(on: machine)
        let close = try await closeSessionA(on: machine)

        let disconnect = try await machine.sceneDidDisconnect(
            boundaryID: identifier("boundary:disconnect-a"),
            recordID: identifier("record:002-session-disconnect-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 2_000_000,
            monotonicTimeNS: 3_000
        )
        let terminal = try requireRecorded(disconnect).record

        let terminalSnapshot = try await machine.snapshot()
        guard case let .sessionTerminated(
            _,
            _,
            _,
            storedCloseBoundary,
            storedTerminalBoundary
        ) = terminalSnapshot.state else {
            return XCTFail("Expected terminated state after close")
        }

        XCTAssertEqual(storedCloseBoundary, close.reference)
        XCTAssertEqual(storedTerminalBoundary, terminal.reference)
        XCTAssertEqual(
            terminalSnapshot.state.observationGapStartBoundary,
            close.reference
        )

        let openB = try await openSessionB(
            on: machine,
            recordID: "record:003-session-open-b",
            wallTimeOffset: 3_000_000
        )
        let gap = try XCTUnwrap(openB.completedGap)

        XCTAssertEqual(gap.gapStartBoundary, close.reference)
        XCTAssertEqual(gap.gapEndBoundary, openB.record.reference)
        XCTAssertNotEqual(gap.gapStartBoundary, terminal.reference)
        let reopenedSnapshot = try await machine.snapshot()
        XCTAssertEqual(
            reopenedSnapshot.chain.recordCount,
            4
        )
    }

    func testNewSessionAfterDirectTerminationUsesTerminalBoundaryAsGapStart() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(on: machine)

        let disconnect = try await machine.sceneDidDisconnect(
            boundaryID: identifier("boundary:disconnect-a"),
            recordID: identifier("record:001-session-disconnect-a"),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000,
            monotonicTimeNS: 2_000
        )
        let terminal = try requireRecorded(disconnect).record

        let openB = try await openSessionB(
            on: machine,
            recordID: "record:002-session-open-b",
            wallTimeOffset: 2_000_000
        )
        let gap = try XCTUnwrap(openB.completedGap)

        XCTAssertEqual(gap.gapStartBoundary, terminal.reference)
        XCTAssertEqual(gap.gapEndBoundary, openB.record.reference)
        XCTAssertEqual(gap.sourceSessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(gap.targetSessionID, identifier("session:synthetic-b"))
    }

    func testSnapshotsAreImmutableValueViewsAcrossLaterTransitions() async throws {
        let machine = makeMachine()
        let open = try await openSessionA(on: machine)
        let openSnapshot = try await machine.snapshot()

        let close = try await closeSessionA(on: machine)
        let closedSnapshot = try await machine.snapshot()

        XCTAssertEqual(openSnapshot.chain.recordCount, 1)
        XCTAssertEqual(openSnapshot.state.observationWindowState, .open)
        XCTAssertEqual(openSnapshot.state.latestBoundaryReference, open.reference)

        XCTAssertEqual(closedSnapshot.chain.recordCount, 2)
        XCTAssertEqual(closedSnapshot.state.observationWindowState, .closed)
        XCTAssertEqual(closedSnapshot.state.latestBoundaryReference, close.reference)

        XCTAssertEqual(openSnapshot.chain.recordCount, 1)
        XCTAssertEqual(openSnapshot.state.observationWindowState, .open)
    }

    func testIdenticalLifecycleInputsProduceByteIdenticalStateAndRecords() async throws {
        let first = makeMachine()
        let second = makeMachine()

        _ = try await openSessionA(on: first)
        _ = try await closeSessionA(on: first)
        _ = try await openSessionB(on: first)

        _ = try await openSessionA(on: second)
        _ = try await closeSessionA(on: second)
        _ = try await openSessionB(on: second)

        let firstSnapshot = try await first.snapshot()
        let secondSnapshot = try await second.snapshot()

        XCTAssertEqual(firstSnapshot, secondSnapshot)
        XCTAssertEqual(
            firstSnapshot.chain.records.map { $0.canonicalBytes() },
            secondSnapshot.chain.records.map { $0.canonicalBytes() }
        )
    }
}
