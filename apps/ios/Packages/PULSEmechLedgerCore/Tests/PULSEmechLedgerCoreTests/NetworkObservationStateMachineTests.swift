import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NetworkObservationStateMachineTests: XCTestCase {
    private enum TestFailure: Error {
        case expectedRecordedLifecycleResult
        case expectedOpenNetworkState
        case expectedObservedAvailability
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

    private func digest(
        _ rawValue: String
    ) -> SHA256HexDigest {
        try! SHA256HexDigest(rawValue)
    }

    private func makeMachine() -> NetworkObservationStateMachine {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: .syntheticReference
        )
        return NetworkObservationStateMachine(
            chain: chain
        )
    }

    private func wifiState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: false,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .wifi,
            ]
        )
    }

    private func cellularState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [
                .cellular,
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: true,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .cellular,
            ]
        )
    }

    @discardableResult
    private func openSessionA(
        on machine: NetworkObservationStateMachine
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

    @discardableResult
    private func closeSessionA(
        on machine: NetworkObservationStateMachine,
        recordID: String = "record:003-session-close-a",
        wallTimeOffset: Int64 = 3_000_000,
        monotonicTimeNS: Int64 = 4_000
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneWillResignActive(
            boundaryID: identifier("boundary:close-a"),
            recordID: identifier(recordID),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + wallTimeOffset,
            monotonicTimeNS: monotonicTimeNS
        )
        return try requireRecorded(result).record
    }

    @discardableResult
    private func disconnectSessionA(
        on machine: NetworkObservationStateMachine,
        recordID: String = "record:003-session-terminate-a",
        wallTimeOffset: Int64 = 3_000_000,
        monotonicTimeNS: Int64 = 4_000
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneDidDisconnect(
            boundaryID: identifier("boundary:terminate-a"),
            recordID: identifier(recordID),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + wallTimeOffset,
            monotonicTimeNS: monotonicTimeNS
        )
        return try requireRecorded(result).record
    }

    @discardableResult
    private func openSessionB(
        on machine: NetworkObservationStateMachine,
        recordID: String = "record:004-session-open-b",
        wallTimeOffset: Int64 = 4_000_000
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

    private func wifiObservationA(
        eventRecordID: String = "record:001-path-wifi-a",
        snapshotRecordID: String = "record:002-snapshot-wifi-a",
        eventID: String = "event:path-wifi-a",
        snapshotID: String = "snapshot:wifi-a",
        eventWallTimeOffset: Int64 = 1_000_000,
        snapshotWallTimeOffset: Int64 = 2_000_000,
        eventMonotonicTimeNS: Int64 = 2_000,
        snapshotMonotonicTimeNS: Int64 = 3_000
    ) throws -> NetworkPathUpdateObservation {
        NetworkPathUpdateObservation(
            eventID: identifier(eventID),
            eventRecordID: identifier(eventRecordID),
            eventRecordedWallTimeUnixNS: baseWallTime + eventWallTimeOffset,
            eventMonotonicTimeNS: eventMonotonicTimeNS,
            snapshotID: identifier(snapshotID),
            snapshotRecordID: identifier(snapshotRecordID),
            snapshotRecordedWallTimeUnixNS: baseWallTime + snapshotWallTimeOffset,
            snapshotMonotonicTimeNS: snapshotMonotonicTimeNS,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            appLifecycleActivationState: .foregroundActive,
            networkPathState: try wifiState()
        )
    }

    private func cellularObservationA() throws -> NetworkPathUpdateObservation {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-cellular-a"),
            eventRecordID: identifier("record:003-path-cellular-a"),
            eventRecordedWallTimeUnixNS: baseWallTime + 3_000_000,
            eventMonotonicTimeNS: 4_000,
            snapshotID: identifier("snapshot:cellular-a"),
            snapshotRecordID: identifier("record:004-snapshot-cellular-a"),
            snapshotRecordedWallTimeUnixNS: baseWallTime + 4_000_000,
            snapshotMonotonicTimeNS: 5_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            appLifecycleActivationState: .foregroundActive,
            networkPathState: try cellularState()
        )
    }

    private func wifiObservationB() throws -> NetworkPathUpdateObservation {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-wifi-b"),
            eventRecordID: identifier("record:005-path-wifi-b"),
            eventRecordedWallTimeUnixNS: baseWallTime + 5_000_000,
            eventMonotonicTimeNS: 2_000,
            snapshotID: identifier("snapshot:wifi-b"),
            snapshotRecordID: identifier("record:006-snapshot-wifi-b"),
            snapshotRecordedWallTimeUnixNS: baseWallTime + 6_000_000,
            snapshotMonotonicTimeNS: 3_000,
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            appLifecycleActivationState: .foregroundActive,
            networkPathState: try wifiState()
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
            throw TestFailure.expectedRecordedLifecycleResult
        }
        return (record, completedGap)
    }

    private func requireOpenState(
        _ state: NetworkObservationStateMachineState,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws -> (
        sessionID: LedgerIdentifier,
        clockEpochID: LedgerIdentifier,
        openBoundary: LedgerRecordReference,
        availability: NetworkObservationWindowAvailability,
        precedingGap: SessionBoundaryObservationGap?,
        retainedGapSource: NetworkObservedSnapshot?
    ) {
        guard case let .observationWindowOpen(
            sessionID,
            clockEpochID,
            openBoundary,
            availability,
            precedingGap,
            retainedGapSource
        ) = state else {
            XCTFail(
                "Expected an open network-observation state",
                file: file,
                line: line
            )
            throw TestFailure.expectedOpenNetworkState
        }
        return (
            sessionID,
            clockEpochID,
            openBoundary,
            availability,
            precedingGap,
            retainedGapSource
        )
    }

    private func requireObservedAvailability(
        _ availability: NetworkObservationWindowAvailability,
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws -> (
        first: NetworkObservedSnapshot,
        latest: NetworkObservedSnapshot
    ) {
        guard case let .observed(first, latest) = availability else {
            XCTFail(
                "Expected observed network availability",
                file: file,
                line: line
            )
            throw TestFailure.expectedObservedAvailability
        }
        return (first, latest)
    }

    func testInitialSnapshotHasNoSessionAndEmptyChain() async throws {
        let machine = makeMachine()
        let snapshot = try await machine.snapshot()

        XCTAssertEqual(snapshot.networkState, .awaitingFirstSession)
        XCTAssertEqual(snapshot.lifecycleState, .awaitingFirstSession)
        XCTAssertEqual(snapshot.chain.recordCount, 0)
        XCTAssertEqual(snapshot.chain.nextSequenceIndex, 0)
        XCTAssertNil(snapshot.chain.latestRecordReference)
    }

    func testOpeningSessionResetsNetworkSurfaceToAwaitingFirstCallback() async throws {
        let machine = makeMachine()
        let openRecord = try await openSessionA(on: machine)
        let snapshot = try await machine.snapshot()
        let openState = try requireOpenState(snapshot.networkState)

        XCTAssertEqual(openState.sessionID, identifier("session:synthetic-a"))
        XCTAssertEqual(
            openState.clockEpochID,
            identifier("clock-epoch:synthetic-a")
        )
        XCTAssertEqual(openState.openBoundary, openRecord.reference)
        XCTAssertEqual(
            openState.availability,
            .awaitingFreshCallback(reason: .awaitingFirstPathUpdate)
        )
        XCTAssertNil(openState.precedingGap)
        XCTAssertNil(openState.retainedGapSource)
        XCTAssertEqual(snapshot.chain.recordCount, 1)
    }

    func testSnapshotPayloadMatchesExactFirstReferenceBytes() throws {
        let eventReference = try LedgerRecordReference(
            recordID: identifier("record:001-path-wifi-a"),
            recordSHA256: digest(
                "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980"
            ),
            sequenceIndex: 1
        )
        let payload = NetworkPathStateSnapshotPayload(
            snapshotID: identifier("snapshot:wifi-a"),
            snapshotRole: .sourceEndpoint,
            sourceEventBinding: eventReference,
            appLifecycleActivationState: .foregroundActive,
            networkPathState: try wifiState()
        )
        let expected =
            #"{"network_freshness_status":"fresh_callback_bound_in_same_session","payload_type":"state_snapshot","snapshot_id":"snapshot:wifi-a","snapshot_role":"source_endpoint","source_event_binding":{"record_id":"record:001-path-wifi-a","record_sha256":"297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980","sequence_index":1},"surfaces":[{"availability":"observed","source_interface":"UIKit UIScene.activationState and UISceneDelegate lifecycle callbacks","state":{"activation_state":"foreground_active"},"surface_id":"app_lifecycle"},{"availability":"observed","source_interface":"Network.framework NWPathMonitor.pathUpdateHandler","state":{"available_interface_types":["wifi","cellular"],"is_constrained":false,"is_expensive":false,"status":"satisfied","supports_dns":true,"supports_ipv4":true,"supports_ipv6":true,"used_interface_types":["wifi"]},"surface_id":"network_path"}]}"#

        XCTAssertEqual(payload.canonicalBytes(), Data(expected.utf8))
        XCTAssertEqual(payload.canonicalBytes().count, 883)
    }

    func testFirstAcceptedCallbackAtomicallyMatchesPythonEventAndSnapshotRecords() async throws {
        let machine = makeMachine()
        let openRecord = try await openSessionA(on: machine)
        let result = try await machine.observePathUpdate(
            try wifiObservationA()
        )

        XCTAssertEqual(
            openRecord.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(
            result.eventRecord.recordSHA256.rawValue,
            "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980"
        )
        XCTAssertEqual(
            result.snapshotRecord.recordSHA256.rawValue,
            "ca0ff596004618e8cb4b1e3f08198f3496548da142a4696745e9677700f175c9"
        )
        XCTAssertEqual(result.eventRecord.canonicalBytes().count, 1_774)
        XCTAssertEqual(result.snapshotRecord.canonicalBytes().count, 2_091)
        XCTAssertEqual(
            result.snapshotRecord.digestSubject.previousRecordSHA256,
            result.eventRecord.recordSHA256
        )
        XCTAssertEqual(result.observedSnapshot.snapshotRole, .sourceEndpoint)
        XCTAssertNil(result.previousSnapshotInSession)
        XCTAssertNil(result.changedFieldsFromPreviousSnapshot)
        XCTAssertNil(result.precedingObservationGap)
        XCTAssertNil(result.retainedGapSourceSnapshot)

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 3)
        XCTAssertEqual(
            snapshot.chain.records.map(\.digestSubject.recordType),
            [
                .sessionBoundary,
                .observationEvent,
                .stateSnapshot,
            ]
        )
        let openState = try requireOpenState(snapshot.networkState)
        let observed = try requireObservedAvailability(openState.availability)
        XCTAssertEqual(observed.first, result.observedSnapshot)
        XCTAssertEqual(observed.latest, result.observedSnapshot)
    }

    func testSecondCallbackRetainsFirstFreshSnapshotAndReportsExactChanges() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let first = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let second = try await machine.observePathUpdate(
            try cellularObservationA()
        )

        XCTAssertEqual(
            second.eventRecord.recordSHA256.rawValue,
            "b83cb83c6f4ad05d799b502d0f8a1df4b39a89ece07dac7faa34e22589e58ae8"
        )
        XCTAssertEqual(
            second.snapshotRecord.recordSHA256.rawValue,
            "0e126ee418a52b2aa8eb456c4e1f799d5ee556d577bd986b0fe8f9835f714d2d"
        )
        XCTAssertEqual(second.observedSnapshot.snapshotRole, .targetEndpoint)
        XCTAssertEqual(second.previousSnapshotInSession, first.observedSnapshot)
        XCTAssertEqual(
            second.changedFieldsFromPreviousSnapshot,
            [
                .isExpensive,
                .usedInterfaceTypes,
            ]
        )

        let snapshot = try await machine.snapshot()
        let openState = try requireOpenState(snapshot.networkState)
        let observed = try requireObservedAvailability(openState.availability)
        XCTAssertEqual(observed.first, first.observedSnapshot)
        XCTAssertEqual(observed.latest, second.observedSnapshot)
        XCTAssertEqual(snapshot.chain.recordCount, 5)
    }

    func testEqualStateCallbackIsRetainedWithoutChangedFields() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let first = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let repeated = try await machine.observePathUpdate(
            try wifiObservationA(
                eventRecordID: "record:003-path-wifi-a-repeat",
                snapshotRecordID: "record:004-snapshot-wifi-a-repeat",
                eventID: "event:path-wifi-a-repeat",
                snapshotID: "snapshot:wifi-a-repeat",
                eventWallTimeOffset: 3_000_000,
                snapshotWallTimeOffset: 4_000_000,
                eventMonotonicTimeNS: 4_000,
                snapshotMonotonicTimeNS: 5_000
            )
        )

        XCTAssertEqual(repeated.previousSnapshotInSession, first.observedSnapshot)
        XCTAssertEqual(repeated.changedFieldsFromPreviousSnapshot, [])

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 5)
        XCTAssertEqual(
            snapshot.chain.records.filter {
                $0.digestSubject.recordType == .transition
            }.count,
            0
        )
    }

    func testPathUpdateBeforeSessionOpenIsRejectedWithoutChainMutation() async throws {
        let machine = makeMachine()

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationA()
            )
            XCTFail("Expected path update before session opening to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .noOpenObservationWindow)
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 0)
        XCTAssertEqual(snapshot.networkState, .awaitingFirstSession)
    }

    func testWrongSessionEpochAndInactiveLifecycleAreRejectedWithoutMutation() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)

        var observation = try wifiObservationA()
        observation = NetworkPathUpdateObservation(
            eventID: observation.eventID,
            eventRecordID: observation.eventRecordID,
            eventRecordedWallTimeUnixNS: observation.eventRecordedWallTimeUnixNS,
            eventMonotonicTimeNS: observation.eventMonotonicTimeNS,
            snapshotID: observation.snapshotID,
            snapshotRecordID: observation.snapshotRecordID,
            snapshotRecordedWallTimeUnixNS: observation.snapshotRecordedWallTimeUnixNS,
            snapshotMonotonicTimeNS: observation.snapshotMonotonicTimeNS,
            sessionID: identifier("session:stale"),
            clockEpochID: observation.clockEpochID,
            appLifecycleActivationState: .foregroundActive,
            networkPathState: observation.networkPathState
        )
        do {
            _ = try await machine.observePathUpdate(observation)
            XCTFail("Expected stale session to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .callbackSessionMismatch(
                    expected: identifier("session:synthetic-a"),
                    actual: identifier("session:stale")
                )
            )
        }

        let base = try wifiObservationA()
        observation = NetworkPathUpdateObservation(
            eventID: base.eventID,
            eventRecordID: base.eventRecordID,
            eventRecordedWallTimeUnixNS: base.eventRecordedWallTimeUnixNS,
            eventMonotonicTimeNS: base.eventMonotonicTimeNS,
            snapshotID: base.snapshotID,
            snapshotRecordID: base.snapshotRecordID,
            snapshotRecordedWallTimeUnixNS: base.snapshotRecordedWallTimeUnixNS,
            snapshotMonotonicTimeNS: base.snapshotMonotonicTimeNS,
            sessionID: base.sessionID,
            clockEpochID: identifier("clock-epoch:stale"),
            appLifecycleActivationState: .foregroundActive,
            networkPathState: base.networkPathState
        )
        do {
            _ = try await machine.observePathUpdate(observation)
            XCTFail("Expected stale clock epoch to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .callbackClockEpochMismatch(
                    expected: identifier("clock-epoch:synthetic-a"),
                    actual: identifier("clock-epoch:stale")
                )
            )
        }

        observation = NetworkPathUpdateObservation(
            eventID: base.eventID,
            eventRecordID: base.eventRecordID,
            eventRecordedWallTimeUnixNS: base.eventRecordedWallTimeUnixNS,
            eventMonotonicTimeNS: base.eventMonotonicTimeNS,
            snapshotID: base.snapshotID,
            snapshotRecordID: base.snapshotRecordID,
            snapshotRecordedWallTimeUnixNS: base.snapshotRecordedWallTimeUnixNS,
            snapshotMonotonicTimeNS: base.snapshotMonotonicTimeNS,
            sessionID: base.sessionID,
            clockEpochID: base.clockEpochID,
            appLifecycleActivationState: .background,
            networkPathState: base.networkPathState
        )
        do {
            _ = try await machine.observePathUpdate(observation)
            XCTFail("Expected inactive lifecycle state to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .appLifecycleNotForegroundActive(.background)
            )
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 1)
        XCTAssertEqual(
            try requireOpenState(snapshot.networkState).availability,
            .awaitingFreshCallback(reason: .awaitingFirstPathUpdate)
        )
    }

    func testLateCallbackAfterWindowCloseIsRejectedAndRetainsGapSource() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let observed = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let closeRecord = try await closeSessionA(on: machine)

        do {
            _ = try await machine.observePathUpdate(
                NetworkPathUpdateObservation(
                    eventID: identifier("event:path-late-a"),
                    eventRecordID: identifier("record:004-path-late-a"),
                    eventRecordedWallTimeUnixNS: baseWallTime + 4_000_000,
                    eventMonotonicTimeNS: 5_000,
                    snapshotID: identifier("snapshot:late-a"),
                    snapshotRecordID: identifier("record:005-snapshot-late-a"),
                    snapshotRecordedWallTimeUnixNS: baseWallTime + 5_000_000,
                    snapshotMonotonicTimeNS: 6_000,
                    sessionID: identifier("session:synthetic-a"),
                    clockEpochID: identifier("clock-epoch:synthetic-a"),
                    appLifecycleActivationState: .foregroundActive,
                    networkPathState: try cellularState()
                )
            )
            XCTFail("Expected late callback after close to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .noOpenObservationWindow)
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 4)
        XCTAssertEqual(
            snapshot.networkState,
            .observationWindowClosed(
                sessionID: identifier("session:synthetic-a"),
                clockEpochID: identifier("clock-epoch:synthetic-a"),
                closeBoundary: closeRecord.reference,
                retainedGapSourceSnapshot: observed.observedSnapshot
            )
        )
    }

    func testReopenRequiresFreshCallbackAndCarriesExactGapEndpoints() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let source = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let closeRecord = try await closeSessionA(on: machine)
        let opening = try await openSessionB(on: machine)

        let beforeCallback = try await machine.snapshot()
        let waiting = try requireOpenState(beforeCallback.networkState)
        XCTAssertEqual(
            waiting.availability,
            .awaitingFreshCallback(
                reason: .awaitingFreshPostReopenPathUpdate
            )
        )
        XCTAssertEqual(
            waiting.retainedGapSource,
            source.observedSnapshot
        )
        XCTAssertEqual(
            waiting.precedingGap?.gapStartBoundary,
            closeRecord.reference
        )
        XCTAssertEqual(
            waiting.precedingGap?.gapEndBoundary,
            opening.record.reference
        )

        let target = try await machine.observePathUpdate(
            try wifiObservationB()
        )
        XCTAssertEqual(target.observedSnapshot.snapshotRole, .targetEndpoint)
        XCTAssertEqual(target.retainedGapSourceSnapshot, source.observedSnapshot)
        XCTAssertEqual(
            target.precedingObservationGap?.gapStartBoundary,
            closeRecord.reference
        )
        XCTAssertEqual(
            target.precedingObservationGap?.gapEndBoundary,
            opening.record.reference
        )

        let afterCallback = try await machine.snapshot()
        let openState = try requireOpenState(afterCallback.networkState)
        let observed = try requireObservedAvailability(openState.availability)
        XCTAssertEqual(observed.first, target.observedSnapshot)
        XCTAssertEqual(observed.latest, target.observedSnapshot)
        XCTAssertEqual(afterCallback.chain.recordCount, 7)
    }

    func testDirectDisconnectStartsNextGapAndRetainsLastSnapshot() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let source = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let terminal = try await disconnectSessionA(on: machine)
        let opening = try await openSessionB(on: machine)

        XCTAssertEqual(
            opening.completedGap?.gapStartBoundary,
            terminal.reference
        )
        XCTAssertEqual(
            opening.completedGap?.gapEndBoundary,
            opening.record.reference
        )

        let snapshot = try await machine.snapshot()
        let openState = try requireOpenState(snapshot.networkState)
        XCTAssertEqual(openState.retainedGapSource, source.observedSnapshot)
        XCTAssertEqual(
            openState.availability,
            .awaitingFreshCallback(
                reason: .awaitingFreshPostReopenPathUpdate
            )
        )
    }

    func testDependentPairFailureLeavesChainUnchangedAtomically() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)

        let invalid = try wifiObservationA(
            snapshotRecordID: "record:000-session-open-a"
        )
        do {
            _ = try await machine.observePathUpdate(invalid)
            XCTFail("Expected duplicate snapshot record ID to fail")
        } catch let error as LedgerRecordChainError {
            XCTAssertEqual(
                error,
                .duplicateRecordID(
                    identifier("record:000-session-open-a")
                )
            )
        }

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 1)
        XCTAssertEqual(
            snapshot.chain.records.map(\.digestSubject.recordType),
            [
                .sessionBoundary,
            ]
        )
        XCTAssertEqual(
            try requireOpenState(snapshot.networkState).availability,
            .awaitingFreshCallback(reason: .awaitingFirstPathUpdate)
        )
    }

    func testExactRepeatedActiveCallbackDoesNotResetObservedNetworkState() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let observed = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:duplicate-open-a"),
            recordID: identifier("record:duplicate-session-open-a"),
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            recordedWallTimeUnixNS: baseWallTime + 3_000_000,
            monotonicTimeNS: 4_000
        )
        guard case .ignoredDuplicate = result else {
            return XCTFail("Expected duplicate opening callback to be ignored")
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)
        XCTAssertEqual(
            after.networkState.latestObservedSnapshot,
            observed.observedSnapshot
        )
    }
}
