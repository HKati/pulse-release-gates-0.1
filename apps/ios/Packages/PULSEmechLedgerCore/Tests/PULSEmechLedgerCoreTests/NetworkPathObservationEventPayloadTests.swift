import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NetworkPathObservationEventPayloadTests: XCTestCase {
    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
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

    private func wifiPayload() throws -> NetworkPathObservationEventPayload {
        NetworkPathObservationEventPayload(
            eventID: identifier("event:path-wifi-a"),
            targetProjection: try wifiState()
        )
    }

    func testFixedMetadataMatchesObservationContract() {
        XCTAssertEqual(
            NetworkPathObservationEventPayload.eventRole,
            "surface_observation"
        )
        XCTAssertEqual(
            NetworkPathObservationEventPayload.eventType,
            "path_update_received"
        )
        XCTAssertEqual(
            NetworkPathObservationEventPayload.initiatingCauseClaim,
            "none"
        )
        XCTAssertEqual(
            NetworkPathObservationEventPayload.sourceInterface,
            "Network.framework NWPathMonitor.pathUpdateHandler"
        )
        XCTAssertEqual(
            NetworkPathObservationEventPayload.surfaceID,
            "network_path"
        )
    }

    func testWiFiPayloadMatchesExactReferenceBytes() throws {
        let payload = try wifiPayload()
        let expected =
            #"{"accepted_while_window_open":true,"event_id":"event:path-wifi-a","event_role":"surface_observation","event_type":"path_update_received","initiating_cause_claim":"none","payload_type":"observation_event","platform_event_time_unix_ns":null,"source_interface":"Network.framework NWPathMonitor.pathUpdateHandler","surface_id":"network_path","target_projection":{"available_interface_types":["wifi","cellular"],"is_constrained":false,"is_expensive":false,"status":"satisfied","supports_dns":true,"supports_ipv4":true,"supports_ipv6":true,"used_interface_types":["wifi"]}}"#
        let bytes = payload.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            567
        )
        XCTAssertEqual(
            payload.eventID.rawValue,
            "event:path-wifi-a"
        )
        XCTAssertEqual(
            payload.targetProjection,
            try wifiState()
        )
    }

    func testCellularPayloadMatchesExactReferenceBytes() throws {
        let payload = NetworkPathObservationEventPayload(
            eventID: identifier("event:path-cellular-a"),
            targetProjection: try cellularState()
        )
        let expected =
            #"{"accepted_while_window_open":true,"event_id":"event:path-cellular-a","event_role":"surface_observation","event_type":"path_update_received","initiating_cause_claim":"none","payload_type":"observation_event","platform_event_time_unix_ns":null,"source_interface":"Network.framework NWPathMonitor.pathUpdateHandler","surface_id":"network_path","target_projection":{"available_interface_types":["wifi","cellular"],"is_constrained":false,"is_expensive":true,"status":"satisfied","supports_dns":true,"supports_ipv4":true,"supports_ipv6":true,"used_interface_types":["cellular"]}}"#
        let bytes = payload.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            574
        )
    }

    func testCanonicalPayloadHasClosedTenFieldShape() throws {
        let payload = try wifiPayload()

        guard case let .object(object) = payload.canonicalValue() else {
            return XCTFail("Expected canonical object payload")
        }

        XCTAssertEqual(
            object.members.map(\.key.value),
            [
                "accepted_while_window_open",
                "event_id",
                "event_role",
                "event_type",
                "initiating_cause_claim",
                "payload_type",
                "platform_event_time_unix_ns",
                "source_interface",
                "surface_id",
                "target_projection",
            ]
        )
        XCTAssertEqual(
            object.members.count,
            10
        )
    }

    func testRecordDraftIsSessionScopedObservationEvent() throws {
        let payload = try wifiPayload()
        let draft = payload.recordDraft(
            recordID: identifier("record:001-path-wifi-a"),
            recordedWallTimeUnixNS: 1_700_000_000_001_000_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 2_000
        )

        XCTAssertEqual(
            draft.recordID.rawValue,
            "record:001-path-wifi-a"
        )
        XCTAssertEqual(
            draft.recordType,
            .observationEvent
        )
        XCTAssertEqual(
            draft.recordedWallTimeUnixNS,
            1_700_000_000_001_000_000
        )
        XCTAssertEqual(
            draft.payload,
            payload.canonicalValue()
        )

        guard case let .session(
            sessionID,
            clockEpochID,
            monotonicTimeNS
        ) = draft.scope else {
            return XCTFail("Expected session-scoped observation event")
        }

        XCTAssertEqual(
            sessionID.rawValue,
            "session:synthetic-a"
        )
        XCTAssertEqual(
            clockEpochID.rawValue,
            "clock-epoch:synthetic-a"
        )
        XCTAssertEqual(
            monotonicTimeNS,
            2_000
        )
    }

    func testTypedWiFiEventMatchesSecondPythonReferenceRecord() async throws {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: .syntheticReference
        )
        let openPayload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )
        let openDraft = try openPayload.recordDraft(
            recordID: identifier("record:000-session-open-a"),
            recordedWallTimeUnixNS: 1_700_000_000_000_000_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 1_000
        )
        let openRecord = try await chain.append(openDraft)

        let eventDraft = try wifiPayload().recordDraft(
            recordID: identifier("record:001-path-wifi-a"),
            recordedWallTimeUnixNS: 1_700_000_000_001_000_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 2_000
        )
        let eventRecord = try await chain.append(eventDraft)
        let snapshot = await chain.snapshot()

        XCTAssertEqual(
            openRecord.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(
            eventRecord.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            eventRecord.digestSubject.previousRecordSHA256,
            openRecord.recordSHA256
        )
        XCTAssertEqual(
            eventRecord.recordSHA256.rawValue,
            "297a4c383f4d94d7459cb1548e42994d6166be89d25d366217241c48c68d1980"
        )
        XCTAssertEqual(
            eventRecord.digestSubject.canonicalBytes().count,
            1_691
        )
        XCTAssertEqual(
            eventRecord.canonicalBytes().count,
            1_774
        )
        XCTAssertEqual(
            snapshot.recordCount,
            2
        )
        XCTAssertEqual(
            snapshot.latestRecordReference,
            eventRecord.reference
        )
    }

    func testCanonicalOutputHasNoAddedBoundaryBytes() throws {
        let bytes = Array(
            try wifiPayload().canonicalBytes()
        )

        XCTAssertFalse(
            bytes.starts(with: [0xEF, 0xBB, 0xBF])
        )
        XCTAssertEqual(
            bytes.first,
            0x7B
        )
        XCTAssertEqual(
            bytes.last,
            0x7D
        )
        XCTAssertFalse(
            bytes.contains(0x0D)
        )
        XCTAssertFalse(
            bytes.contains(0x0A)
        )
    }

    func testRepeatedSerializationIsByteIdentical() throws {
        let payload = try wifiPayload()
        let expected = payload.canonicalBytes()

        for _ in 0..<100 {
            XCTAssertEqual(
                payload.canonicalBytes(),
                expected
            )
        }
    }
}
