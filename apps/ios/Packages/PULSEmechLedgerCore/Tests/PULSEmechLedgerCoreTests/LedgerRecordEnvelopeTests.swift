import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class LedgerRecordEnvelopeTests: XCTestCase {
    private let zeroDigest = try! SHA256HexDigest(
        String(repeating: "0", count: 64)
    )
    private let oneDigest = try! SHA256HexDigest(
        String(repeating: "1", count: 64)
    )
    private let observerFingerprint = try! SHA256HexDigest(
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"
    )

    private func identifier(
        _ rawValue: String
    ) -> LedgerIdentifier {
        try! LedgerIdentifier(rawValue)
    }

    private func string(
        _ value: String
    ) -> CanonicalJSONValue {
        try! .string(value)
    }

    private func member(
        _ key: String,
        _ value: CanonicalJSONValue
    ) -> CanonicalJSONObjectMember {
        try! CanonicalJSONObjectMember(
            key: key,
            value: value
        )
    }

    private func object(
        _ members: [CanonicalJSONObjectMember]
    ) -> CanonicalJSONValue {
        try! .object(members)
    }

    private func minimalPayload(
        type: String,
        transitionClass: CanonicalJSONValue? = nil
    ) -> CanonicalJSONValue {
        var members = [
            member(
                "payload_type",
                string(type)
            ),
        ]

        if let transitionClass {
            members.append(
                member(
                    "transition_class",
                    transitionClass
                )
            )
        }

        return object(members)
    }

    private func sessionScope(
        monotonicTimeNS: Int64 = 1_000
    ) -> LedgerRecordScope {
        .session(
            sessionID: identifier("session:test"),
            clockEpochID: identifier("clock-epoch:test"),
            monotonicTimeNS: monotonicTimeNS
        )
    }

    private func makeSubject(
        payload: CanonicalJSONValue? = nil,
        previousRecordSHA256: SHA256HexDigest? = nil,
        recordStatus: LedgerRecordStatus = .observed,
        recordType: LedgerRecordType = .sessionBoundary,
        recordedWallTimeUnixNS: Int64 = 1,
        sequenceIndex: Int64 = 0,
        scope: LedgerRecordScope? = nil
    ) throws -> LedgerRecordDigestSubject {
        try LedgerRecordDigestSubject(
            ledgerID: identifier("device-ledger:test"),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            payload: payload ?? minimalPayload(type: recordType.rawValue),
            previousRecordSHA256: previousRecordSHA256,
            recordID: identifier("record:test"),
            recordStatus: recordStatus,
            recordType: recordType,
            recordedWallTimeUnixNS: recordedWallTimeUnixNS,
            sequenceIndex: sequenceIndex,
            scope: scope ?? sessionScope()
        )
    }

    private func firstReferencePayload() -> CanonicalJSONValue {
        object([
            member(
                "boundary_id",
                string("boundary:open-a")
            ),
            member(
                "boundary_kind",
                string("opened")
            ),
            member(
                "duplicate_boundary_rule",
                string("not_applicable_new_session")
            ),
            member(
                "lifecycle_event",
                string("scene_did_become_active")
            ),
            member(
                "network_surface_after_boundary",
                string("unavailable_until_fresh_path_update")
            ),
            member(
                "observation_window_state",
                string("open")
            ),
            member(
                "payload_type",
                string("session_boundary")
            ),
            member(
                "previous_session_id",
                .null
            ),
            member(
                "session_terminal",
                .boolean(false)
            ),
        ])
    }

    private func firstReferenceSubject() throws -> LedgerRecordDigestSubject {
        try LedgerRecordDigestSubject(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            payload: firstReferencePayload(),
            previousRecordSHA256: nil,
            recordID: identifier(
                "record:000-session-open-a"
            ),
            recordStatus: .syntheticReference,
            recordType: .sessionBoundary,
            recordedWallTimeUnixNS: 1_700_000_000_000_000_000,
            sequenceIndex: 0,
            scope: .session(
                sessionID: identifier(
                    "session:synthetic-a"
                ),
                clockEpochID: identifier(
                    "clock-epoch:synthetic-a"
                ),
                monotonicTimeNS: 1_000
            )
        )
    }

    func testLedgerIdentifierAcceptsExactAlphabetAndLengthBounds() throws {
        let alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:/+-"
        let maximum = String(repeating: "a", count: 256)

        XCTAssertEqual(
            try LedgerIdentifier(alphabet).rawValue,
            alphabet
        )
        XCTAssertEqual(
            try LedgerIdentifier("a").rawValue,
            "a"
        )
        XCTAssertEqual(
            try LedgerIdentifier(maximum).rawValue,
            maximum
        )
    }

    func testLedgerIdentifierRejectsEmptyOversizedAndForbiddenValues() {
        XCTAssertThrowsError(
            try LedgerIdentifier("")
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .identifierLengthOutOfRange
            )
        }

        XCTAssertThrowsError(
            try LedgerIdentifier(
                String(repeating: "a", count: 257)
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .identifierLengthOutOfRange
            )
        }

        XCTAssertThrowsError(
            try LedgerIdentifier("not allowed")
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .identifierContainsForbiddenByte(0x20)
            )
        }

        XCTAssertThrowsError(
            try LedgerIdentifier("é")
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .identifierContainsForbiddenByte(0xC3)
            )
        }
    }

    func testSHA256DigestAcceptsOnlyLowercaseHex() throws {
        let valid = "0123456789abcdef" + String(
            repeating: "0",
            count: 48
        )

        XCTAssertEqual(
            try SHA256HexDigest(valid).rawValue,
            valid
        )

        for invalid in [
            String(repeating: "0", count: 63),
            String(repeating: "0", count: 65),
            String(repeating: "A", count: 64),
            String(repeating: "g", count: 64),
        ] {
            XCTAssertThrowsError(
                try SHA256HexDigest(invalid)
            ) { error in
                XCTAssertEqual(
                    error as? LedgerRecordEnvelopeError,
                    .sha256DigestMustBeLowercaseHex
                )
            }
        }
    }

    func testFirstAndLaterRecordPreviousDigestRules() throws {
        XCTAssertNoThrow(
            try makeSubject(
                previousRecordSHA256: nil,
                sequenceIndex: 0
            )
        )

        XCTAssertThrowsError(
            try makeSubject(
                previousRecordSHA256: zeroDigest,
                sequenceIndex: 0
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .firstRecordRequiresNoPreviousDigest
            )
        }

        XCTAssertNoThrow(
            try makeSubject(
                previousRecordSHA256: zeroDigest,
                sequenceIndex: 1
            )
        )

        XCTAssertThrowsError(
            try makeSubject(
                previousRecordSHA256: nil,
                sequenceIndex: 1
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .nonFirstRecordRequiresPreviousDigest
            )
        }
    }

    func testNegativeSequenceWallAndMonotonicTimesAreRejected() {
        XCTAssertThrowsError(
            try makeSubject(
                sequenceIndex: -1
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .negativeSequenceIndex
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                recordedWallTimeUnixNS: -1
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .negativeRecordedWallTime
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                scope: sessionScope(
                    monotonicTimeNS: -1
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .negativeMonotonicTime
            )
        }
    }

    func testPayloadMustBeObjectWithMatchingStringPayloadType() {
        XCTAssertThrowsError(
            try makeSubject(
                payload: .null
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .payloadMustBeObject
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                payload: object([
                    member(
                        "other",
                        .null
                    ),
                ])
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .payloadTypeMissing
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                payload: object([
                    member(
                        "payload_type",
                        .integer(1)
                    ),
                ])
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .payloadTypeMustBeString
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                payload: minimalPayload(
                    type: "state_snapshot"
                )
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .payloadTypeMismatch(
                    expected: "session_boundary",
                    actual: "state_snapshot"
                )
            )
        }
    }

    func testNonTransitionRecordScopesAreClosed() throws {
        for recordType in [
            LedgerRecordType.sessionBoundary,
            .stateSnapshot,
            .observationEvent,
        ] {
            XCTAssertNoThrow(
                try makeSubject(
                    recordType: recordType,
                    scope: sessionScope()
                )
            )
            XCTAssertThrowsError(
                try makeSubject(
                    recordType: recordType,
                    scope: .ledgerWide
                )
            ) { error in
                XCTAssertEqual(
                    error as? LedgerRecordEnvelopeError,
                    .scopeMismatch(recordType)
                )
            }
        }

        for recordType in [
            LedgerRecordType.coverageInterval,
            .checkpoint,
        ] {
            XCTAssertNoThrow(
                try makeSubject(
                    recordType: recordType,
                    scope: .ledgerWide
                )
            )
            XCTAssertThrowsError(
                try makeSubject(
                    recordType: recordType,
                    scope: sessionScope()
                )
            ) { error in
                XCTAssertEqual(
                    error as? LedgerRecordEnvelopeError,
                    .scopeMismatch(recordType)
                )
            }
        }
    }

    func testTransitionRequiresStringSupportedClass() {
        XCTAssertThrowsError(
            try makeSubject(
                payload: minimalPayload(
                    type: "transition"
                ),
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: sessionScope()
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .transitionClassMissing
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                payload: minimalPayload(
                    type: "transition",
                    transitionClass: .integer(1)
                ),
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: sessionScope()
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .transitionClassMustBeString
            )
        }

        XCTAssertThrowsError(
            try makeSubject(
                payload: minimalPayload(
                    type: "transition",
                    transitionClass: string("future")
                ),
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: sessionScope()
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .unsupportedTransitionClass("future")
            )
        }
    }

    func testTransitionClassDeterminesScope() throws {
        let eventBound = minimalPayload(
            type: "transition",
            transitionClass: string("event_bound")
        )
        let endpointDifference = minimalPayload(
            type: "transition",
            transitionClass: string("endpoint_difference_only")
        )

        XCTAssertNoThrow(
            try makeSubject(
                payload: eventBound,
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: sessionScope()
            )
        )
        XCTAssertThrowsError(
            try makeSubject(
                payload: eventBound,
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: .ledgerWide
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .transitionClassScopeMismatch("event_bound")
            )
        }

        XCTAssertNoThrow(
            try makeSubject(
                payload: endpointDifference,
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: .ledgerWide
            )
        )
        XCTAssertThrowsError(
            try makeSubject(
                payload: endpointDifference,
                previousRecordSHA256: zeroDigest,
                recordType: .transition,
                sequenceIndex: 1,
                scope: sessionScope()
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .transitionClassScopeMismatch(
                    "endpoint_difference_only"
                )
            )
        }
    }

    func testLedgerWideScopeSerializesNullScopeFields() throws {
        let subject = try makeSubject(
            previousRecordSHA256: zeroDigest,
            recordType: .coverageInterval,
            sequenceIndex: 1,
            scope: .ledgerWide
        )
        let text = try XCTUnwrap(
            String(
                data: subject.canonicalBytes(),
                encoding: .utf8
            )
        )

        XCTAssertTrue(
            text.contains(#""clock_epoch_id":null"#)
        )
        XCTAssertTrue(
            text.contains(#""monotonic_time_ns":null"#)
        )
        XCTAssertTrue(
            text.contains(#""session_id":null"#)
        )
    }

    func testFirstReferenceDigestSubjectMatchesExactProducerBytes() throws {
        let subject = try firstReferenceSubject()
        let expected =
            #"{"authority_effect":"none","canonicalization_profile_sha256":"ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550","claim_boundary":{"causal_completion_claim":"none","continuous_monitoring_claim":"none","device_security_claim":"none","malware_claim":"none","physical_measurement_claim":"none","release_authority_effect":"none","system_wide_network_claim":"none"},"clock_epoch_id":"clock-epoch:synthetic-a","document_type":"pulsemech_device_ledger_record","ledger_id":"device-ledger:iphone-synthetic-reference-v0","monotonic_time_ns":1000,"observation_contract_sha256":"e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","payload":{"boundary_id":"boundary:open-a","boundary_kind":"opened","duplicate_boundary_rule":"not_applicable_new_session","lifecycle_event":"scene_did_become_active","network_surface_after_boundary":"unavailable_until_fresh_path_update","observation_window_state":"open","payload_type":"session_boundary","previous_session_id":null,"session_terminal":false},"previous_record_sha256":null,"record_id":"record:000-session-open-a","record_status":"synthetic_reference","record_type":"session_boundary","recorded_wall_time_unix_ns":1700000000000000000,"schema_version":"pulsemech_device_ledger_record_v0","sequence_index":0,"session_id":"session:synthetic-a"}"#
        let bytes = subject.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            1_412
        )
        XCTAssertFalse(
            expected.contains(#""record_sha256""#)
        )
    }

    func testFinalizedFirstReferenceRecordMatchesExactStoredBytes() throws {
        let digest = try SHA256HexDigest(
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        let envelope = try firstReferenceSubject().finalized(
            recordSHA256: digest
        )
        let expected =
            #"{"authority_effect":"none","canonicalization_profile_sha256":"ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550","claim_boundary":{"causal_completion_claim":"none","continuous_monitoring_claim":"none","device_security_claim":"none","malware_claim":"none","physical_measurement_claim":"none","release_authority_effect":"none","system_wide_network_claim":"none"},"clock_epoch_id":"clock-epoch:synthetic-a","document_type":"pulsemech_device_ledger_record","ledger_id":"device-ledger:iphone-synthetic-reference-v0","monotonic_time_ns":1000,"observation_contract_sha256":"e537fa04a7fb9e84292a2275e2818cb2012a66867bcd09d3ad3a8ff6cb7767c2","observer_public_key_fingerprint_sha256":"f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6","payload":{"boundary_id":"boundary:open-a","boundary_kind":"opened","duplicate_boundary_rule":"not_applicable_new_session","lifecycle_event":"scene_did_become_active","network_surface_after_boundary":"unavailable_until_fresh_path_update","observation_window_state":"open","payload_type":"session_boundary","previous_session_id":null,"session_terminal":false},"previous_record_sha256":null,"record_id":"record:000-session-open-a","record_sha256":"28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5","record_status":"synthetic_reference","record_type":"session_boundary","recorded_wall_time_unix_ns":1700000000000000000,"schema_version":"pulsemech_device_ledger_record_v0","sequence_index":0,"session_id":"session:synthetic-a"}"#
        let bytes = envelope.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            1_495
        )
        XCTAssertEqual(
            envelope.recordSHA256,
            digest
        )
    }

    func testRecordReferenceMatchesExactThreeFieldObject() throws {
        let envelope = try firstReferenceSubject().finalized(
            recordSHA256: oneDigest
        )
        let reference = envelope.reference

        XCTAssertEqual(
            reference.recordID.rawValue,
            "record:000-session-open-a"
        )
        XCTAssertEqual(
            reference.recordSHA256,
            oneDigest
        )
        XCTAssertEqual(
            reference.sequenceIndex,
            0
        )
        XCTAssertEqual(
            reference.canonicalBytes(),
            Data(
                #"{"record_id":"record:000-session-open-a","record_sha256":"1111111111111111111111111111111111111111111111111111111111111111","sequence_index":0}"#.utf8
            )
        )
    }

    func testRecordReferenceRejectsNegativeSequenceIndex() {
        XCTAssertThrowsError(
            try LedgerRecordReference(
                recordID: identifier("record:test"),
                recordSHA256: zeroDigest,
                sequenceIndex: -1
            )
        ) { error in
            XCTAssertEqual(
                error as? LedgerRecordEnvelopeError,
                .negativeSequenceIndex
            )
        }
    }

    func testRepeatedSubjectAndEnvelopeEncodingIsByteIdentical() throws {
        let subject = try firstReferenceSubject()
        let envelope = subject.finalized(
            recordSHA256: oneDigest
        )
        let subjectBytes = subject.canonicalBytes()
        let envelopeBytes = envelope.canonicalBytes()

        for _ in 0..<100 {
            XCTAssertEqual(
                subject.canonicalBytes(),
                subjectBytes
            )
            XCTAssertEqual(
                envelope.canonicalBytes(),
                envelopeBytes
            )
        }
    }
}
