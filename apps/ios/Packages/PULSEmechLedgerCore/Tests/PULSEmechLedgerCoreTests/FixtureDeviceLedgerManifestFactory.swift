import Foundation
@testable import PULSEmechLedgerCore

enum FixtureDeviceLedgerManifestFactoryError:
    Error,
    Sendable,
    Equatable
{
    case expectedRecordedLifecycleResult
    case repositoryRootUnavailable
}

enum FixtureDeviceLedgerManifestFactory {
    static let baseWallTime: Int64 =
        1_700_000_000_000_000_000

    static let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    static func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    static func observerIdentity() throws
        -> DeviceLedgerObserverIdentity
    {
        try DeviceLedgerObserverIdentity(
            identityScope: .fixtureInstallation,
            keyOriginProfile: .fixtureSoftwareP256,
            publicKeyX963Uncompressed: Data(
                base64Encoded:
                    "BAIa75uP4gO+twVlypJYAjIKXK0JVnBPBArgoE50sEI+HbKkjFpxpQifk3hgoQs08yYzY850htpv1wl0/4u6i10="
            )!
        )
    }

    static func makeReferenceClosure() async throws
        -> DeviceTransitionLedgerClosure
    {
        let machine = makeMachine()

        _ = try await openSessionA(on: machine)
        _ = try await machine.observePathUpdate(
            try wifiObservationA()
        )
        _ = try await machine.observePathUpdate(
            try cellularObservationA()
        )
        _ = try await closeSessionA(on: machine)
        _ = try await openSessionB(on: machine)
        _ = try await machine.observePathUpdate(
            try wifiObservationB()
        )

        return try await machine.closeLedger(
            LedgerCheckpointMaterializationInput(
                checkpointID: identifier(
                    "checkpoint:synthetic-reference-v0"
                ),
                recordID: identifier("record:013-checkpoint"),
                recordedWallTimeUnixNS:
                    baseWallTime + 13_000_000
            ),
            observerIdentity: observerIdentity()
        )
    }

    static func makeReferenceCheckpointSignature(
        closure: DeviceTransitionLedgerClosure
    ) async throws -> DeviceCheckpointSignatureMaterialization {
        let subject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signer = FixtureCheckpointSigner(
            observerIdentity: try observerIdentity(),
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixtureCheckpointSigner.referenceCheckpointSignature()
        )

        return try await closure.materializeCheckpointSignature(
            using: signer
        )
    }

    static func contractMembers() throws
        -> DeviceLedgerManifestContractMembers
    {
        let root = try repositoryRoot()

        return try DeviceLedgerManifestContractMembers(
            canonicalizationProfileBytes: try Data(
                contentsOf: root.appendingPathComponent(
                    "contracts/pulsemech_device_canonical_json_v0.json"
                )
            ),
            observationContractBytes: try Data(
                contentsOf: root.appendingPathComponent(
                    "contracts/pulsemech_ios_observation_contract_v0.json"
                )
            ),
            manifestSchemaBytes: try Data(
                contentsOf: root.appendingPathComponent(
                    "schemas/pulsemech_device_ledger_manifest_v0.schema.json"
                )
            ),
            signatureSchemaBytes: try Data(
                contentsOf: root.appendingPathComponent(
                    "schemas/pulsemech_device_signature_v0.schema.json"
                )
            ),
            transitionLedgerSchemaBytes: try Data(
                contentsOf: root.appendingPathComponent(
                    "schemas/pulsemech_device_transition_ledger_v0.schema.json"
                )
            )
        )
    }

    static func referenceManifestBytes() throws -> Data {
        try Data(
            contentsOf: try repositoryRoot().appendingPathComponent(
                "examples/device_transition_ledger/pulsemech_device_ledger_manifest_reference_v0.json"
            )
        )
    }

    private static func repositoryRoot() throws -> URL {
        if let workspace =
            ProcessInfo.processInfo.environment["GITHUB_WORKSPACE"]
        {
            let candidate = URL(
                fileURLWithPath: workspace,
                isDirectory: true
            )
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(
                    "contracts/pulsemech_device_canonical_json_v0.json"
                ).path
            ) {
                return candidate
            }
        }

        var candidate = URL(
            fileURLWithPath: #filePath
        )
        for _ in 0..<7 {
            candidate.deleteLastPathComponent()
        }

        guard FileManager.default.fileExists(
            atPath: candidate.appendingPathComponent(
                "contracts/pulsemech_device_canonical_json_v0.json"
            ).path
        ) else {
            throw FixtureDeviceLedgerManifestFactoryError
                .repositoryRootUnavailable
        }

        return candidate
    }

    private static func makeMachine()
        -> NetworkObservationStateMachine
    {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256:
                observerFingerprint,
            recordStatus: .syntheticReference
        )
        return NetworkObservationStateMachine(
            chain: chain
        )
    }

    private static func wifiState() throws -> NetworkPathState {
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

    private static func cellularState() throws
        -> NetworkPathState
    {
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
    private static func openSessionA(
        on machine: NetworkObservationStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-a"),
            recordID: identifier("record:000-session-open-a"),
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            recordedWallTimeUnixNS: baseWallTime,
            monotonicTimeNS: 1_000
        )
        return try requireRecorded(result).record
    }

    @discardableResult
    private static func closeSessionA(
        on machine: NetworkObservationStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneWillResignActive(
            boundaryID: identifier("boundary:close-a"),
            recordID: identifier(
                "record:007-session-close-a"
            ),
            sessionID: identifier("session:synthetic-a"),
            recordedWallTimeUnixNS:
                baseWallTime + 7_000_000,
            monotonicTimeNS: 7_000
        )
        return try requireRecorded(result).record
    }

    @discardableResult
    private static func openSessionB(
        on machine: NetworkObservationStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-b"),
            recordID: identifier(
                "record:008-session-open-b"
            ),
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier(
                "clock-epoch:synthetic-b"
            ),
            recordedWallTimeUnixNS:
                baseWallTime + 8_000_000,
            monotonicTimeNS: 1_000
        )
        return try requireRecorded(result).record
    }

    private static func wifiObservationA() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-wifi-a"),
            eventRecordID: identifier(
                "record:001-path-wifi-a"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 1_000_000,
            eventMonotonicTimeNS: 2_000,
            snapshotID: identifier("snapshot:wifi-a"),
            snapshotRecordID: identifier(
                "record:002-snapshot-wifi-a"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 2_000_000,
            snapshotMonotonicTimeNS: 3_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState: try wifiState(),
            coverageMaterialization: nil,
            transitionMaterialization: nil
        )
    }

    private static func cellularObservationA() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-cellular-a"),
            eventRecordID: identifier(
                "record:003-path-cellular-a"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 3_000_000,
            eventMonotonicTimeNS: 4_000,
            snapshotID: identifier("snapshot:cellular-a"),
            snapshotRecordID: identifier(
                "record:004-snapshot-cellular-a"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 4_000_000,
            snapshotMonotonicTimeNS: 5_000,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState: try cellularState(),
            coverageMaterialization:
                NetworkCoverageMaterializationInput(
                    intervalID: identifier(
                        "coverage:continuous-a"
                    ),
                    recordID: identifier(
                        "record:005-coverage-continuous"
                    ),
                    recordedWallTimeUnixNS:
                        baseWallTime + 5_000_000
                ),
            transitionMaterialization:
                NetworkTransitionMaterializationInput(
                    transitionID: identifier(
                        "transition:event-bound-wifi-to-cellular"
                    ),
                    recordID: identifier(
                        "record:006-transition-event-bound"
                    ),
                    recordedWallTimeUnixNS:
                        baseWallTime + 6_000_000,
                    eventBoundMonotonicTimeNS: 6_000
                )
        )
    }

    private static func wifiObservationB() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier("event:path-wifi-b"),
            eventRecordID: identifier(
                "record:009-path-wifi-b"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 9_000_000,
            eventMonotonicTimeNS: 2_000,
            snapshotID: identifier("snapshot:wifi-b"),
            snapshotRecordID: identifier(
                "record:010-snapshot-wifi-b"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 10_000_000,
            snapshotMonotonicTimeNS: 3_000,
            sessionID: identifier("session:synthetic-b"),
            clockEpochID: identifier(
                "clock-epoch:synthetic-b"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState: try wifiState(),
            coverageMaterialization:
                NetworkCoverageMaterializationInput(
                    intervalID: identifier(
                        "coverage:interrupted-a-to-b"
                    ),
                    recordID: identifier(
                        "record:011-coverage-interrupted"
                    ),
                    recordedWallTimeUnixNS:
                        baseWallTime + 11_000_000
                ),
            transitionMaterialization:
                NetworkTransitionMaterializationInput(
                    transitionID: identifier(
                        "transition:endpoint-difference-cellular-to-wifi"
                    ),
                    recordID: identifier(
                        "record:012-transition-endpoint-difference"
                    ),
                    recordedWallTimeUnixNS:
                        baseWallTime + 12_000_000,
                    eventBoundMonotonicTimeNS: nil
                )
        )
    }

    private static func requireRecorded(
        _ result: SessionBoundaryLifecycleResult
    ) throws -> (
        record: LedgerRecordEnvelope,
        completedGap: SessionBoundaryObservationGap?
    ) {
        guard case let .recorded(
            record,
            completedGap
        ) = result else {
            throw FixtureDeviceLedgerManifestFactoryError
                .expectedRecordedLifecycleResult
        }
        return (record, completedGap)
    }
}
