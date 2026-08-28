import XCTest
@testable import PULSEmechProofApp

final class PULSEmechProofAppTests: XCTestCase {
    func testReferenceRunClosesExactBoundedProof()
        async throws
    {
        let result = try await BoundedReferenceProofRunner.run()

        XCTAssertEqual(result.recordCount, 14)
        XCTAssertEqual(result.sessionCount, 2)
        XCTAssertEqual(result.clockEpochCount, 2)
        XCTAssertEqual(result.sessionBoundaryCount, 3)

        XCTAssertEqual(result.continuousCoverageCount, 1)
        XCTAssertEqual(result.interruptedCoverageCount, 1)
        XCTAssertEqual(result.eventBoundTransitionCount, 1)
        XCTAssertEqual(
            result.endpointDifferenceOnlyTransitionCount,
            1
        )

        XCTAssertEqual(
            result.checkpointSHA256,
            BoundedReferenceProofRunner
                .expectedCheckpointSHA256
        )
        XCTAssertEqual(
            result.ledgerSHA256,
            BoundedReferenceProofRunner
                .expectedLedgerSHA256
        )
        XCTAssertEqual(
            result.manifestSHA256,
            BoundedReferenceProofRunner
                .expectedManifestSHA256
        )
        XCTAssertEqual(
            result.carrierSHA256,
            BoundedReferenceProofRunner
                .expectedCarrierSHA256
        )
        XCTAssertEqual(
            result.carrierSizeBytes,
            BoundedReferenceProofRunner
                .expectedCarrierSizeBytes
        )
        XCTAssertEqual(
            result.carrierBytes.count,
            Int(
                BoundedReferenceProofRunner
                    .expectedCarrierSizeBytes
            )
        )
    }

    func testVerifierResultBindsTheSameExactCarrier()
        async throws
    {
        let result = try await BoundedReferenceProofRunner.run()

        XCTAssertEqual(
            result.verifierResult,
            "verified_with_declared_unavailability"
        )
        XCTAssertEqual(result.verifierCheckCount, 49)
        XCTAssertTrue(
            result.verifierCarrierBindingMatches
        )
        XCTAssertEqual(
            result.verifierCarrierSHA256,
            result.carrierSHA256
        )
        XCTAssertEqual(
            result.verifierImplementationRelation,
            "separate_from_producer_code"
        )
        XCTAssertFalse(
            result.producerCodeImportedByVerifier
        )
        XCTAssertEqual(
            result.checkpointSignatureStatus,
            "verified"
        )
        XCTAssertEqual(
            result.packageSignatureStatus,
            "verified"
        )
    }

    func testDemonstratorPreservesClaimAndAuthorityBoundary()
        async throws
    {
        let result = try await BoundedReferenceProofRunner.run()

        XCTAssertEqual(
            result.observerIdentityScope,
            "fixture_installation"
        )
        XCTAssertEqual(
            result.observerKeyOriginProfile,
            "fixture_software_p256"
        )
        XCTAssertTrue(
            result.declaredUnavailabilityPresent
        )
        XCTAssertEqual(
            result.authorityEffect,
            "none"
        )
        XCTAssertEqual(
            result.externalValidationClaim,
            "none"
        )
        XCTAssertEqual(
            result.carrierFileName,
            BoundedReferenceProofRunner
                .carrierFileName
        )
    }
}
