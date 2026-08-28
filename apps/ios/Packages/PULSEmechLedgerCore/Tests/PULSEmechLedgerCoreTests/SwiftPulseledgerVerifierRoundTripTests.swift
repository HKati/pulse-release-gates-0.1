import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class SwiftPulseledgerVerifierRoundTripTests: XCTestCase {
    private func referenceCarrier() async throws
        -> DevicePulseledgerCarrier
    {
        try await FixturePulseledgerCarrierFactory
            .makeReferenceMaterialization()
            .carrier
    }

    private func reportObject(
        _ bytes: Data
    ) throws -> [String: Any] {
        let value = try JSONSerialization.jsonObject(
            with: bytes,
            options: []
        )
        return try XCTUnwrap(value as? [String: Any])
    }

    private func object(
        _ value: Any?,
        _ key: String
    ) throws -> [String: Any] {
        try XCTUnwrap(
            value as? [String: Any],
            "Expected object at \(key)"
        )
    }

    private func array(
        _ value: Any?,
        _ key: String
    ) throws -> [Any] {
        try XCTUnwrap(
            value as? [Any],
            "Expected array at \(key)"
        )
    }

    func testSwiftCarrierProducesExactCanonicalStandaloneVerifierReport()
        async throws
    {
        let carrier = try await referenceCarrier()
        let expectedCarrier = try FixturePulseledgerCarrierFactory
            .referenceCarrierBytes()

        XCTAssertEqual(carrier.exactBytes, expectedCarrier)
        XCTAssertEqual(
            carrier.carrierSHA256,
            FixturePulseledgerCarrierFactory
                .referenceCarrierSHA256
        )

        let execution = try FixtureStandaloneDeviceLedgerVerifier.run(
            carrierBytes: carrier.exactBytes
        )
        let expectedReport = try FixtureStandaloneDeviceLedgerVerifier
            .referenceReportBytes()

        XCTAssertEqual(execution.terminationStatus, 0)
        XCTAssertTrue(execution.standardError.isEmpty)
        XCTAssertEqual(execution.standardOutput, expectedReport)
        XCTAssertEqual(execution.standardOutput.first, 0x7B)
        XCTAssertEqual(execution.standardOutput.last, 0x7D)
        XCTAssertNotEqual(execution.standardOutput.last, 0x0A)

        let report = try reportObject(
            execution.standardOutput
        )
        XCTAssertEqual(report["ok"] as? Bool, true)
        XCTAssertEqual(
            report["result"] as? String,
            "verified_with_declared_unavailability"
        )
        XCTAssertTrue(
            try array(
                report["errors"],
                "errors"
            ).isEmpty
        )
        XCTAssertTrue(
            try array(
                report["failed_check_ids"],
                "failed_check_ids"
            ).isEmpty
        )
        XCTAssertTrue(report["failure_stage"] is NSNull)

        let checks = try object(
            report["checks"],
            "checks"
        )
        XCTAssertEqual(checks.count, 49)
        XCTAssertTrue(
            checks.values.allSatisfy {
                ($0 as? String) == "passed"
            }
        )

        let subject = try object(
            report["subject"],
            "subject"
        )
        XCTAssertEqual(
            subject["carrier_file_name"] as? String,
            FixtureStandaloneDeviceLedgerVerifier
                .referenceCarrierFileName
        )
        XCTAssertEqual(
            subject["carrier_sha256"] as? String,
            carrier.carrierSHA256.rawValue
        )
        XCTAssertEqual(
            (subject["carrier_size_bytes"] as? NSNumber)?
                .int64Value,
            carrier.sizeBytes
        )
        XCTAssertEqual(
            subject["media_type"] as? String,
            DevicePulseledgerCarrier.mediaType
        )
        XCTAssertEqual(
            subject["package_format"] as? String,
            DevicePulseledgerCarrier.packageFormat
        )

        let authority = try object(
            report["authority_boundary"],
            "authority_boundary"
        )
        XCTAssertEqual(
            authority["authority_effect"] as? String,
            "none"
        )
        XCTAssertEqual(
            authority["verifier_report_is_release_authority"]
                as? Bool,
            false
        )

        let claimBoundary = try object(
            report["claim_boundary"],
            "claim_boundary"
        )
        XCTAssertEqual(
            claimBoundary["external_validation_claim"]
                as? String,
            "none"
        )

        let reproductionContext = try object(
            report["reproduction_context"],
            "reproduction_context"
        )
        XCTAssertEqual(
            reproductionContext[
                "verifier_implementation_relation"
            ] as? String,
            "separate_from_producer_code"
        )
        XCTAssertEqual(
            reproductionContext["external_validation_claim"]
                as? String,
            "none"
        )

        let tool = try object(
            report["tool"],
            "tool"
        )
        XCTAssertEqual(
            tool["id"] as? String,
            "verify_pulsemech_device_ledger_v0"
        )
        XCTAssertEqual(
            tool["producer_code_imported"] as? Bool,
            false
        )

        let signatures = try object(
            report["signature_verification"],
            "signature_verification"
        )
        let checkpoint = try object(
            signatures["checkpoint"],
            "signature_verification.checkpoint"
        )
        let package = try object(
            signatures["package"],
            "signature_verification.package"
        )
        XCTAssertEqual(
            checkpoint["signature_status"] as? String,
            "verified"
        )
        XCTAssertEqual(
            package["signature_status"] as? String,
            "verified"
        )
    }

    func testRepeatedStandaloneVerificationIsByteDeterministic()
        async throws
    {
        let carrier = try await referenceCarrier()

        let first = try FixtureStandaloneDeviceLedgerVerifier.run(
            carrierBytes: carrier.exactBytes
        )
        let second = try FixtureStandaloneDeviceLedgerVerifier.run(
            carrierBytes: carrier.exactBytes
        )

        XCTAssertEqual(first.terminationStatus, 0)
        XCTAssertEqual(second.terminationStatus, 0)
        XCTAssertTrue(first.standardError.isEmpty)
        XCTAssertTrue(second.standardError.isEmpty)
        XCTAssertEqual(first.standardOutput, second.standardOutput)
        XCTAssertEqual(
            first.standardOutput,
            try FixtureStandaloneDeviceLedgerVerifier
                .referenceReportBytes()
        )
    }

    func testSameStandaloneVerifierRejectsCRCConsistentSignatureTamper()
        async throws
    {
        let carrier = try await referenceCarrier()
        let originalBytes = carrier.exactBytes
        let tamperedBytes = try FixtureStandaloneDeviceLedgerVerifier
            .crcConsistentPackageSignatureTamper(
                originalBytes
            )

        XCTAssertEqual(tamperedBytes.count, originalBytes.count)
        XCTAssertNotEqual(tamperedBytes, originalBytes)
        XCTAssertEqual(carrier.exactBytes, originalBytes)

        let tamperedSHA256 = LedgerRecordHasher.sha256Hex(
            of: tamperedBytes
        )
        XCTAssertNotEqual(
            tamperedSHA256,
            carrier.carrierSHA256
        )

        let execution = try FixtureStandaloneDeviceLedgerVerifier.run(
            carrierBytes: tamperedBytes
        )

        XCTAssertEqual(execution.terminationStatus, 2)
        XCTAssertTrue(execution.standardError.isEmpty)
        XCTAssertEqual(execution.standardOutput.first, 0x7B)
        XCTAssertEqual(execution.standardOutput.last, 0x7D)
        XCTAssertNotEqual(execution.standardOutput.last, 0x0A)
        XCTAssertNotEqual(
            execution.standardOutput,
            try FixtureStandaloneDeviceLedgerVerifier
                .referenceReportBytes()
        )

        let report = try reportObject(
            execution.standardOutput
        )
        XCTAssertEqual(report["ok"] as? Bool, false)
        XCTAssertEqual(
            report["result"] as? String,
            "rejected"
        )
        XCTAssertEqual(
            report["failure_stage"] as? String,
            "package_signature"
        )
        XCTAssertEqual(
            try array(
                report["failed_check_ids"],
                "failed_check_ids"
            ) as? [String],
            ["package_signature_valid"]
        )

        let errors = try array(
            report["errors"],
            "errors"
        )
        XCTAssertEqual(errors.count, 1)
        let error = try object(
            errors.first,
            "errors[0]"
        )
        XCTAssertEqual(
            error["stage"] as? String,
            "package_signature"
        )
        XCTAssertEqual(
            error["check_id"] as? String,
            "package_signature_valid"
        )
        XCTAssertEqual(
            error["error_code"] as? String,
            "signature_verification_failed"
        )
        XCTAssertEqual(
            error["member_path"] as? String,
            DeviceLedgerManifest.packageSignaturePath
        )

        let checks = try object(
            report["checks"],
            "checks"
        )
        XCTAssertEqual(
            checks["zip_crc32_valid"] as? String,
            "passed"
        )
        XCTAssertEqual(
            checks["package_signature_document_valid"]
                as? String,
            "passed"
        )
        XCTAssertEqual(
            checks["package_signature_subject_valid"]
                as? String,
            "passed"
        )
        XCTAssertEqual(
            checks["package_signature_valid"] as? String,
            "failed"
        )

        let subject = try object(
            report["subject"],
            "subject"
        )
        XCTAssertEqual(
            subject["carrier_sha256"] as? String,
            tamperedSHA256.rawValue
        )
        XCTAssertEqual(
            (subject["carrier_size_bytes"] as? NSNumber)?
                .int64Value,
            Int64(tamperedBytes.count)
        )

        let authority = try object(
            report["authority_boundary"],
            "authority_boundary"
        )
        XCTAssertEqual(
            authority["authority_effect"] as? String,
            "none"
        )
        let claimBoundary = try object(
            report["claim_boundary"],
            "claim_boundary"
        )
        XCTAssertEqual(
            claimBoundary["external_validation_claim"]
                as? String,
            "none"
        )
    }
}
