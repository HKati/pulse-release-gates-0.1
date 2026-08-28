import Foundation
import PULSEmechLedgerCore

enum BoundedProofRunError: Error, Sendable, Equatable, LocalizedError {
    case expectedRecordedLifecycleResult
    case missingBundledResource(String)
    case resourceReadFailed(String)
    case referenceCarrierIdentityMismatch
    case referenceLedgerIdentityMismatch
    case referenceManifestIdentityMismatch
    case verifierReportNotCanonical
    case verifierReportRejected
    case verifierReportCheckSetMismatch
    case verifierReportCarrierBindingMismatch
    case verifierReportSignatureStatusMismatch
    case verifierReportImplementationBoundaryMismatch
    case verifierReportAuthorityBoundaryMismatch

    var errorDescription: String? {
        switch self {
        case .expectedRecordedLifecycleResult:
            "The deterministic lifecycle boundary was not recorded."
        case let .missingBundledResource(name):
            "Required bundled proof resource is missing: \(name)"
        case let .resourceReadFailed(name):
            "Required bundled proof resource could not be read: \(name)"
        case .referenceCarrierIdentityMismatch:
            "The generated carrier does not match the exact bounded reference identity."
        case .referenceLedgerIdentityMismatch:
            "The generated ledger does not match the exact bounded reference identity."
        case .referenceManifestIdentityMismatch:
            "The generated manifest does not match the exact bounded reference identity."
        case .verifierReportNotCanonical:
            "The bundled standalone-verifier report is not the required canonical stored form."
        case .verifierReportRejected:
            "The bundled standalone-verifier report does not record the successful bounded result."
        case .verifierReportCheckSetMismatch:
            "The bundled standalone-verifier report does not contain 49 passed checks."
        case .verifierReportCarrierBindingMismatch:
            "The standalone-verifier report is not bound to the exact generated carrier."
        case .verifierReportSignatureStatusMismatch:
            "The standalone-verifier report does not verify both required signatures."
        case .verifierReportImplementationBoundaryMismatch:
            "The standalone-verifier implementation-separation boundary is not preserved."
        case .verifierReportAuthorityBoundaryMismatch:
            "The verifier report does not preserve the non-authorizing claim boundary."
        }
    }
}

struct BoundedProofRunResult: Sendable, Equatable {
    let recordCount: Int64
    let sessionCount: Int64
    let clockEpochCount: Int64
    let sessionBoundaryCount: Int64
    let continuousCoverageCount: Int64
    let interruptedCoverageCount: Int64
    let eventBoundTransitionCount: Int64
    let endpointDifferenceOnlyTransitionCount: Int64

    let checkpointSHA256: String
    let ledgerSHA256: String
    let manifestSHA256: String
    let carrierSHA256: String
    let carrierSizeBytes: Int64

    let verifierResult: String
    let verifierCheckCount: Int
    let verifierCarrierSHA256: String
    let verifierCarrierBindingMatches: Bool
    let verifierImplementationRelation: String
    let producerCodeImportedByVerifier: Bool
    let checkpointSignatureStatus: String
    let packageSignatureStatus: String

    let observerIdentityScope: String
    let observerKeyOriginProfile: String
    let declaredUnavailabilityPresent: Bool
    let authorityEffect: String
    let externalValidationClaim: String

    let carrierFileName: String
    let carrierBytes: Data

    init(
        recordCount: Int64,
        sessionCount: Int64,
        clockEpochCount: Int64,
        sessionBoundaryCount: Int64,
        continuousCoverageCount: Int64,
        interruptedCoverageCount: Int64,
        eventBoundTransitionCount: Int64,
        endpointDifferenceOnlyTransitionCount: Int64,
        checkpointSHA256: String,
        ledgerSHA256: String,
        manifestSHA256: String,
        carrierSHA256: String,
        carrierSizeBytes: Int64,
        verifierResult: String,
        verifierCheckCount: Int,
        verifierCarrierSHA256: String,
        verifierCarrierBindingMatches: Bool,
        verifierImplementationRelation: String,
        producerCodeImportedByVerifier: Bool,
        checkpointSignatureStatus: String,
        packageSignatureStatus: String,
        observerIdentityScope: String,
        observerKeyOriginProfile: String,
        declaredUnavailabilityPresent: Bool,
        authorityEffect: String,
        externalValidationClaim: String,
        carrierFileName: String,
        carrierBytes: Data
    ) {
        self.recordCount = recordCount
        self.sessionCount = sessionCount
        self.clockEpochCount = clockEpochCount
        self.sessionBoundaryCount = sessionBoundaryCount
        self.continuousCoverageCount = continuousCoverageCount
        self.interruptedCoverageCount = interruptedCoverageCount
        self.eventBoundTransitionCount = eventBoundTransitionCount
        self.endpointDifferenceOnlyTransitionCount =
            endpointDifferenceOnlyTransitionCount
        self.checkpointSHA256 = checkpointSHA256
        self.ledgerSHA256 = ledgerSHA256
        self.manifestSHA256 = manifestSHA256
        self.carrierSHA256 = carrierSHA256
        self.carrierSizeBytes = carrierSizeBytes
        self.verifierResult = verifierResult
        self.verifierCheckCount = verifierCheckCount
        self.verifierCarrierSHA256 = verifierCarrierSHA256
        self.verifierCarrierBindingMatches = verifierCarrierBindingMatches
        self.verifierImplementationRelation = verifierImplementationRelation
        self.producerCodeImportedByVerifier = producerCodeImportedByVerifier
        self.checkpointSignatureStatus = checkpointSignatureStatus
        self.packageSignatureStatus = packageSignatureStatus
        self.observerIdentityScope = observerIdentityScope
        self.observerKeyOriginProfile = observerKeyOriginProfile
        self.declaredUnavailabilityPresent = declaredUnavailabilityPresent
        self.authorityEffect = authorityEffect
        self.externalValidationClaim = externalValidationClaim
        self.carrierFileName = carrierFileName
        self.carrierBytes = Data(carrierBytes)
    }
}

enum BoundedReferenceProofRunner {
    static let carrierFileName =
        "pulsemech_device_transition_ledger_reference_v0.pulseledger"

    static let expectedCheckpointSHA256 =
        "16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff"

    static let expectedLedgerSHA256 =
        "360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77"

    static let expectedManifestSHA256 =
        "47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1"

    static let expectedCarrierSHA256 =
        "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3"

    static let expectedCarrierSizeBytes: Int64 = 133_568

    private static let baseWallTime: Int64 =
        1_700_000_000_000_000_000

    private static let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    static func run() async throws -> BoundedProofRunResult {
        let observerIdentity = try makeObserverIdentity()
        let closure = try await makeReferenceClosure(
            observerIdentity: observerIdentity
        )

        let checkpointSignature =
            try await materializeCheckpointSignature(
                closure: closure,
                observerIdentity: observerIdentity
            )

        let manifest = try closure.materializePackageManifest(
            checkpointSignature: checkpointSignature,
            contractMembers: try makeContractMembers()
        )

        let packageSignature =
            try await materializePackageSignature(
                closure: closure,
                manifest: manifest,
                observerIdentity: observerIdentity
            )

        let carrier = try manifest.materializePulseledgerCarrier(
            packageSignature: packageSignature
        )

        guard closure.checkpointRecord.recordSHA256.rawValue ==
                expectedCheckpointSHA256,
              closure.document.ledgerSHA256.rawValue ==
                expectedLedgerSHA256 else {
            throw BoundedProofRunError
                .referenceLedgerIdentityMismatch
        }

        guard manifest.manifest.manifestSHA256.rawValue ==
                expectedManifestSHA256 else {
            throw BoundedProofRunError
                .referenceManifestIdentityMismatch
        }

        guard carrier.carrierSHA256.rawValue ==
                expectedCarrierSHA256,
              carrier.sizeBytes == expectedCarrierSizeBytes,
              carrier.memberCount == 10 else {
            throw BoundedProofRunError
                .referenceCarrierIdentityMismatch
        }

        let reportBytes = try ProofResourceLoader.data(
            named:
                "pulsemech_device_transition_ledger_reference_verification_v0.json"
        )
        let report = try decodeAndValidateVerifierReport(
            reportBytes,
            carrier: carrier
        )

        let checkpointSource = closure.checkpointSource

        return BoundedProofRunResult(
            recordCount: Int64(closure.document.records.count),
            sessionCount: checkpointSource.sessionCount,
            clockEpochCount: checkpointSource.clockEpochCount,
            sessionBoundaryCount:
                checkpointSource.recordTypeCounts.sessionBoundary,
            continuousCoverageCount:
                checkpointSource.coverageSummary.continuousIntervals,
            interruptedCoverageCount:
                checkpointSource.coverageSummary.interruptedIntervals,
            eventBoundTransitionCount:
                checkpointSource.transitionSummary.eventBound,
            endpointDifferenceOnlyTransitionCount:
                checkpointSource.transitionSummary
                    .endpointDifferenceOnly,
            checkpointSHA256:
                closure.checkpointRecord.recordSHA256.rawValue,
            ledgerSHA256:
                closure.document.ledgerSHA256.rawValue,
            manifestSHA256:
                manifest.manifest.manifestSHA256.rawValue,
            carrierSHA256:
                carrier.carrierSHA256.rawValue,
            carrierSizeBytes:
                carrier.sizeBytes,
            verifierResult:
                report.result,
            verifierCheckCount:
                report.checks.count,
            verifierCarrierSHA256:
                report.subject.carrierSHA256,
            verifierCarrierBindingMatches:
                report.subject.carrierSHA256 ==
                    carrier.carrierSHA256.rawValue,
            verifierImplementationRelation:
                report.reproductionContext
                    .verifierImplementationRelation,
            producerCodeImportedByVerifier:
                report.tool.producerCodeImported,
            checkpointSignatureStatus:
                report.signatureVerification
                    .checkpoint.signatureStatus,
            packageSignatureStatus:
                report.signatureVerification
                    .package.signatureStatus,
            observerIdentityScope:
                observerIdentity.identityScope.rawValue,
            observerKeyOriginProfile:
                observerIdentity.keyOriginProfile.rawValue,
            declaredUnavailabilityPresent:
                report.semanticSummary
                    .declaredUnavailabilityPresent,
            authorityEffect:
                report.authorityBoundary.authorityEffect,
            externalValidationClaim:
                report.claimBoundary.externalValidationClaim,
            carrierFileName:
                carrierFileName,
            carrierBytes:
                carrier.exactBytes
        )
    }

    private static func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private static func makeObserverIdentity() throws
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

    private static func makeReferenceClosure(
        observerIdentity: DeviceLedgerObserverIdentity
    ) async throws -> DeviceTransitionLedgerClosure {
        let chain = LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256:
                observerFingerprint,
            recordStatus: .syntheticReference
        )
        let machine = NetworkObservationStateMachine(
            chain: chain
        )

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
                recordID: identifier(
                    "record:013-checkpoint"
                ),
                recordedWallTimeUnixNS:
                    baseWallTime + 13_000_000
            ),
            observerIdentity: observerIdentity
        )
    }

    private static func materializeCheckpointSignature(
        closure: DeviceTransitionLedgerClosure,
        observerIdentity: DeviceLedgerObserverIdentity
    ) async throws -> DeviceCheckpointSignatureMaterialization {
        let subject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signer = BoundedReferenceCheckpointSigner(
            observerIdentity: observerIdentity,
            expectedDigest: subject.signatureInputSHA256
        )

        return try await closure.materializeCheckpointSignature(
            using: signer
        )
    }

    private static func materializePackageSignature(
        closure: DeviceTransitionLedgerClosure,
        manifest: DeviceLedgerManifestMaterialization,
        observerIdentity: DeviceLedgerObserverIdentity
    ) async throws -> DevicePackageSignatureMaterialization {
        let subject = DevicePackageSignatureSubject(
            ledgerID: manifest.manifest.ledgerID,
            observerPublicKeyFingerprintSHA256:
                manifest.manifest
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                manifest.manifest.manifestSHA256
        )
        let signer = BoundedReferencePackageSigner(
            observerIdentity: observerIdentity,
            expectedDigest: subject.signatureInputSHA256
        )

        return try await closure.materializePackageSignature(
            manifest: manifest,
            using: signer
        )
    }

    private static func makeContractMembers() throws
        -> DeviceLedgerManifestContractMembers
    {
        try DeviceLedgerManifestContractMembers(
            canonicalizationProfileBytes:
                try ProofResourceLoader.data(
                    named:
                        "pulsemech_device_canonical_json_v0.json"
                ),
            observationContractBytes:
                try ProofResourceLoader.data(
                    named:
                        "pulsemech_ios_observation_contract_v0.json"
                ),
            manifestSchemaBytes:
                try ProofResourceLoader.data(
                    named:
                        "pulsemech_device_ledger_manifest_v0.schema.json"
                ),
            signatureSchemaBytes:
                try ProofResourceLoader.data(
                    named:
                        "pulsemech_device_signature_v0.schema.json"
                ),
            transitionLedgerSchemaBytes:
                try ProofResourceLoader.data(
                    named:
                        "pulsemech_device_transition_ledger_v0.schema.json"
                )
        )
    }

    @discardableResult
    private static func openSessionA(
        on machine: NetworkObservationStateMachine
    ) async throws -> LedgerRecordEnvelope {
        let result = try await machine.sceneDidBecomeActive(
            boundaryID: identifier("boundary:open-a"),
            recordID: identifier(
                "record:000-session-open-a"
            ),
            sessionID: identifier(
                "session:synthetic-a"
            ),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            recordedWallTimeUnixNS:
                baseWallTime,
            monotonicTimeNS:
                1_000
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
            sessionID: identifier(
                "session:synthetic-a"
            ),
            recordedWallTimeUnixNS:
                baseWallTime + 7_000_000,
            monotonicTimeNS:
                7_000
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
            sessionID: identifier(
                "session:synthetic-b"
            ),
            clockEpochID: identifier(
                "clock-epoch:synthetic-b"
            ),
            recordedWallTimeUnixNS:
                baseWallTime + 8_000_000,
            monotonicTimeNS:
                1_000
        )
        return try requireRecorded(result).record
    }

    private static func wifiState() throws
        -> NetworkPathState
    {
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

    private static func wifiObservationA() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier(
                "event:path-wifi-a"
            ),
            eventRecordID: identifier(
                "record:001-path-wifi-a"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 1_000_000,
            eventMonotonicTimeNS:
                2_000,
            snapshotID: identifier(
                "snapshot:wifi-a"
            ),
            snapshotRecordID: identifier(
                "record:002-snapshot-wifi-a"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 2_000_000,
            snapshotMonotonicTimeNS:
                3_000,
            sessionID: identifier(
                "session:synthetic-a"
            ),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState:
                try wifiState(),
            coverageMaterialization:
                nil,
            transitionMaterialization:
                nil
        )
    }

    private static func cellularObservationA() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier(
                "event:path-cellular-a"
            ),
            eventRecordID: identifier(
                "record:003-path-cellular-a"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 3_000_000,
            eventMonotonicTimeNS:
                4_000,
            snapshotID: identifier(
                "snapshot:cellular-a"
            ),
            snapshotRecordID: identifier(
                "record:004-snapshot-cellular-a"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 4_000_000,
            snapshotMonotonicTimeNS:
                5_000,
            sessionID: identifier(
                "session:synthetic-a"
            ),
            clockEpochID: identifier(
                "clock-epoch:synthetic-a"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState:
                try cellularState(),
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
                    eventBoundMonotonicTimeNS:
                        6_000
                )
        )
    }

    private static func wifiObservationB() throws
        -> NetworkPathUpdateObservation
    {
        NetworkPathUpdateObservation(
            eventID: identifier(
                "event:path-wifi-b"
            ),
            eventRecordID: identifier(
                "record:009-path-wifi-b"
            ),
            eventRecordedWallTimeUnixNS:
                baseWallTime + 9_000_000,
            eventMonotonicTimeNS:
                2_000,
            snapshotID: identifier(
                "snapshot:wifi-b"
            ),
            snapshotRecordID: identifier(
                "record:010-snapshot-wifi-b"
            ),
            snapshotRecordedWallTimeUnixNS:
                baseWallTime + 10_000_000,
            snapshotMonotonicTimeNS:
                3_000,
            sessionID: identifier(
                "session:synthetic-b"
            ),
            clockEpochID: identifier(
                "clock-epoch:synthetic-b"
            ),
            appLifecycleActivationState:
                .foregroundActive,
            networkPathState:
                try wifiState(),
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
                    eventBoundMonotonicTimeNS:
                        nil
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
            throw BoundedProofRunError
                .expectedRecordedLifecycleResult
        }
        return (record, completedGap)
    }

    private static func decodeAndValidateVerifierReport(
        _ exactBytes: Data,
        carrier: DevicePulseledgerCarrier
    ) throws -> BundledVerifierReport {
        guard exactBytes.first == 0x7B,
              exactBytes.last == 0x7D,
              !exactBytes.starts(with: [0xEF, 0xBB, 0xBF]),
              !exactBytes.contains(0x0A),
              !exactBytes.contains(0x0D) else {
            throw BoundedProofRunError
                .verifierReportNotCanonical
        }

        let report: BundledVerifierReport
        do {
            report = try JSONDecoder().decode(
                BundledVerifierReport.self,
                from: exactBytes
            )
        } catch {
            throw BoundedProofRunError
                .verifierReportNotCanonical
        }

        guard report.ok,
              report.result ==
                "verified_with_declared_unavailability",
              report.errors.isEmpty,
              report.failedCheckIDs.isEmpty,
              report.failureStage == nil else {
            throw BoundedProofRunError
                .verifierReportRejected
        }

        guard report.checks.count == 49,
              report.checks.values.allSatisfy({
                  $0 == "passed"
              }) else {
            throw BoundedProofRunError
                .verifierReportCheckSetMismatch
        }

        guard report.subject.carrierFileName ==
                carrierFileName,
              report.subject.carrierSHA256 ==
                carrier.carrierSHA256.rawValue,
              report.subject.carrierSizeBytes ==
                carrier.sizeBytes else {
            throw BoundedProofRunError
                .verifierReportCarrierBindingMismatch
        }

        guard report.signatureVerification
                .checkpoint.signatureStatus ==
                "verified",
              report.signatureVerification
                .package.signatureStatus ==
                "verified" else {
            throw BoundedProofRunError
                .verifierReportSignatureStatusMismatch
        }

        guard report.tool.producerCodeImported == false,
              report.reproductionContext
                .verifierImplementationRelation ==
                "separate_from_producer_code" else {
            throw BoundedProofRunError
                .verifierReportImplementationBoundaryMismatch
        }

        guard report.authorityBoundary.authorityEffect ==
                "none",
              report.authorityBoundary
                .changesReleaseAuthority == false,
              report.authorityBoundary
                .createsDeviceControlAuthority == false,
              report.authorityBoundary
                .createsReleaseDecision == false,
              report.authorityBoundary
                .verifierReportIsReleaseAuthority == false,
              report.claimBoundary
                .externalValidationClaim == "none" else {
            throw BoundedProofRunError
                .verifierReportAuthorityBoundaryMismatch
        }

        return report
    }
}

private struct BoundedReferenceCheckpointSigner:
    DeviceCheckpointSigner
{
    let observerIdentity: DeviceLedgerObserverIdentity
    let expectedDigest: Data

    init(
        observerIdentity: DeviceLedgerObserverIdentity,
        expectedDigest: Data
    ) {
        self.observerIdentity = observerIdentity
        self.expectedDigest = Data(expectedDigest)
    }

    func signCheckpointDigest(
        _ digest: Data
    ) async throws -> Data {
        guard digest == expectedDigest else {
            throw BoundedReferenceSignerError
                .unexpectedDigest
        }

        return Data(
            base64Encoded:
                "BOBikuqSCnXUQnqSzGnB6EmJhvM0Bm7BGg0uX0EeSAMJyAaJRC2P+xS9gVqK8t0zU6zmXRkGqYaLj9nLK+GzgQ=="
        )!
    }
}

private struct BoundedReferencePackageSigner:
    DevicePackageSigner
{
    let observerIdentity: DeviceLedgerObserverIdentity
    let expectedDigest: Data

    init(
        observerIdentity: DeviceLedgerObserverIdentity,
        expectedDigest: Data
    ) {
        self.observerIdentity = observerIdentity
        self.expectedDigest = Data(expectedDigest)
    }

    func signPackageDigest(
        _ digest: Data
    ) async throws -> Data {
        guard digest == expectedDigest else {
            throw BoundedReferenceSignerError
                .unexpectedDigest
        }

        return Data(
            base64Encoded:
                "OAI79AEDhcp/XMZwhT7SXlj0lz0GOAfUMOe3f8UTXocdN4A1tOszsQUIUH2dIRAjSsXwtCDpw/wKsNGS4AoZlQ=="
        )!
    }
}

private enum BoundedReferenceSignerError:
    Error,
    Sendable,
    Equatable
{
    case unexpectedDigest
}

private enum ProofResourceLoader {
    static func data(
        named fileName: String
    ) throws -> Data {
        let bundle = Bundle(
            for: PULSEmechProofResourceAnchor.self
        )
        guard let url = bundle.url(
            forResource: fileName,
            withExtension: nil
        ) else {
            throw BoundedProofRunError
                .missingBundledResource(fileName)
        }

        do {
            return try Data(contentsOf: url)
        } catch {
            throw BoundedProofRunError
                .resourceReadFailed(fileName)
        }
    }
}

private final class PULSEmechProofResourceAnchor:
    NSObject
{}

private struct BundledVerifierReport: Decodable {
    let authorityBoundary: AuthorityBoundary
    let checks: [String: String]
    let claimBoundary: ClaimBoundary
    let errors: [VerifierDiagnostic]
    let failedCheckIDs: [String]
    let failureStage: String?
    let ok: Bool
    let reproductionContext: ReproductionContext
    let result: String
    let semanticSummary: SemanticSummary
    let signatureVerification: SignatureVerification
    let subject: Subject
    let tool: Tool

    enum CodingKeys: String, CodingKey {
        case authorityBoundary = "authority_boundary"
        case checks
        case claimBoundary = "claim_boundary"
        case errors
        case failedCheckIDs = "failed_check_ids"
        case failureStage = "failure_stage"
        case ok
        case reproductionContext = "reproduction_context"
        case result
        case semanticSummary = "semantic_summary"
        case signatureVerification = "signature_verification"
        case subject
        case tool
    }

    struct AuthorityBoundary: Decodable {
        let authorityEffect: String
        let changesReleaseAuthority: Bool
        let createsDeviceControlAuthority: Bool
        let createsReleaseDecision: Bool
        let verifierReportIsReleaseAuthority: Bool

        enum CodingKeys: String, CodingKey {
            case authorityEffect = "authority_effect"
            case changesReleaseAuthority =
                "changes_release_authority"
            case createsDeviceControlAuthority =
                "creates_device_control_authority"
            case createsReleaseDecision =
                "creates_release_decision"
            case verifierReportIsReleaseAuthority =
                "verifier_report_is_release_authority"
        }
    }

    struct ClaimBoundary: Decodable {
        let externalValidationClaim: String

        enum CodingKeys: String, CodingKey {
            case externalValidationClaim =
                "external_validation_claim"
        }
    }

    struct ReproductionContext: Decodable {
        let verifierImplementationRelation: String

        enum CodingKeys: String, CodingKey {
            case verifierImplementationRelation =
                "verifier_implementation_relation"
        }
    }

    struct SemanticSummary: Decodable {
        let declaredUnavailabilityPresent: Bool

        enum CodingKeys: String, CodingKey {
            case declaredUnavailabilityPresent =
                "declared_unavailability_present"
        }
    }

    struct SignatureVerification: Decodable {
        let checkpoint: SignatureResult
        let package: SignatureResult
    }

    struct SignatureResult: Decodable {
        let signatureStatus: String

        enum CodingKeys: String, CodingKey {
            case signatureStatus = "signature_status"
        }
    }

    struct Subject: Decodable {
        let carrierFileName: String
        let carrierSHA256: String
        let carrierSizeBytes: Int64

        enum CodingKeys: String, CodingKey {
            case carrierFileName = "carrier_file_name"
            case carrierSHA256 = "carrier_sha256"
            case carrierSizeBytes = "carrier_size_bytes"
        }
    }

    struct Tool: Decodable {
        let producerCodeImported: Bool

        enum CodingKeys: String, CodingKey {
            case producerCodeImported =
                "producer_code_imported"
        }
    }

    struct VerifierDiagnostic: Decodable {}
}
