import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class DeviceCheckpointSignatureTests: XCTestCase {
    private let baseWallTime: Int64 = 1_700_000_000_000_000_000

    private let referenceLedgerID = try! LedgerIdentifier(
        "device-ledger:iphone-synthetic-reference-v0"
    )
    private let referenceObserverFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )
    private let referenceCheckpointSHA256 = try! SHA256HexDigest(
        "16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff"
    )

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private func fixturePublicKey() -> Data {
        Data(
            base64Encoded:
                "BAIa75uP4gO+twVlypJYAjIKXK0JVnBPBArgoE50sEI+HbKkjFpxpQifk3hgoQs08yYzY850htpv1wl0/4u6i10="
        )!
    }

    private func fixtureObserverIdentity() throws
        -> DeviceLedgerObserverIdentity
    {
        try DeviceLedgerObserverIdentity(
            identityScope: .fixtureInstallation,
            keyOriginProfile: .fixtureSoftwareP256,
            publicKeyX963Uncompressed: fixturePublicKey()
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

    private func referenceSubject() -> DeviceCheckpointSignatureSubject {
        DeviceCheckpointSignatureSubject(
            ledgerID: referenceLedgerID,
            observerPublicKeyFingerprintSHA256:
                referenceObserverFingerprint,
            signedObjectSHA256: referenceCheckpointSHA256
        )
    }

    private func makeMinimalClosure() async throws
        -> DeviceTransitionLedgerClosure
    {
        let chain = LedgerRecordChain(
            ledgerID: referenceLedgerID,
            observerPublicKeyFingerprintSHA256:
                referenceObserverFingerprint,
            recordStatus: .syntheticReference
        )

        let openingPayload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )
        let openingDraft = try openingPayload.recordDraft(
            recordID: identifier("record:000-session-open-a"),
            recordedWallTimeUnixNS: baseWallTime,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 1_000
        )
        _ = try await chain.append(openingDraft)

        return try await chain.closeAndMaterializeLedger(
            LedgerCheckpointMaterializationInput(
                checkpointID: identifier("checkpoint:minimal-v0"),
                recordID: identifier("record:001-checkpoint"),
                recordedWallTimeUnixNS:
                    baseWallTime + 1_000_000
            ),
            observerIdentity: fixtureObserverIdentity()
        )
    }

    func testReferenceSubjectMatchesExactPythonBytesAndDigest() {
        let subject = referenceSubject()
        let expected = Data(
            #"""
            {"ledger_id":"device-ledger:iphone-synthetic-reference-v0","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","signature_suite":"ecdsa-p256-sha256","signed_object_sha256":"16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff"}
            """#.utf8
        )

        XCTAssertEqual(subject.canonicalBytes(), expected)
        XCTAssertEqual(subject.canonicalBytes().count, 295)
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: subject.canonicalBytes()
            ).rawValue,
            "2b686f24f53d517172867231ce90caf4e21e5ee580576b17f88795bf462be8e2"
        )
        XCTAssertEqual(subject.framedBytes().count, 333)
        XCTAssertEqual(
            subject.signatureInputSHA256Hex.rawValue,
            "043b69a81530ea0b10effd8abc19f0ea7b55757cc3d5d6bc178242e855e14c4e"
        )
        XCTAssertEqual(
            subject.signatureInputSHA256.count,
            32
        )
        XCTAssertNotEqual(subject.canonicalBytes().last, 0x0A)
    }

    func testReferenceDocumentMatchesExactPythonBytes() throws {
        let signature = try DeviceP256Signature(
            ieeeP1363FixedWidth:
                FixtureCheckpointSigner.referenceCheckpointSignature()
        )
        let document = DeviceCheckpointSignatureDocument(
            subject: referenceSubject(),
            signature: signature
        )
        let expected = Data(
            #"""
            {"authority_effect":"none","curve":"secp256r1","document_type":"pulsemech_device_signature","ecdsa_s_rule":"low_s_required","ecdsa_scalar_range":"one_to_curve_order_minus_one","hash_algorithm":"SHA-256","ledger_id":"device-ledger:iphone-synthetic-reference-v0","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","public_key_encoding":"x963_uncompressed","public_key_fingerprint_subject":"exact_65_byte_x963_uncompressed_public_key","public_key_size_bytes":65,"schema_version":"pulsemech_device_signature_v0","signature_base64":"BOBikuqSCnXUQnqSzGnB6EmJhvM0Bm7BGg0uX0EeSAMJyAaJRC2P+xS9gVqK8t0zU6zmXRkGqYaLj9nLK+GzgQ==","signature_domain":"PULSEMECH-DEVICE-LEDGER-CHECKPOINT-V0","signature_encoding":"ieee_p1363_fixed_width","signature_role":"ledger_checkpoint","signature_size_bytes":64,"signature_subject_canonicalization":"pulsemech_device_canonical_json_v0","signature_subject_framing":"ascii_domain_separator_then_0x00_then_canonical_subject_json","signature_subject_version":"pulsemech_device_signature_subject_v0","signature_suite":"ecdsa-p256-sha256","signed_object_sha256":"16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff","signed_object_type":"checkpoint_record_sha256"}
            """#.utf8
        )

        XCTAssertEqual(document.canonicalBytes(), expected)
        XCTAssertEqual(document.sizeBytes, 1_252)
        XCTAssertEqual(
            document.documentSHA256.rawValue,
            "2b8de3ae948dfe0693900f4ba83a17a15ab39a80b8ecd37a9c22a1e60c705605"
        )
        XCTAssertEqual(
            signature.canonicalBase64,
            "BOBikuqSCnXUQnqSzGnB6EmJhvM0Bm7BGg0uX0EeSAMJyAaJRC2P+xS9gVqK8t0zU6zmXRkGqYaLj9nLK+GzgQ=="
        )
        XCTAssertNotEqual(document.canonicalBytes().last, 0x0A)
    }

    func testSignatureScalarValidationIsFailClosed() {
        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: Data(repeating: 0, count: 63)
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .signatureSizeInvalid
            )
        }

        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: signatureBytes(
                    r: Data(repeating: 0, count: 32),
                    s: scalarOne()
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .rScalarZero
            )
        }

        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: signatureBytes(
                    r: curveOrder(),
                    s: scalarOne()
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .rScalarOutOfRange
            )
        }

        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: signatureBytes(
                    r: scalarOne(),
                    s: Data(repeating: 0, count: 32)
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .sScalarZero
            )
        }

        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: signatureBytes(
                    r: scalarOne(),
                    s: curveOrder()
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .sScalarOutOfRange
            )
        }

        XCTAssertThrowsError(
            try DeviceP256Signature(
                ieeeP1363FixedWidth: signatureBytes(
                    r: scalarOne(),
                    s: halfOrderPlusOne()
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceP256SignatureError,
                .highSForbidden
            )
        }
    }

    func testMaterializerBindsClosureIdentityAndExactDigest() async throws {
        let closure = try await makeMinimalClosure()
        let expectedSubject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signer = FixtureCheckpointSigner(
            observerIdentity: try fixtureObserverIdentity(),
            expectedDigest: expectedSubject.signatureInputSHA256,
            returnedSignature:
                FixtureCheckpointSigner.validShapeSignature()
        )

        let materialized = try await closure
            .materializeCheckpointSignature(using: signer)

        XCTAssertEqual(materialized.subject, expectedSubject)
        XCTAssertEqual(
            materialized.signatureInputSHA256,
            expectedSubject.signatureInputSHA256
        )
        XCTAssertEqual(
            materialized.document.subject.signedObjectSHA256,
            closure.checkpointRecord.recordSHA256
        )
        XCTAssertEqual(
            materialized.document.subject.ledgerID,
            closure.checkpointSource.ledgerID
        )
        XCTAssertEqual(
            materialized.document.subject
                .observerPublicKeyFingerprintSHA256,
            closure.document.observerIdentity
                .publicKeyFingerprintSHA256
        )
        XCTAssertNotEqual(
            materialized.document.canonicalBytes().last,
            0x0A
        )
    }

    func testMaterializerRejectsSignerIdentityBeforeSigning() async throws {
        let closure = try await makeMinimalClosure()
        let signer = FixtureCheckpointSigner(
            observerIdentity: try alternateObserverIdentity(),
            expectedDigest: Data(),
            returnedSignature:
                FixtureCheckpointSigner.validShapeSignature()
        )

        do {
            _ = try await closure.materializeCheckpointSignature(
                using: signer
            )
            XCTFail("Expected signer identity mismatch")
        } catch let error as
            DeviceCheckpointSignatureMaterializationError
        {
            XCTAssertEqual(
                error,
                .signerObserverIdentityMismatch
            )
        }
    }

    func testMaterializerRejectsInvalidSignerOutput() async throws {
        let closure = try await makeMinimalClosure()
        let subject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signer = FixtureCheckpointSigner(
            observerIdentity: try fixtureObserverIdentity(),
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature: Data(repeating: 0, count: 63)
        )

        do {
            _ = try await closure.materializeCheckpointSignature(
                using: signer
            )
            XCTFail("Expected invalid signer output")
        } catch let error as
            DeviceCheckpointSignatureMaterializationError
        {
            XCTAssertEqual(
                error,
                .signerReturnedInvalidSignature(
                    .signatureSizeInvalid
                )
            )
        }
    }

    func testSignerFailurePropagatesWithoutChangingClosure() async throws {
        let closure = try await makeMinimalClosure()
        let before = closure
        let subject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signer = FixtureCheckpointSigner(
            observerIdentity: try fixtureObserverIdentity(),
            expectedDigest: subject.signatureInputSHA256,
            returnedSignature:
                FixtureCheckpointSigner.validShapeSignature(),
            forceFailure: true
        )

        do {
            _ = try await closure.materializeCheckpointSignature(
                using: signer
            )
            XCTFail("Expected signer failure")
        } catch let error as FixtureCheckpointSignerError {
            XCTAssertEqual(error, .forcedFailure)
        }

        XCTAssertEqual(closure, before)
    }

    private func scalarOne() -> Data {
        var value = Data(repeating: 0, count: 32)
        value[31] = 1
        return value
    }

    private func signatureBytes(
        r: Data,
        s: Data
    ) -> Data {
        precondition(r.count == 32)
        precondition(s.count == 32)
        return r + s
    }

    private func curveOrder() -> Data {
        Data([
            0xFF, 0xFF, 0xFF, 0xFF,
            0x00, 0x00, 0x00, 0x00,
            0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF,
            0xBC, 0xE6, 0xFA, 0xAD,
            0xA7, 0x17, 0x9E, 0x84,
            0xF3, 0xB9, 0xCA, 0xC2,
            0xFC, 0x63, 0x25, 0x51,
        ])
    }

    private func halfOrderPlusOne() -> Data {
        Data([
            0x7F, 0xFF, 0xFF, 0xFF,
            0x80, 0x00, 0x00, 0x00,
            0x7F, 0xFF, 0xFF, 0xFF,
            0xFF, 0xFF, 0xFF, 0xFF,
            0xDE, 0x73, 0x7D, 0x56,
            0xD3, 0x8B, 0xCF, 0x42,
            0x79, 0xDC, 0xE5, 0x61,
            0x7E, 0x31, 0x92, 0xA9,
        ])
    }
}
