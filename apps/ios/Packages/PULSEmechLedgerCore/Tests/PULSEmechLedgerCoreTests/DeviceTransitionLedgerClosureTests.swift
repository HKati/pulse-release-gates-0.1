import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class DeviceTransitionLedgerClosureTests: XCTestCase {
    private let baseWallTime: Int64 = 1_700_000_000_000_000_000
    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
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

    private func fixtureObserverIdentity() throws -> DeviceLedgerObserverIdentity {
        try DeviceLedgerObserverIdentity(
            identityScope: .fixtureInstallation,
            keyOriginProfile: .fixtureSoftwareP256,
            publicKeyX963Uncompressed: fixturePublicKey()
        )
    }

    private func makeChain() -> LedgerRecordChain {
        LedgerRecordChain(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            recordStatus: .syntheticReference
        )
    }

    @discardableResult
    private func appendOpening(
        to chain: LedgerRecordChain
    ) async throws -> LedgerRecordEnvelope {
        let payload = SessionBoundaryPayload.opened(
            boundaryID: identifier("boundary:open-a"),
            previousSessionID: nil
        )
        let draft = try payload.recordDraft(
            recordID: identifier("record:000-session-open-a"),
            recordedWallTimeUnixNS: baseWallTime,
            sessionID: identifier("session:synthetic-a"),
            clockEpochID: identifier("clock-epoch:synthetic-a"),
            monotonicTimeNS: 1_000
        )
        return try await chain.append(draft)
    }

    private func checkpointInput() -> LedgerCheckpointMaterializationInput {
        LedgerCheckpointMaterializationInput(
            checkpointID: identifier("checkpoint:minimal-v0"),
            recordID: identifier("record:001-checkpoint"),
            recordedWallTimeUnixNS: baseWallTime + 1_000_000
        )
    }

    func testObserverIdentityMatchesExactReferenceBytes() throws {
        let identity = try fixtureObserverIdentity()
        let expected = Data(
            #"{"device_class":"iphone","identity_scope":"fixture_installation","key_origin_profile":"fixture_software_p256","platform":"ios","platform_attestation_status":"not_present","public_key_base64":"BAIa75uP4gO+twVlypJYAjIKXK0JVnBPBArgoE50sEI+HbKkjFpxpQifk3hgoQs08yYzY850htpv1wl0/4u6i10=","public_key_encoding":"x963_uncompressed","public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","public_key_size_bytes":65,"signature_encoding":"ieee_p1363_fixed_width","signature_suite":"ecdsa-p256-sha256"}"#.utf8
        )
        let observed = CanonicalJSONEncoder.encode(identity.canonicalValue())

        XCTAssertEqual(observed, expected)
        XCTAssertEqual(observed.count, 534)
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(of: observed).rawValue,
            "88b8e8da3bd26d1a6dc15f1967dad307376058803b19a46982ca45285a42bd2d"
        )
        XCTAssertEqual(
            identity.publicKeyFingerprintSHA256,
            observerFingerprint
        )
        XCTAssertNotEqual(observed.last, 0x0A)
    }

    func testObserverIdentityRejectsInvalidShapeAndProfile() throws {
        XCTAssertThrowsError(
            try DeviceLedgerObserverIdentity(
                identityScope: .fixtureInstallation,
                keyOriginProfile: .fixtureSoftwareP256,
                publicKeyX963Uncompressed: Data(repeating: 0, count: 64)
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceTransitionLedgerDocumentError,
                .observerPublicKeySizeInvalid
            )
        }

        XCTAssertThrowsError(
            try DeviceLedgerObserverIdentity(
                identityScope: .installation,
                keyOriginProfile: .softwareP256,
                publicKeyX963Uncompressed: Data(
                    [UInt8(0x04)] + [UInt8](repeating: 0, count: 64)
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceTransitionLedgerDocumentError,
                .observerPublicKeyCurveInvalid
            )
        }

        XCTAssertNoThrow(
            try DeviceLedgerObserverIdentity(
                identityScope: .installation,
                keyOriginProfile: .softwareP256,
                publicKeyX963Uncompressed: Data(
                    base64Encoded:
                        "BHzyexiNA09+ilI4AwS1GsPAiWnid/IbNaYLSPxHZpl4B3dVENuO0EApPZrGn3Qw27p9reY86YIpngS3nSJ4c9E="
                )!
            )
        )

        XCTAssertThrowsError(
            try DeviceLedgerObserverIdentity(
                identityScope: .installation,
                keyOriginProfile: .fixtureSoftwareP256,
                publicKeyX963Uncompressed: fixturePublicKey()
            )
        ) { error in
            XCTAssertEqual(
                error as? DeviceTransitionLedgerDocumentError,
                .observerIdentityProfileMismatch
            )
        }
    }

    func testMinimalChainClosureDerivesCheckpointAndDocument() async throws {
        let chain = makeChain()
        let opening = try await appendOpening(to: chain)
        let closure = try await chain.closeAndMaterializeLedger(
            checkpointInput(),
            observerIdentity: fixtureObserverIdentity()
        )

        XCTAssertEqual(closure.checkpointSource.closedRecordCount, 1)
        XCTAssertEqual(closure.checkpointSource.firstRecord, opening.reference)
        XCTAssertEqual(
            closure.checkpointSource.terminalRecord,
            opening.reference
        )
        XCTAssertEqual(closure.checkpointSource.sessionCount, 1)
        XCTAssertEqual(closure.checkpointSource.clockEpochCount, 1)
        XCTAssertEqual(
            closure.checkpointSource.recordTypeCounts,
            LedgerCheckpointRecordTypeCounts(
                coverageInterval: 0,
                observationEvent: 0,
                sessionBoundary: 1,
                stateSnapshot: 0,
                transition: 0
            )
        )
        XCTAssertEqual(
            closure.checkpointSource.coverageSummary,
            LedgerCheckpointCoverageSummary(
                continuousIntervals: 0,
                interruptedIntervals: 0
            )
        )
        XCTAssertEqual(
            closure.checkpointSource.transitionSummary,
            LedgerCheckpointTransitionSummary(
                endpointDifferenceOnly: 0,
                eventBound: 0
            )
        )

        XCTAssertEqual(
            closure.checkpointRecord.digestSubject.sequenceIndex,
            1
        )
        XCTAssertEqual(
            closure.checkpointRecord.digestSubject.previousRecordSHA256,
            opening.recordSHA256
        )
        XCTAssertEqual(
            closure.checkpointRecord.digestSubject.payload,
            closure.checkpointPayload.canonicalValue()
        )
        XCTAssertEqual(closure.document.records.count, 2)
        XCTAssertEqual(
            closure.document.records.last,
            closure.checkpointRecord
        )
        XCTAssertNotEqual(
            closure.document.canonicalBytes().last,
            0x0A
        )

        let snapshot = await chain.snapshot()
        XCTAssertEqual(snapshot.state, .checkpointed)
        XCTAssertEqual(snapshot.recordCount, 2)
        XCTAssertNil(snapshot.nextSequenceIndex)
    }

    func testObserverMismatchRollsBackCheckpointAndKeepsIDReusable() async throws {
        let chain = makeChain()
        try await appendOpening(to: chain)
        let before = await chain.snapshot()

        let wrongIdentity = try DeviceLedgerObserverIdentity(
            identityScope: .installation,
            keyOriginProfile: .softwareP256,
            publicKeyX963Uncompressed: Data(
                base64Encoded:
                    "BHzyexiNA09+ilI4AwS1GsPAiWnid/IbNaYLSPxHZpl4B3dVENuO0EApPZrGn3Qw27p9reY86YIpngS3nSJ4c9E="
            )!
        )

        do {
            _ = try await chain.closeAndMaterializeLedger(
                checkpointInput(),
                observerIdentity: wrongIdentity
            )
            XCTFail("Expected observer mismatch to fail")
        } catch let error as DeviceTransitionLedgerDocumentError {
            XCTAssertEqual(error, .observerFingerprintMismatch)
        }

        let afterFailure = await chain.snapshot()
        XCTAssertEqual(afterFailure, before)

        let accepted = try await chain.closeAndMaterializeLedger(
            checkpointInput(),
            observerIdentity: fixtureObserverIdentity()
        )
        XCTAssertEqual(
            accepted.checkpointRecord.digestSubject.recordID,
            checkpointInput().recordID
        )
    }

    func testCheckpointSourceRejectsCheckpointedRecordSet() async throws {
        let chain = makeChain()
        try await appendOpening(to: chain)
        _ = try await chain.closeAndMaterializeLedger(
            checkpointInput(),
            observerIdentity: fixtureObserverIdentity()
        )
        let snapshot = await chain.snapshot()

        XCTAssertThrowsError(
            try LedgerCheckpointSource(
                ledgerID: snapshot.ledgerID,
                observerPublicKeyFingerprintSHA256:
                    snapshot.observerPublicKeyFingerprintSHA256,
                recordStatus: snapshot.recordStatus,
                records: snapshot.records
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerCheckpointPayloadError,
                .checkpointAlreadyPresent
            )
        }
    }
}
