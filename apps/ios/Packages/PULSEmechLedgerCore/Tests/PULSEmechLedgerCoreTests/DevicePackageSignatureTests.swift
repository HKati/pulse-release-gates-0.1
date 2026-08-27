import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class DevicePackageSignatureTests: XCTestCase {
    private let expectedSubjectSHA256 =
        "8d888ae44309f5543c6fd9efec3f910f1c62246a3262b281b22141df830b1604"

    private let expectedSigningInputSHA256 =
        "fcd90dc41a07d24146f04938d6ca43a88c17c0f0e2d526d4f04dbb4e2ff7012e"

    private let expectedDocumentSHA256 =
        "de5eb2228e0626803a0ede44f5779855d4e22dbc98cea86352dd8f6524c09eb4"

    private let expectedSubjectText = #"""
    {"ledger_id":"device-ledger:iphone-synthetic-reference-v0","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","signature_suite":"ecdsa-p256-sha256","signed_object_sha256":"47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1"}
    """#

    private let expectedDocumentText = #"""
    {"authority_effect":"none","curve":"secp256r1","document_type":"pulsemech_device_signature","ecdsa_s_rule":"low_s_required","ecdsa_scalar_range":"one_to_curve_order_minus_one","hash_algorithm":"SHA-256","ledger_id":"device-ledger:iphone-synthetic-reference-v0","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","public_key_encoding":"x963_uncompressed","public_key_fingerprint_subject":"exact_65_byte_x963_uncompressed_public_key","public_key_size_bytes":65,"schema_version":"pulsemech_device_signature_v0","signature_base64":"OAI79AEDhcp/XMZwhT7SXlj0lz0GOAfUMOe3f8UTXocdN4A1tOszsQUIUH2dIRAjSsXwtCDpw/wKsNGS4AoZlQ==","signature_domain":"PULSEMECH-DEVICE-LEDGER-PACKAGE-V0","signature_encoding":"ieee_p1363_fixed_width","signature_role":"ledger_package","signature_size_bytes":64,"signature_subject_canonicalization":"pulsemech_device_canonical_json_v0","signature_subject_framing":"ascii_domain_separator_then_0x00_then_canonical_subject_json","signature_subject_version":"pulsemech_device_signature_subject_v0","signature_suite":"ecdsa-p256-sha256","signed_object_sha256":"47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1","signed_object_type":"ledger_manifest_sha256"}
    """#

    private func referenceInputs() async throws
        -> (
            closure: DeviceTransitionLedgerClosure,
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
            manifest
        )
    }

    private func packageSubject(
        for manifest: DeviceLedgerManifest
    ) -> DevicePackageSignatureSubject {
        DevicePackageSignatureSubject(
            ledgerID: manifest.ledgerID,
            observerPublicKeyFingerprintSHA256:
                manifest.observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                manifest.manifestSHA256
        )
    }

    private func alternateObserverIdentity() throws
        -> DeviceLedgerObserverIdentity
    {
        try DeviceLedgerObserverIdentity(
            identityScope: .installation,
            keyOriginProfile: .softwareP256,
            publicKeyX963Uncompressed: Data(
                base64Encoded:
                    "BHzyexiNA09+ilI4AwS1GsPAiWnid/IbNaYLSPxHZpl4B3dVENuO0EApPZrGn3Qw27p9reY86YIpngS3nSJ4c9E="
            )!
        )
    }

    private func copyManifest(
        _ manifest: DeviceLedgerManifest,
        ledgerID: LedgerIdentifier? = nil,
        observerPublicKeyFingerprintSHA256:
            SHA256HexDigest? = nil,
        payloadMembers:
            [DeviceLedgerPayloadMember]? = nil
    ) throws -> DeviceLedgerManifest {
        try DeviceLedgerManifest(
            createdUnixNS: manifest.createdUnixNS,
            ledgerID: ledgerID ?? manifest.ledgerID,
            recordStatus: manifest.recordStatus,
            ledgerSHA256: manifest.ledgerSHA256,
            ledgerSizeBytes: manifest.ledgerSizeBytes,
            recordCount: manifest.recordCount,
            checkpointRecordSHA256:
                manifest.checkpointRecordSHA256,
            observerPublicKeyFingerprintSHA256:
                observerPublicKeyFingerprintSHA256 ??
                    manifest.observerPublicKeyFingerprintSHA256,
            checkpointSignatureDocumentSHA256:
                manifest.checkpointSignatureDocumentSHA256,
            checkpointSignatureDocumentSizeBytes:
                manifest.checkpointSignatureDocumentSizeBytes,
            payloadMembers:
                payloadMembers ?? manifest.payloadMembers
        )
    }

    private func highSSignature() -> Data {
        var bytes = Data(
            repeating: 0,
            count: 64
        )
        bytes[31] = 1
        bytes.replaceSubrange(
            32..<64,
            with: [
                0x7F, 0xFF, 0xFF, 0xFF,
                0x80, 0x00, 0x00, 0x00,
                0x7F, 0xFF, 0xFF, 0xFF,
                0xFF, 0xFF, 0xFF, 0xFF,
                0xDE, 0x73, 0x7D, 0x56,
                0xD3, 0x8B, 0xCF, 0x42,
                0x79, 0xDC, 0xE5, 0x61,
                0x7E, 0x31, 0x92, 0xA9,
            ]
        )
        return bytes
    }

    func testReferenceSubjectMatchesExactCanonicalBytesAndIdentity()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let canonicalBytes = subject.canonicalBytes()

        XCTAssertEqual(
            canonicalBytes,
            Data(expectedSubjectText.utf8)
        )
        XCTAssertEqual(canonicalBytes.count, 295)
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: canonicalBytes
            ).rawValue,
            expectedSubjectSHA256
        )
        XCTAssertNotEqual(canonicalBytes.last, 0x0A)
    }

    func testReferenceSubjectUsesExactPackageDomainFraming()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )

        var expected = Data(
            DevicePackageSignatureSubject.signatureDomain.utf8
        )
        expected.append(0x00)
        expected.append(subject.canonicalBytes())

        XCTAssertEqual(subject.framedBytes(), expected)
        XCTAssertEqual(subject.framedBytes().count, 330)
    }

    func testReferenceSubjectProducesExactSigningInputSHA256()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )

        XCTAssertEqual(subject.signatureInputSHA256.count, 32)
        XCTAssertEqual(
            subject.signatureInputSHA256,
            Data(
                base64Encoded:
                    "/NkNxBoH0kFG8Ek41spDqIwXwPDi1SbU8E27Ti/3AS4="
            )!
        )
        XCTAssertEqual(
            subject.signatureInputSHA256Hex.rawValue,
            expectedSigningInputSHA256
        )
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: subject.framedBytes()
            ),
            subject.signatureInputSHA256Hex
        )
    }

    func testFixtureSignerAdmitsOnlyTheExactPackageDigest()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let expectedSignature =
            FixturePackageSigner.referencePackageSignature()
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature: expectedSignature
        )

        let acceptedSignature = try await signer.signPackageDigest(
            subject.signatureInputSHA256
        )
        XCTAssertEqual(
            acceptedSignature,
            expectedSignature
        )

        do {
            _ = try await signer.signPackageDigest(
                Data(repeating: 0, count: 32)
            )
            XCTFail("Expected the fixture signer to reject the wrong digest")
        } catch {
            XCTAssertEqual(
                error as? FixturePackageSignerError,
                .unexpectedDigest
            )
        }
    }

    func testReferenceMaterializationMatchesExactDocumentBytesAndIdentity()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let recorder = FixturePackageSignerInvocationRecorder()
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.referencePackageSignature(),
            invocationRecorder: recorder
        )

        let materialized = try await inputs.closure
            .materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )
        let documentBytes = materialized.document.canonicalBytes()
        let receivedDigests = await recorder.snapshot()

        XCTAssertEqual(materialized.subject, subject)
        XCTAssertEqual(
            materialized.signatureInputSHA256,
            subject.signatureInputSHA256
        )
        XCTAssertEqual(
            materialized.signature.ieeeP1363FixedWidth,
            FixturePackageSigner.referencePackageSignature()
        )
        XCTAssertEqual(
            documentBytes,
            Data(expectedDocumentText.utf8)
        )
        XCTAssertEqual(documentBytes.count, 1_244)
        XCTAssertEqual(materialized.document.sizeBytes, 1_244)
        XCTAssertEqual(
            materialized.document.documentSHA256.rawValue,
            expectedDocumentSHA256
        )
        XCTAssertNotEqual(documentBytes.last, 0x0A)
        XCTAssertEqual(
            receivedDigests,
            [subject.signatureInputSHA256]
        )
    }

    func testMaterializerBindsPackageSubjectToManifestLedgerID()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.validShapeSignature()
        )

        let materialized = try await inputs.closure
            .materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )

        XCTAssertEqual(
            materialized.subject.ledgerID,
            inputs.manifest.manifest.ledgerID
        )
        XCTAssertEqual(
            materialized.document.subject.ledgerID,
            inputs.closure.checkpointSource.ledgerID
        )
    }

    func testMaterializerBindsPackageSubjectToManifestObserverFingerprint()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.validShapeSignature()
        )

        let materialized = try await inputs.closure
            .materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )

        XCTAssertEqual(
            materialized.subject
                .observerPublicKeyFingerprintSHA256,
            inputs.manifest.manifest
                .observerPublicKeyFingerprintSHA256
        )
        XCTAssertEqual(
            materialized.document.subject
                .observerPublicKeyFingerprintSHA256,
            inputs.closure.document.observerIdentity
                .publicKeyFingerprintSHA256
        )
    }

    func testMaterializerBindsSignedObjectToExactCanonicalManifestSHA256()
        async throws
    {
        let inputs = try await referenceInputs()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.validShapeSignature()
        )

        let materialized = try await inputs.closure
            .materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )

        XCTAssertEqual(
            materialized.subject.signedObjectSHA256,
            inputs.manifest.manifest.manifestSHA256
        )
        XCTAssertEqual(
            materialized.document.subject.signedObjectSHA256,
            LedgerRecordHasher.sha256Hex(
                of: inputs.manifest.manifest.canonicalBytes()
            )
        )
    }

    func testMaterializerRejectsManifestMaterializationMismatchBeforeSigning()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let inconsistent = DeviceLedgerManifestMaterialization(
            payloadMembers:
                Array(inputs.manifest.payloadMembers.dropLast()),
            manifest: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: Data(),
            returnedSignature:
                FixturePackageSigner.validShapeSignature(),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inconsistent,
                using: signer
            )
            XCTFail("Expected manifest/materialization mismatch rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .manifestMaterializationMismatch
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 0)
    }

    func testMaterializerRejectsManifestClosureLedgerMismatchBeforeSigning()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let wrongManifest = try copyManifest(
            inputs.manifest.manifest,
            ledgerID: try LedgerIdentifier(
                "device-ledger:other"
            )
        )
        let inconsistent = DeviceLedgerManifestMaterialization(
            payloadMembers: inputs.manifest.payloadMembers,
            manifest: wrongManifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: Data(),
            returnedSignature:
                FixturePackageSigner.validShapeSignature(),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inconsistent,
                using: signer
            )
            XCTFail("Expected manifest/closure ledger mismatch rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .manifestClosureLedgerMismatch
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 0)
    }

    func testMaterializerRejectsManifestClosureObserverMismatchBeforeSigning()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let alternateIdentity = try alternateObserverIdentity()
        let alternateMember = try DeviceLedgerPayloadMember(
            kind: .observerPublicKey,
            exactBytes:
                alternateIdentity.publicKeyX963Uncompressed
        )
        var payloadMembers = inputs.manifest.payloadMembers
        let observerIndex = try XCTUnwrap(
            payloadMembers.firstIndex {
                $0.path == "keys/observer-public-key-v0.bin"
            }
        )
        payloadMembers[observerIndex] = alternateMember

        let wrongManifest = try copyManifest(
            inputs.manifest.manifest,
            observerPublicKeyFingerprintSHA256:
                alternateIdentity.publicKeyFingerprintSHA256,
            payloadMembers: payloadMembers
        )
        let inconsistent = DeviceLedgerManifestMaterialization(
            payloadMembers: payloadMembers,
            manifest: wrongManifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: Data(),
            returnedSignature:
                FixturePackageSigner.validShapeSignature(),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inconsistent,
                using: signer
            )
            XCTFail("Expected manifest/closure observer mismatch rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .manifestClosureObserverMismatch
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 0)
    }

    func testMaterializerRejectsSignerIdentityBeforeSignerInvocation()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: try alternateObserverIdentity(),
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.validShapeSignature(),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )
            XCTFail("Expected signer observer-identity rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .signerObserverIdentityMismatch
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 0)
    }

    func testMaterializerRejectsMalformedFixedWidthSignerOutput()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature: Data(
                repeating: 0,
                count: 63
            ),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )
            XCTFail("Expected malformed signature output rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .signerReturnedInvalidSignature(
                    .signatureSizeInvalid
                )
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 1)
    }

    func testMaterializerRejectsHighSSignerOutput()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature: highSSignature(),
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )
            XCTFail("Expected high-S signature output rejection")
        } catch {
            XCTAssertEqual(
                error as?
                    DevicePackageSignatureMaterializationError,
                .signerReturnedInvalidSignature(
                    .highSForbidden
                )
            )
        }

        let invocationCount = await recorder.invocationCount
        XCTAssertEqual(invocationCount, 1)
    }

    func testMaterializerPropagatesSignerFailureWithoutOutput()
        async throws
    {
        let inputs = try await referenceInputs()
        let recorder = FixturePackageSignerInvocationRecorder()
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.validShapeSignature(),
            forceFailure: true,
            invocationRecorder: recorder
        )

        do {
            _ = try await inputs.closure.materializePackageSignature(
                manifest: inputs.manifest,
                using: signer
            )
            XCTFail("Expected the signer failure to propagate")
        } catch {
            XCTAssertEqual(
                error as? FixturePackageSignerError,
                .forcedFailure
            )
        }

        let receivedDigests = await recorder.snapshot()
        XCTAssertEqual(
            receivedDigests,
            [subject.signatureInputSHA256]
        )
    }

    func testPackageSignatureMaterializationDoesNotMutateInputs()
        async throws
    {
        let inputs = try await referenceInputs()
        let closureBefore = inputs.closure
        let manifestBefore = inputs.manifest
        let subject = packageSubject(
            for: inputs.manifest.manifest
        )
        let signer = FixturePackageSigner(
            observerIdentity: inputs.closure.document.observerIdentity,
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.referencePackageSignature()
        )

        _ = try await inputs.closure.materializePackageSignature(
            manifest: inputs.manifest,
            using: signer
        )

        XCTAssertEqual(inputs.closure, closureBefore)
        XCTAssertEqual(inputs.manifest, manifestBefore)
    }
}
