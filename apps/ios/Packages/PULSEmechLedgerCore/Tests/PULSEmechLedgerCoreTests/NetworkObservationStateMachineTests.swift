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

    private func fixtureObserverIdentity() throws -> DeviceLedgerObserverIdentity {
        try DeviceLedgerObserverIdentity(
            identityScope: .fixtureInstallation,
            keyOriginProfile: .fixtureSoftwareP256,
            publicKeyX963Uncompressed: Data(
                base64Encoded:
                    "BAIa75uP4gO+twVlypJYAjIKXK0JVnBPBArgoE50sEI+HbKkjFpxpQifk3hgoQs08yYzY850htpv1wl0/4u6i10="
            )!
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
        snapshotMonotonicTimeNS: Int64 = 3_000,
        coverageMaterialization: NetworkCoverageMaterializationInput? = nil,
        transitionMaterialization: NetworkTransitionMaterializationInput? = nil
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
            networkPathState: try wifiState(),
            coverageMaterialization: coverageMaterialization,
            transitionMaterialization: transitionMaterialization
        )
    }

    private func cellularObservationA(
        includeCoverage: Bool = true,
        coverageRecordID: String = "record:005-coverage-continuous",
        coverageIntervalID: String = "coverage:continuous-a",
        coverageWallTimeOffset: Int64 = 5_000_000,
        includeTransition: Bool = true,
        transitionRecordID: String = "record:006-transition-event-bound",
        transitionID: String =
            "transition:event-bound-wifi-to-cellular",
        transitionWallTimeOffset: Int64 = 6_000_000,
        transitionMonotonicTimeNS: Int64? = 6_000
    ) throws -> NetworkPathUpdateObservation {
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
            networkPathState: try cellularState(),
            coverageMaterialization: includeCoverage
                ? NetworkCoverageMaterializationInput(
                    intervalID: identifier(coverageIntervalID),
                    recordID: identifier(coverageRecordID),
                    recordedWallTimeUnixNS:
                        baseWallTime + coverageWallTimeOffset
                )
                : nil,
            transitionMaterialization: includeTransition
                ? NetworkTransitionMaterializationInput(
                    transitionID: identifier(transitionID),
                    recordID: identifier(transitionRecordID),
                    recordedWallTimeUnixNS:
                        baseWallTime + transitionWallTimeOffset,
                    eventBoundMonotonicTimeNS:
                        transitionMonotonicTimeNS
                )
                : nil
        )
    }

    private func wifiObservationB(
        eventRecordID: String = "record:005-path-wifi-b",
        snapshotRecordID: String = "record:006-snapshot-wifi-b",
        eventWallTimeOffset: Int64 = 5_000_000,
        snapshotWallTimeOffset: Int64 = 6_000_000,
        includeCoverage: Bool = true,
        coverageRecordID: String = "record:007-coverage-interrupted",
        coverageIntervalID: String =
            "coverage:interrupted-a-to-b-runtime",
        coverageWallTimeOffset: Int64 = 7_000_000,
        includeTransition: Bool = false,
        transitionRecordID: String =
            "record:008-transition-endpoint-difference",
        transitionID: String =
            "transition:endpoint-difference-cellular-to-wifi",
        transitionWallTimeOffset: Int64 = 8_000_000,
        transitionMonotonicTimeNS: Int64? = nil
    ) throws -> NetworkPathUpdateObservation {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-wifi-b"),
            eventRecordID: identifier(eventRecordID),
            eventRecordedWallTimeUnixNS: baseWallTime + eventWallTimeOffset,
            eventMonotonicTimeNS: 2_000,
            snapshotID: identifier("snapshot:wifi-b"),
            snapshotRecordID: identifier(snapshotRecordID),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + snapshotWallTimeOffset,
            snapshotMonotonicTimeNS: 3_000,
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier("clock-epoch:synthetic-b"),
            appLifecycleActivationState: .foregroundActive,
            networkPathState: try wifiState(),
            coverageMaterialization: includeCoverage
                ? NetworkCoverageMaterializationInput(
                    intervalID: identifier(coverageIntervalID),
                    recordID: identifier(coverageRecordID),
                    recordedWallTimeUnixNS:
                        baseWallTime + coverageWallTimeOffset
                )
                : nil,
            transitionMaterialization: includeTransition
                ? NetworkTransitionMaterializationInput(
                    transitionID: identifier(transitionID),
                    recordID: identifier(transitionRecordID),
                    recordedWallTimeUnixNS:
                        baseWallTime + transitionWallTimeOffset,
                    eventBoundMonotonicTimeNS:
                        transitionMonotonicTimeNS
                )
                : nil
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
        XCTAssertNil(result.coverageRecord)
        XCTAssertNil(result.coverageRelation)
        XCTAssertNil(result.transitionRecord)
        XCTAssertNil(result.transitionRelation)
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
        XCTAssertEqual(
            second.coverageRecord?.recordSHA256.rawValue,
            "5d5de19bdd2eddfc5f23791ede88b7afc13077f4c54810cef451e7602ec4df38"
        )
        XCTAssertEqual(
            second.coverageRecord?.digestSubject.recordType,
            .coverageInterval
        )
        XCTAssertEqual(
            second.coverageRecord?.digestSubject.previousRecordSHA256,
            second.snapshotRecord.recordSHA256
        )
        XCTAssertEqual(second.coverageRelation?.status, .continuous)
        XCTAssertEqual(
            second.transitionRecord?.recordSHA256.rawValue,
            "57396fbb180ed7eb6fd3b99f17fe86709616684ad16445b9559f879e20f8c594"
        )
        XCTAssertEqual(
            second.transitionRecord?.digestSubject.sequenceIndex,
            6
        )
        XCTAssertEqual(
            second.transitionRecord?.digestSubject.previousRecordSHA256,
            second.coverageRecord?.recordSHA256
        )
        XCTAssertEqual(
            second.transitionRelation?.transitionClass,
            .eventBound
        )
        XCTAssertEqual(
            second.transitionRelation?.changedFields,
            [.isExpensive, .usedInterfaceTypes]
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
        XCTAssertEqual(snapshot.chain.recordCount, 7)
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
                snapshotMonotonicTimeNS: 5_000,
                coverageMaterialization: NetworkCoverageMaterializationInput(
                    intervalID: identifier("coverage:continuous-a-repeat"),
                    recordID: identifier("record:005-coverage-continuous-repeat"),
                    recordedWallTimeUnixNS: baseWallTime + 5_000_000
                )
            )
        )

        XCTAssertEqual(repeated.previousSnapshotInSession, first.observedSnapshot)
        XCTAssertEqual(repeated.changedFieldsFromPreviousSnapshot, [])
        XCTAssertEqual(repeated.coverageRelation?.status, .continuous)
        XCTAssertNotNil(repeated.coverageRecord)
        XCTAssertNil(repeated.transitionRecord)
        XCTAssertNil(repeated.transitionRelation)

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 6)
        XCTAssertEqual(
            snapshot.chain.records.filter {
                $0.digestSubject.recordType == .coverageInterval
            }.count,
            1
        )
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
        XCTAssertEqual(
            target.coverageRecord?.recordSHA256.rawValue,
            "d46d2430e8a14aadf6dc97b7f18f45da0a94121b5c2253f5bb27f8fa5ebe1340"
        )
        XCTAssertEqual(target.coverageRelation?.status, .interrupted)
        XCTAssertNil(target.transitionRecord)
        XCTAssertNil(target.transitionRelation)
        XCTAssertEqual(
            target.coverageRecord?.digestSubject.recordType,
            .coverageInterval
        )
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
        XCTAssertEqual(afterCallback.chain.recordCount, 8)
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

    func testCoverageInputBeforeAnyEndpointRelationIsRejectedAtomically() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let before = try await machine.snapshot()
        let coverage = NetworkCoverageMaterializationInput(
            intervalID: identifier("coverage:not-permitted"),
            recordID: identifier("record:003-coverage-not-permitted"),
            recordedWallTimeUnixNS: baseWallTime + 3_000_000
        )

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationA(
                    coverageMaterialization: coverage
                )
            )
            XCTFail("Expected premature coverage input to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .coverageMaterializationNotPermitted)
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        XCTAssertNil(accepted.coverageRecord)
        XCTAssertEqual(accepted.eventRecord.digestSubject.sequenceIndex, 1)
    }

    func testContinuousCoverageIsRequiredBeforeAnyCallbackRecordsCommit() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(includeCoverage: false)
            )
            XCTFail("Expected missing continuous coverage to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .coverageMaterializationRequired(.continuous)
            )
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)

        let accepted = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        XCTAssertEqual(accepted.coverageRelation?.status, .continuous)
        XCTAssertEqual(accepted.eventRecord.digestSubject.sequenceIndex, 3)
        XCTAssertEqual(accepted.snapshotRecord.digestSubject.sequenceIndex, 4)
        XCTAssertEqual(accepted.coverageRecord?.digestSubject.sequenceIndex, 5)
        XCTAssertEqual(accepted.transitionRecord?.digestSubject.sequenceIndex, 6)
    }

    func testCoverageWallTimeCannotPrecedeTargetSnapshot() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    coverageWallTimeOffset: 3_000_000
                )
            )
            XCTFail("Expected coverage wall time before target to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .coverageWallTimePrecedesTargetSnapshot(
                    snapshot: baseWallTime + 4_000_000,
                    coverage: baseWallTime + 3_000_000
                )
            )
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)
        _ = try await machine.observePathUpdate(
            try cellularObservationA()
        )
    }

    func testCoveragePreparationFailureRollsBackEventSnapshotAndCoverage() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    coverageRecordID: "record:000-session-open-a"
                )
            )
            XCTFail("Expected duplicate coverage record ID to fail")
        } catch let error as LedgerRecordChainError {
            XCTAssertEqual(
                error,
                .duplicateRecordID(
                    identifier("record:000-session-open-a")
                )
            )
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)

        let accepted = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        XCTAssertEqual(accepted.eventRecord.digestSubject.sequenceIndex, 3)
        XCTAssertEqual(accepted.snapshotRecord.digestSubject.sequenceIndex, 4)
        XCTAssertEqual(accepted.coverageRecord?.digestSubject.sequenceIndex, 5)
        XCTAssertEqual(accepted.transitionRecord?.digestSubject.sequenceIndex, 6)
    }

    func testInterruptedCoverageIsRequiredBeforeFirstFreshTargetCommits() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        try await closeSessionA(on: machine)
        try await openSessionB(on: machine)
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationB(includeCoverage: false)
            )
            XCTFail("Expected missing interrupted coverage to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .coverageMaterializationRequired(.interrupted)
            )
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationB()
        )
        XCTAssertEqual(accepted.coverageRelation?.status, .interrupted)
        XCTAssertNotNil(accepted.coverageRecord)
    }

    func testDirectDisconnectMaterializesInterruptedCoverageFromTerminalBoundary() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let source = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let terminal = try await disconnectSessionA(on: machine)
        let opening = try await openSessionB(on: machine)
        let target = try await machine.observePathUpdate(
            try wifiObservationB()
        )

        guard case let .interrupted(
            relationSource,
            relationTarget,
            gap
        ) = target.coverageRelation else {
            return XCTFail("Expected interrupted coverage relation")
        }

        XCTAssertEqual(relationSource, source.observedSnapshot.coverageEndpoint)
        XCTAssertEqual(relationTarget, target.observedSnapshot.coverageEndpoint)
        XCTAssertEqual(gap.gapStartBoundary, terminal.reference)
        XCTAssertEqual(gap.gapEndBoundary, opening.record.reference)
        XCTAssertEqual(
            target.coverageRecord?.recordSHA256.rawValue,
            "81debed71b54c2aa31769d07753c0071d26b1903e83e2b5c692365af9be738ab"
        )
        XCTAssertEqual(target.coverageRecord?.digestSubject.sequenceIndex, 7)
        XCTAssertNil(target.transitionRecord)
        XCTAssertNil(target.transitionRelation)
    }

    func testReopenWithoutObservedSourceCannotFabricateInterruptedCoverage() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await closeSessionA(on: machine)
        try await openSessionB(on: machine)
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationB()
            )
            XCTFail("Expected coverage without a retained source to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .coverageMaterializationNotPermitted)
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationB(includeCoverage: false)
        )
        XCTAssertEqual(accepted.observedSnapshot.snapshotRole, .sourceEndpoint)
        XCTAssertNil(accepted.coverageRecord)
        XCTAssertNil(accepted.coverageRelation)
        XCTAssertNil(accepted.transitionRecord)
        XCTAssertNil(accepted.transitionRelation)
    }

    func testTransitionInputBeforeChangedRelationIsRejectedAtomically() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        let before = try await machine.snapshot()
        let transition = NetworkTransitionMaterializationInput(
            transitionID: identifier("transition:not-permitted"),
            recordID: identifier("record:003-transition-not-permitted"),
            recordedWallTimeUnixNS: baseWallTime + 3_000_000,
            eventBoundMonotonicTimeNS: 4_000
        )

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationA(
                    transitionMaterialization: transition
                )
            )
            XCTFail("Expected transition before a changed relation to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .transitionMaterializationNotPermitted)
        }

        let afterRejectedTransition = try await machine.snapshot()
        XCTAssertEqual(afterRejectedTransition, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        XCTAssertNil(accepted.transitionRecord)
        XCTAssertEqual(accepted.eventRecord.digestSubject.sequenceIndex, 1)
    }

    func testChangedContinuousRelationRequiresTransitionBeforeCommit() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(includeTransition: false)
            )
            XCTFail("Expected missing event-bound transition to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .transitionMaterializationRequired(.eventBound)
            )
        }

        let afterMissingTransition = try await machine.snapshot()
        XCTAssertEqual(afterMissingTransition, before)

        let accepted = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        XCTAssertEqual(
            accepted.transitionRecord?.digestSubject.sequenceIndex,
            6
        )
        XCTAssertEqual(
            accepted.transitionRelation?.transitionClass,
            .eventBound
        )
    }

    func testEqualStateRelationForbidsTransitionInput() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        let coverage = NetworkCoverageMaterializationInput(
            intervalID: identifier("coverage:equal"),
            recordID: identifier("record:005-coverage-equal"),
            recordedWallTimeUnixNS: baseWallTime + 5_000_000
        )
        let transition = NetworkTransitionMaterializationInput(
            transitionID: identifier("transition:forbidden-equal"),
            recordID: identifier("record:006-transition-forbidden-equal"),
            recordedWallTimeUnixNS: baseWallTime + 6_000_000,
            eventBoundMonotonicTimeNS: 6_000
        )

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationA(
                    eventRecordID: "record:003-path-equal",
                    snapshotRecordID: "record:004-snapshot-equal",
                    eventID: "event:path-equal",
                    snapshotID: "snapshot:equal",
                    eventWallTimeOffset: 3_000_000,
                    snapshotWallTimeOffset: 4_000_000,
                    eventMonotonicTimeNS: 4_000,
                    snapshotMonotonicTimeNS: 5_000,
                    coverageMaterialization: coverage,
                    transitionMaterialization: transition
                )
            )
            XCTFail("Expected equal-state transition input to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .transitionMaterializationNotPermitted)
        }

        let afterForbiddenEqualTransition = try await machine.snapshot()
        XCTAssertEqual(afterForbiddenEqualTransition, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationA(
                eventRecordID: "record:003-path-equal",
                snapshotRecordID: "record:004-snapshot-equal",
                eventID: "event:path-equal",
                snapshotID: "snapshot:equal",
                eventWallTimeOffset: 3_000_000,
                snapshotWallTimeOffset: 4_000_000,
                eventMonotonicTimeNS: 4_000,
                snapshotMonotonicTimeNS: 5_000,
                coverageMaterialization: coverage
            )
        )
        XCTAssertEqual(accepted.changedFieldsFromPreviousSnapshot, [])
        XCTAssertNotNil(accepted.coverageRecord)
        XCTAssertNil(accepted.transitionRecord)
    }

    func testEventBoundTransitionTimeShapeIsFailClosed() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    transitionWallTimeOffset: 4_000_000
                )
            )
            XCTFail("Expected transition wall time before coverage to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .transitionWallTimePrecedesCoverage(
                    coverage: baseWallTime + 5_000_000,
                    transition: baseWallTime + 4_000_000
                )
            )
        }
        let afterEarlyWallTime = try await machine.snapshot()
        XCTAssertEqual(afterEarlyWallTime, before)

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    transitionMonotonicTimeNS: nil
                )
            )
            XCTFail("Expected missing event-bound monotonic time to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .eventBoundTransitionMonotonicTimeRequired
            )
        }
        let afterMissingMonotonic = try await machine.snapshot()
        XCTAssertEqual(afterMissingMonotonic, before)

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    transitionMonotonicTimeNS: 5_000
                )
            )
            XCTFail("Expected non-increasing transition monotonic time to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .eventBoundTransitionMonotonicTimeNotAfterSnapshot(
                    snapshot: 5_000,
                    transition: 5_000
                )
            )
        }
        let afterNonIncreasingMonotonic = try await machine.snapshot()
        XCTAssertEqual(afterNonIncreasingMonotonic, before)

        _ = try await machine.observePathUpdate(
            try cellularObservationA()
        )
    }

    func testChangedInterruptedRelationRequiresLedgerWideTransitionBeforeCommit() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        try await machine.observePathUpdate(
            try cellularObservationA()
        )
        _ = try await closeSessionA(
            on: machine,
            recordID: "record:007-session-close-a",
            wallTimeOffset: 7_000_000,
            monotonicTimeNS: 7_000
        )
        _ = try await openSessionB(
            on: machine,
            recordID: "record:008-session-open-b",
            wallTimeOffset: 8_000_000
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationB(
                    eventRecordID: "record:009-path-wifi-b",
                    snapshotRecordID: "record:010-snapshot-wifi-b",
                    eventWallTimeOffset: 9_000_000,
                    snapshotWallTimeOffset: 10_000_000,
                    coverageRecordID: "record:011-coverage-interrupted",
                    coverageWallTimeOffset: 11_000_000,
                    includeTransition: false
                )
            )
            XCTFail("Expected missing endpoint-difference transition to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .transitionMaterializationRequired(.endpointDifferenceOnly)
            )
        }
        let afterMissingTransition = try await machine.snapshot()
        XCTAssertEqual(afterMissingTransition, before)

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationB(
                    eventRecordID: "record:009-path-wifi-b",
                    snapshotRecordID: "record:010-snapshot-wifi-b",
                    eventWallTimeOffset: 9_000_000,
                    snapshotWallTimeOffset: 10_000_000,
                    coverageRecordID: "record:011-coverage-interrupted",
                    coverageWallTimeOffset: 11_000_000,
                    includeTransition: true,
                    transitionRecordID:
                        "record:012-transition-endpoint-difference",
                    transitionWallTimeOffset: 12_000_000,
                    transitionMonotonicTimeNS: 4_000
                )
            )
            XCTFail("Expected ledger-wide transition monotonic time to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(
                error,
                .endpointDifferenceTransitionMonotonicTimeForbidden
            )
        }
        let afterForbiddenMonotonic = try await machine.snapshot()
        XCTAssertEqual(afterForbiddenMonotonic, before)

        let accepted = try await machine.observePathUpdate(
            try wifiObservationB(
                eventRecordID: "record:009-path-wifi-b",
                snapshotRecordID: "record:010-snapshot-wifi-b",
                eventWallTimeOffset: 9_000_000,
                snapshotWallTimeOffset: 10_000_000,
                coverageRecordID: "record:011-coverage-interrupted",
                coverageWallTimeOffset: 11_000_000,
                includeTransition: true,
                transitionRecordID:
                    "record:012-transition-endpoint-difference",
                transitionWallTimeOffset: 12_000_000
            )
        )
        XCTAssertEqual(
            accepted.transitionRelation?.transitionClass,
            .endpointDifferenceOnly
        )
        XCTAssertEqual(
            accepted.transitionRecord?.digestSubject.sequenceIndex,
            12
        )
    }

    func testTransitionPreparationFailureRollsBackEventSnapshotCoverageAndTransition() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.observePathUpdate(
                try cellularObservationA(
                    transitionRecordID: "record:000-session-open-a"
                )
            )
            XCTFail("Expected duplicate transition record ID to fail")
        } catch let error as LedgerRecordChainError {
            XCTAssertEqual(
                error,
                .duplicateRecordID(
                    identifier("record:000-session-open-a")
                )
            )
        }

        let afterFailedTransitionPreparation = try await machine.snapshot()
        XCTAssertEqual(afterFailedTransitionPreparation, before)

        let accepted = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        XCTAssertEqual(accepted.eventRecord.digestSubject.sequenceIndex, 3)
        XCTAssertEqual(accepted.snapshotRecord.digestSubject.sequenceIndex, 4)
        XCTAssertEqual(accepted.coverageRecord?.digestSubject.sequenceIndex, 5)
        XCTAssertEqual(accepted.transitionRecord?.digestSubject.sequenceIndex, 6)
    }

    func testCompleteReferencePathMatchesBothTransitionClassesExactly() async throws {
        let machine = makeMachine()
        let openA = try await openSessionA(on: machine)
        let wifiA = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let cellularA = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        let closeA = try await closeSessionA(
            on: machine,
            recordID: "record:007-session-close-a",
            wallTimeOffset: 7_000_000,
            monotonicTimeNS: 7_000
        )
        let openB = try await openSessionB(
            on: machine,
            recordID: "record:008-session-open-b",
            wallTimeOffset: 8_000_000
        )
        let wifiB = try await machine.observePathUpdate(
            try wifiObservationB(
                eventRecordID: "record:009-path-wifi-b",
                snapshotRecordID: "record:010-snapshot-wifi-b",
                eventWallTimeOffset: 9_000_000,
                snapshotWallTimeOffset: 10_000_000,
                coverageRecordID: "record:011-coverage-interrupted",
                coverageIntervalID: "coverage:interrupted-a-to-b",
                coverageWallTimeOffset: 11_000_000,
                includeTransition: true,
                transitionRecordID:
                    "record:012-transition-endpoint-difference",
                transitionID:
                    "transition:endpoint-difference-cellular-to-wifi",
                transitionWallTimeOffset: 12_000_000
            )
        )

        XCTAssertEqual(
            openA.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(
            wifiA.eventRecord.recordSHA256.rawValue,
            "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980"
        )
        XCTAssertEqual(
            cellularA.transitionRecord?.recordSHA256.rawValue,
            "57396fbb180ed7eb6fd3b99f17fe86709616684ad16445b9559f879e20f8c594"
        )
        XCTAssertEqual(
            closeA.recordSHA256.rawValue,
            "c8a19d0980a17921747507be3ca901dea23e716cffb03b595f93d6ffa98c652d"
        )
        XCTAssertEqual(
            openB.record.recordSHA256.rawValue,
            "e2124b6cecf0549f19e2e804ffaf05c64a745b354828344c178793e8c324841b"
        )
        XCTAssertEqual(
            wifiB.eventRecord.recordSHA256.rawValue,
            "a8ddd09176678809732c26edfd58acae5681e4e4f0b0e3c2fff78fccf814fbc0"
        )
        XCTAssertEqual(
            wifiB.snapshotRecord.recordSHA256.rawValue,
            "6e6af21f6590c2ac508d0119a8c32477d87e9a3fd2a2df6b4f6909eac7b788fd"
        )
        XCTAssertEqual(
            wifiB.coverageRecord?.recordSHA256.rawValue,
            "220fcd76f0ad3f6f9aa6483968ee7fd7639fb54115215722571393f181fc1bcd"
        )
        XCTAssertEqual(
            wifiB.transitionRecord?.recordSHA256.rawValue,
            "de8aab56372ca0ec3bfff26bce199e0d5e700aee026916ae3ebb19714952de35"
        )
        XCTAssertEqual(
            wifiB.transitionRelation?.transitionClass,
            .endpointDifferenceOnly
        )
        XCTAssertEqual(
            wifiB.transitionRelation?.changedFields,
            [.isExpensive, .usedInterfaceTypes]
        )
        XCTAssertNil(wifiB.transitionRelation?.eventReference)
        XCTAssertNil(wifiB.changedFieldsFromPreviousSnapshot)

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.recordCount, 13)
        XCTAssertEqual(
            snapshot.chain.records.map(\.digestSubject.recordType),
            [
                .sessionBoundary,
                .observationEvent,
                .stateSnapshot,
                .observationEvent,
                .stateSnapshot,
                .coverageInterval,
                .transition,
                .sessionBoundary,
                .sessionBoundary,
                .observationEvent,
                .stateSnapshot,
                .coverageInterval,
                .transition,
            ]
        )
    }

    func testDirectDisconnectChangedRelationMaterializesEndpointDifferenceTransition() async throws {
        let machine = makeMachine()
        try await openSessionA(on: machine)
        try await machine.observePathUpdate(
            try wifiObservationA()
        )
        let source = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        let terminal = try await disconnectSessionA(
            on: machine,
            recordID: "record:007-session-terminate-a",
            wallTimeOffset: 7_000_000,
            monotonicTimeNS: 7_000
        )
        let opening = try await openSessionB(
            on: machine,
            recordID: "record:008-session-open-b",
            wallTimeOffset: 8_000_000
        )
        let target = try await machine.observePathUpdate(
            try wifiObservationB(
                eventRecordID: "record:009-path-wifi-b",
                snapshotRecordID: "record:010-snapshot-wifi-b",
                eventWallTimeOffset: 9_000_000,
                snapshotWallTimeOffset: 10_000_000,
                coverageRecordID: "record:011-coverage-interrupted",
                coverageWallTimeOffset: 11_000_000,
                includeTransition: true,
                transitionRecordID:
                    "record:012-transition-endpoint-difference",
                transitionWallTimeOffset: 12_000_000
            )
        )

        guard case let .interrupted(_, _, gap) = target.coverageRelation else {
            return XCTFail("Expected interrupted relation")
        }
        XCTAssertEqual(gap.gapStartBoundary, terminal.reference)
        XCTAssertEqual(gap.gapEndBoundary, opening.record.reference)
        XCTAssertEqual(
            target.transitionRelation?.source,
            source.observedSnapshot.transitionEndpoint
        )
        XCTAssertEqual(
            target.transitionRelation?.transitionClass,
            .endpointDifferenceOnly
        )
        XCTAssertNotNil(target.transitionRecord)
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

    func testCompleteReferencePathClosesExactCheckpointAndLedgerDocument() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(on: machine)
        _ = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        _ = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        _ = try await closeSessionA(
            on: machine,
            recordID: "record:007-session-close-a",
            wallTimeOffset: 7_000_000,
            monotonicTimeNS: 7_000
        )
        _ = try await openSessionB(
            on: machine,
            recordID: "record:008-session-open-b",
            wallTimeOffset: 8_000_000
        )
        _ = try await machine.observePathUpdate(
            try wifiObservationB(
                eventRecordID: "record:009-path-wifi-b",
                snapshotRecordID: "record:010-snapshot-wifi-b",
                eventWallTimeOffset: 9_000_000,
                snapshotWallTimeOffset: 10_000_000,
                coverageRecordID: "record:011-coverage-interrupted",
                coverageIntervalID: "coverage:interrupted-a-to-b",
                coverageWallTimeOffset: 11_000_000,
                includeTransition: true,
                transitionRecordID:
                    "record:012-transition-endpoint-difference",
                transitionID:
                    "transition:endpoint-difference-cellular-to-wifi",
                transitionWallTimeOffset: 12_000_000
            )
        )

        let closure = try await machine.closeLedger(
            LedgerCheckpointMaterializationInput(
                checkpointID: identifier(
                    "checkpoint:synthetic-reference-v0"
                ),
                recordID: identifier("record:013-checkpoint"),
                recordedWallTimeUnixNS: baseWallTime + 13_000_000
            ),
            observerIdentity: fixtureObserverIdentity()
        )

        XCTAssertEqual(closure.checkpointSource.closedRecordCount, 13)
        XCTAssertEqual(closure.checkpointSource.sessionCount, 2)
        XCTAssertEqual(closure.checkpointSource.clockEpochCount, 2)
        XCTAssertEqual(
            closure.checkpointSource.recordTypeCounts,
            LedgerCheckpointRecordTypeCounts(
                coverageInterval: 2,
                observationEvent: 3,
                sessionBoundary: 3,
                stateSnapshot: 3,
                transition: 2
            )
        )
        XCTAssertEqual(
            closure.checkpointSource.coverageSummary,
            LedgerCheckpointCoverageSummary(
                continuousIntervals: 1,
                interruptedIntervals: 1
            )
        )
        XCTAssertEqual(
            closure.checkpointSource.transitionSummary,
            LedgerCheckpointTransitionSummary(
                endpointDifferenceOnly: 1,
                eventBound: 1
            )
        )

        let checkpointPayloadBytes = closure.checkpointPayload.canonicalBytes()
        XCTAssertEqual(checkpointPayloadBytes.count, 1_307)
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: checkpointPayloadBytes
            ).rawValue,
            "2dd55e7af9716efbdd72345e881ad10dfeae74dbcb64f37245c8a7e9c56366c7"
        )
        XCTAssertEqual(
            closure.checkpointRecord.digestSubject.canonicalBytes().count,
            2_386
        )
        XCTAssertEqual(
            closure.checkpointRecord.recordSHA256.rawValue,
            "16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff"
        )
        XCTAssertEqual(
            closure.checkpointRecord.canonicalBytes().count,
            2_469
        )
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: closure.checkpointRecord.canonicalBytes()
            ).rawValue,
            "1a71f5235f754f769bb00d6e1c24621caeacfd8994a4693a12b37000e152d862"
        )

        let ledgerBytes = closure.document.canonicalBytes()
        XCTAssertEqual(ledgerBytes.count, 31_904)
        XCTAssertEqual(
            closure.document.ledgerSHA256.rawValue,
            "360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77"
        )
        XCTAssertNotEqual(ledgerBytes.last, 0x0A)
        XCTAssertEqual(closure.document.records.count, 14)
        XCTAssertEqual(
            closure.document.records.last,
            closure.checkpointRecord
        )

        let snapshot = try await machine.snapshot()
        XCTAssertEqual(snapshot.chain.state, .checkpointed)
        XCTAssertEqual(snapshot.chain.recordCount, 14)
        XCTAssertNil(snapshot.chain.nextSequenceIndex)
        XCTAssertEqual(snapshot.ledgerClosure, closure)
    }

    func testPostClosureMutationAndRepeatedClosureAreRejectedWithoutChange() async throws {
        let machine = makeMachine()
        _ = try await openSessionA(on: machine)
        let input = LedgerCheckpointMaterializationInput(
            checkpointID: identifier("checkpoint:minimal-runtime-v0"),
            recordID: identifier("record:001-checkpoint"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000
        )
        let closure = try await machine.closeLedger(
            input,
            observerIdentity: fixtureObserverIdentity()
        )
        let before = try await machine.snapshot()

        do {
            _ = try await machine.closeLedger(
                input,
                observerIdentity: fixtureObserverIdentity()
            )
            XCTFail("Expected repeated closure to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .ledgerAlreadyClosed)
        }

        do {
            _ = try await machine.sceneWillResignActive(
                boundaryID: identifier("boundary:late-close-a"),
                recordID: identifier("record:late-close-a"),
                sessionID: identifier("session:synthetic-a"),
                recordedWallTimeUnixNS: baseWallTime + 2_000_000,
                monotonicTimeNS: 2_000
            )
            XCTFail("Expected post-closure lifecycle mutation to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .ledgerAlreadyClosed)
        }

        do {
            _ = try await machine.observePathUpdate(
                try wifiObservationA(
                    eventRecordID: "record:late-event",
                    snapshotRecordID: "record:late-snapshot"
                )
            )
            XCTFail("Expected post-closure observation to fail")
        } catch let error as NetworkObservationStateMachineError {
            XCTAssertEqual(error, .ledgerAlreadyClosed)
        }

        let after = try await machine.snapshot()
        XCTAssertEqual(after, before)
        XCTAssertEqual(after.ledgerClosure, closure)
        XCTAssertEqual(after.chain.recordCount, 2)
    }
}
