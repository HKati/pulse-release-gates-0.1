import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class DeviceLedgerManifestTests: XCTestCase {
    private let expectedManifestSHA256 =
        "47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1"

    private func referenceMaterialization() async throws
        -> (
            closure: DeviceTransitionLedgerClosure,
            checkpointSignature:
                DeviceCheckpointSignatureMaterialization,
            manifest: DeviceLedgerManifestMaterialization
        )
    {
        let closure = try await FixtureDeviceLedgerManifestFactory
            .makeReferenceClosure()
        let checkpointSignature =
            try await FixtureDeviceLedgerManifestFactory
                .makeReferenceCheckpointSignature(
                    closure: closure
                )
        let manifest = try closure.materializePackageManifest(
            checkpointSignature: checkpointSignature,
            contractMembers:
                FixtureDeviceLedgerManifestFactory
                    .contractMembers()
        )
        return (
            closure,
            checkpointSignature,
            manifest
        )
    }

    func testReferenceManifestMatchesExactPythonBytesAndIdentity()
        async throws
    {
        let result = try await referenceMaterialization()
        let generated = result.manifest.manifest.canonicalBytes()
        let expected = try FixtureDeviceLedgerManifestFactory
            .referenceManifestBytes()

        XCTAssertEqual(generated, expected)
        XCTAssertEqual(generated.count, 5_764)
        XCTAssertEqual(
            result.manifest.manifest.manifestSHA256.rawValue,
            expectedManifestSHA256
        )
        XCTAssertEqual(
            result.manifest.manifest.sizeBytes,
            5_764
        )
        XCTAssertNotEqual(generated.last, 0x0A)
        XCTAssertEqual(
            result.manifest.manifest.createdUnixNS,
            FixtureDeviceLedgerManifestFactory.baseWallTime +
                13_000_000
        )
        XCTAssertEqual(
            result.manifest.manifest.recordCount,
            14
        )
    }

    func testReferencePayloadInventoryMatchesExactEightMembers()
        async throws
    {
        let result = try await referenceMaterialization()
        let members = result.manifest.payloadMembers

        XCTAssertEqual(
            members.map(\.path),
            [
                "contracts/pulsemech_device_canonical_json_v0.json",
                "contracts/pulsemech_ios_observation_contract_v0.json",
                "keys/observer-public-key-v0.bin",
                "ledger/pulsemech_device_transition_ledger_v0.json",
                "schemas/pulsemech_device_ledger_manifest_v0.schema.json",
                "schemas/pulsemech_device_signature_v0.schema.json",
                "schemas/pulsemech_device_transition_ledger_v0.schema.json",
                "signatures/checkpoint-signature-v0.json",
            ]
        )
        XCTAssertEqual(
            members.map(\.role),
            [
                "canonicalization_profile",
                "ios_observation_contract",
                "observer_public_key",
                "transition_ledger",
                "ledger_manifest_schema",
                "signature_schema",
                "transition_ledger_schema",
                "checkpoint_signature",
            ]
        )
        XCTAssertEqual(
            members.map(\.mediaType),
            [
                "application/json",
                "application/json",
                "application/octet-stream",
                "application/json",
                "application/schema+json",
                "application/schema+json",
                "application/schema+json",
                "application/json",
            ]
        )
        XCTAssertEqual(
            members.map(\.sizeBytes),
            [
                2_719,
                9_893,
                65,
                31_904,
                19_913,
                5_031,
                54_069,
                1_252,
            ]
        )
        XCTAssertEqual(
            members.map(\.sha256.rawValue),
            [
                "ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550",
                "e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2",
                "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6",
                "360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77",
                "bf8126db9a9c5c40f1dbe3ad835ae7711a98d77fa8b3a59016f4ebd406d0ce3d",
                "80304b08b73f3c05092909e7917240af94121e2c15b9305440a7e01460c049c0",
                "58eddf75d9c89fef4aa3787e3e4db4d86624f4a387b2a33a3c2fd1f972d6c07f",
                "2b8de3ae948dfe0693900f4ba83a17a15ab39a80b8ecd37a9c22a1e60c705605",
            ]
        )
        XCTAssertEqual(
            result.manifest.manifest.payloadMembers,
            members
        )
    }

    func testStaticContractAndSchemaDriftIsRejected()
        throws
    {
        let valid = try FixtureDeviceLedgerManifestFactory
            .contractMembers()

        let cases: [
            (
                path: String,
                build:
                    (Data) throws
                        -> DeviceLedgerManifestContractMembers,
                original: Data
            )
        ] = [
            (
                "contracts/pulsemech_device_canonical_json_v0.json",
                { mutated in
                    try DeviceLedgerManifestContractMembers(
                        canonicalizationProfileBytes: mutated,
                        observationContractBytes:
                            valid.observationContractBytes,
                        manifestSchemaBytes:
                            valid.manifestSchemaBytes,
                        signatureSchemaBytes:
                            valid.signatureSchemaBytes,
                        transitionLedgerSchemaBytes:
                            valid.transitionLedgerSchemaBytes
                    )
                },
                valid.canonicalizationProfileBytes
            ),
            (
                "contracts/pulsemech_ios_observation_contract_v0.json",
                { mutated in
                    try DeviceLedgerManifestContractMembers(
                        canonicalizationProfileBytes:
                            valid.canonicalizationProfileBytes,
                        observationContractBytes: mutated,
                        manifestSchemaBytes:
                            valid.manifestSchemaBytes,
                        signatureSchemaBytes:
                            valid.signatureSchemaBytes,
                        transitionLedgerSchemaBytes:
                            valid.transitionLedgerSchemaBytes
                    )
                },
                valid.observationContractBytes
            ),
            (
                "schemas/pulsemech_device_ledger_manifest_v0.schema.json",
                { mutated in
                    try DeviceLedgerManifestContractMembers(
                        canonicalizationProfileBytes:
                            valid.canonicalizationProfileBytes,
                        observationContractBytes:
                            valid.observationContractBytes,
                        manifestSchemaBytes: mutated,
                        signatureSchemaBytes:
                            valid.signatureSchemaBytes,
                        transitionLedgerSchemaBytes:
                            valid.transitionLedgerSchemaBytes
                    )
                },
                valid.manifestSchemaBytes
            ),
            (
                "schemas/pulsemech_device_signature_v0.schema.json",
                { mutated in
                    try DeviceLedgerManifestContractMembers(
                        canonicalizationProfileBytes:
                            valid.canonicalizationProfileBytes,
                        observationContractBytes:
                            valid.observationContractBytes,
                        manifestSchemaBytes:
                            valid.manifestSchemaBytes,
                        signatureSchemaBytes: mutated,
                        transitionLedgerSchemaBytes:
                            valid.transitionLedgerSchemaBytes
                    )
                },
                valid.signatureSchemaBytes
            ),
            (
                "schemas/pulsemech_device_transition_ledger_v0.schema.json",
                { mutated in
                    try DeviceLedgerManifestContractMembers(
                        canonicalizationProfileBytes:
                            valid.canonicalizationProfileBytes,
                        observationContractBytes:
                            valid.observationContractBytes,
                        manifestSchemaBytes:
                            valid.manifestSchemaBytes,
                        signatureSchemaBytes:
                            valid.signatureSchemaBytes,
                        transitionLedgerSchemaBytes: mutated
                    )
                },
                valid.transitionLedgerSchemaBytes
            ),
        ]

        for testCase in cases {
            var mutated = testCase.original
            mutated[mutated.startIndex] ^= 0x01

            XCTAssertThrowsError(
                try testCase.build(mutated)
            ) { error in
                XCTAssertEqual(
                    error as?
                        DeviceLedgerManifestContractMembersError,
                    .staticMemberIdentityMismatch(
                        path: testCase.path
                    )
                )
            }
        }
    }

    func testCheckpointSignatureSubjectBindingsAreRequired()
        async throws
    {
        let result = try await referenceMaterialization()
        let closure = result.closure
        let signature = result.checkpointSignature.signature
        let contractMembers =
            try FixtureDeviceLedgerManifestFactory
                .contractMembers()

        let wrongLedgerSubject =
            DeviceCheckpointSignatureSubject(
                ledgerID: try LedgerIdentifier(
                    "device-ledger:other"
                ),
                observerPublicKeyFingerprintSHA256:
                    closure.checkpointSource
                        .observerPublicKeyFingerprintSHA256,
                signedObjectSHA256:
                    closure.checkpointRecord.recordSHA256
            )
        let wrongLedger = materialization(
            subject: wrongLedgerSubject,
            signature: signature
        )
        XCTAssertThrowsError(
            try closure.materializePackageManifest(
                checkpointSignature: wrongLedger,
                contractMembers: contractMembers
            )
        ) { error in
            XCTAssertEqual(
                error as?
                    DeviceLedgerManifestMaterializationError,
                .checkpointSignatureLedgerMismatch
            )
        }

        let wrongObserverSubject =
            DeviceCheckpointSignatureSubject(
                ledgerID: closure.checkpointSource.ledgerID,
                observerPublicKeyFingerprintSHA256:
                    try! SHA256HexDigest(
                        String(repeating: "0", count: 64)
                    ),
                signedObjectSHA256:
                    closure.checkpointRecord.recordSHA256
            )
        let wrongObserver = materialization(
            subject: wrongObserverSubject,
            signature: signature
        )
        XCTAssertThrowsError(
            try closure.materializePackageManifest(
                checkpointSignature: wrongObserver,
                contractMembers: contractMembers
            )
        ) { error in
            XCTAssertEqual(
                error as?
                    DeviceLedgerManifestMaterializationError,
                .checkpointSignatureObserverMismatch
            )
        }

        let wrongObjectSubject =
            DeviceCheckpointSignatureSubject(
                ledgerID: closure.checkpointSource.ledgerID,
                observerPublicKeyFingerprintSHA256:
                    closure.checkpointSource
                        .observerPublicKeyFingerprintSHA256,
                signedObjectSHA256:
                    try! SHA256HexDigest(
                        String(repeating: "0", count: 64)
                    )
            )
        let wrongObject = materialization(
            subject: wrongObjectSubject,
            signature: signature
        )
        XCTAssertThrowsError(
            try closure.materializePackageManifest(
                checkpointSignature: wrongObject,
                contractMembers: contractMembers
            )
        ) { error in
            XCTAssertEqual(
                error as?
                    DeviceLedgerManifestMaterializationError,
                .checkpointSignatureObjectMismatch
            )
        }
    }

    func testSignatureMaterializationMustRemainInternallyConsistent()
        async throws
    {
        let result = try await referenceMaterialization()
        let valid = result.checkpointSignature
        let wrongSubject = DeviceCheckpointSignatureSubject(
            ledgerID: try LedgerIdentifier(
                "device-ledger:other"
            ),
            observerPublicKeyFingerprintSHA256:
                valid.subject
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                valid.subject.signedObjectSHA256
        )
        let wrongDocument = DeviceCheckpointSignatureDocument(
            subject: wrongSubject,
            signature: valid.signature
        )
        let inconsistent =
            DeviceCheckpointSignatureMaterialization(
                subject: valid.subject,
                signatureInputSHA256:
                    valid.signatureInputSHA256,
                signature: valid.signature,
                document: wrongDocument
            )

        XCTAssertThrowsError(
            try result.closure.materializePackageManifest(
                checkpointSignature: inconsistent,
                contractMembers:
                    FixtureDeviceLedgerManifestFactory
                        .contractMembers()
            )
        ) { error in
            XCTAssertEqual(
                error as?
                    DeviceLedgerManifestMaterializationError,
                .checkpointSignatureMaterializationMismatch
            )
        }
    }

    func testDynamicMemberBytesComeOnlyFromClosureAndSignature()
        async throws
    {
        let result = try await referenceMaterialization()

        XCTAssertEqual(
            result.manifest.payloadMember(
                at: "keys/observer-public-key-v0.bin"
            )?.exactBytes,
            result.closure.document.observerIdentity
                .publicKeyX963Uncompressed
        )
        XCTAssertEqual(
            result.manifest.payloadMember(
                at:
                    "ledger/pulsemech_device_transition_ledger_v0.json"
            )?.exactBytes,
            result.closure.document.canonicalBytes()
        )
        XCTAssertEqual(
            result.manifest.payloadMember(
                at:
                    "signatures/checkpoint-signature-v0.json"
            )?.exactBytes,
            result.checkpointSignature.document.canonicalBytes()
        )
    }

    func testManifestMaterializationDoesNotMutateInputs()
        async throws
    {
        let closure = try await FixtureDeviceLedgerManifestFactory
            .makeReferenceClosure()
        let signature =
            try await FixtureDeviceLedgerManifestFactory
                .makeReferenceCheckpointSignature(
                    closure: closure
                )
        let closureBefore = closure
        let signatureBefore = signature

        _ = try closure.materializePackageManifest(
            checkpointSignature: signature,
            contractMembers:
                FixtureDeviceLedgerManifestFactory
                    .contractMembers()
        )

        XCTAssertEqual(closure, closureBefore)
        XCTAssertEqual(signature, signatureBefore)
    }

    func testPayloadMemberSizeLimitIsFailClosed() {
        let oversized = Data(
            repeating: 0,
            count:
                Int(DeviceLedgerPayloadMember.maximumSizeBytes) + 1
        )

        XCTAssertThrowsError(
            try DeviceLedgerPayloadMember(
                kind: .transitionLedger,
                exactBytes: oversized
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceLedgerPayloadMemberError,
                .memberExceedsCarrierLimit(
                    path:
                        "ledger/pulsemech_device_transition_ledger_v0.json"
                )
            )
        }
    }

    func testReorderedInventoryCannotConstructManifest()
        async throws
    {
        let result = try await referenceMaterialization()
        let manifest = result.manifest.manifest
        var reordered = result.manifest.payloadMembers
        reordered.swapAt(0, 1)

        XCTAssertThrowsError(
            try DeviceLedgerManifest(
                createdUnixNS: manifest.createdUnixNS,
                ledgerID: manifest.ledgerID,
                recordStatus: manifest.recordStatus,
                ledgerSHA256: manifest.ledgerSHA256,
                ledgerSizeBytes: manifest.ledgerSizeBytes,
                recordCount: manifest.recordCount,
                checkpointRecordSHA256:
                    manifest.checkpointRecordSHA256,
                observerPublicKeyFingerprintSHA256:
                    manifest
                        .observerPublicKeyFingerprintSHA256,
                checkpointSignatureDocumentSHA256:
                    manifest
                        .checkpointSignatureDocumentSHA256,
                checkpointSignatureDocumentSizeBytes:
                    manifest
                        .checkpointSignatureDocumentSizeBytes,
                payloadMembers: reordered
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceLedgerManifestError,
                .payloadInventoryMismatch
            )
        }
    }

    func testManifestExcludesCircularMembersFromPayloadInventory()
        async throws
    {
        let result = try await referenceMaterialization()
        let paths = Set(
            result.manifest.payloadMembers.map(\.path)
        )

        XCTAssertFalse(
            paths.contains(DeviceLedgerManifest.manifestPath)
        )
        XCTAssertFalse(
            paths.contains(
                DeviceLedgerManifest.packageSignaturePath
            )
        )
        XCTAssertEqual(paths.count, 8)
    }

    private func materialization(
        subject: DeviceCheckpointSignatureSubject,
        signature: DeviceP256Signature
    ) -> DeviceCheckpointSignatureMaterialization {
        DeviceCheckpointSignatureMaterialization(
            subject: subject,
            signatureInputSHA256:
                subject.signatureInputSHA256,
            signature: signature,
            document:
                DeviceCheckpointSignatureDocument(
                    subject: subject,
                    signature: signature
                )
        )
    }
}
