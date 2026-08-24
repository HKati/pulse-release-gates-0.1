import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class LedgerRecordHasherTests: XCTestCase {
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

    private func firstReferenceSubject() throws -> LedgerRecordDigestSubject {
        let payload = object([
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

        return try LedgerRecordDigestSubject(
            ledgerID: identifier(
                "device-ledger:iphone-synthetic-reference-v0"
            ),
            observerPublicKeyFingerprintSHA256: observerFingerprint,
            payload: payload,
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

    func testStandardSHA256HexVectors() {
        let vectors: [(Data, String)] = [
            (
                Data(),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ),
            (
                Data("abc".utf8),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            ),
            (
                Data("hello world".utf8),
                "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
            ),
        ]

        for (input, expected) in vectors {
            XCTAssertEqual(
                LedgerRecordHasher.sha256Hex(
                    of: input
                ).rawValue,
                expected
            )
        }
    }

    func testRawSHA256BytesMatchABCVector() {
        let digest = LedgerRecordHasher.sha256Bytes(
            of: Data("abc".utf8)
        )

        XCTAssertEqual(
            digest,
            Data([
                0xBA, 0x78, 0x16, 0xBF,
                0x8F, 0x01, 0xCF, 0xEA,
                0x41, 0x41, 0x40, 0xDE,
                0x5D, 0xAE, 0x22, 0x23,
                0xB0, 0x03, 0x61, 0xA3,
                0x96, 0x17, 0x7A, 0x9C,
                0xB4, 0x10, 0xFF, 0x61,
                0xF2, 0x00, 0x15, 0xAD,
            ])
        )
        XCTAssertEqual(
            digest.count,
            32
        )
    }

    func testMillionAReferenceVector() {
        let input = Data(
            repeating: 0x61,
            count: 1_000_000
        )

        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: input
            ).rawValue,
            "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"
        )
    }

    func testExactByteIdentityDistinguishesTrailingNewline() {
        let canonical = Data("{}".utf8)
        let newlineTerminated = Data("{}\n".utf8)
        let canonicalDigest = LedgerRecordHasher.sha256Hex(
            of: canonical
        )
        let newlineDigest = LedgerRecordHasher.sha256Hex(
            of: newlineTerminated
        )

        XCTAssertEqual(
            canonicalDigest.rawValue,
            "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
        )
        XCTAssertEqual(
            newlineDigest.rawValue,
            "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"
        )
        XCTAssertNotEqual(
            canonicalDigest,
            newlineDigest
        )
    }

    func testFirstReferenceRecordDigestMatchesPythonProducer() throws {
        let subject = try firstReferenceSubject()
        let digest = LedgerRecordHasher.recordSHA256(
            for: subject
        )

        XCTAssertEqual(
            subject.canonicalBytes().count,
            1_412
        )
        XCTAssertEqual(
            digest.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
    }

    func testFinalizeAttachesOnlyTheCalculatedRecordDigest() throws {
        let subject = try firstReferenceSubject()
        let envelope = LedgerRecordHasher.finalize(
            subject
        )

        XCTAssertEqual(
            envelope.digestSubject,
            subject
        )
        XCTAssertEqual(
            envelope.recordSHA256.rawValue,
            "28176d2164cc5d543e1ce856bf1efad588004ff346375c3c30a6e4aad638ecb5"
        )
        XCTAssertEqual(
            envelope.canonicalBytes().count,
            1_495
        )
        XCTAssertEqual(
            envelope.reference.recordSHA256,
            envelope.recordSHA256
        )
        XCTAssertEqual(
            envelope.reference.sequenceIndex,
            0
        )
    }

    func testRepeatedHashingIsByteIdentical() throws {
        let subject = try firstReferenceSubject()
        let exactBytes = subject.canonicalBytes()
        let expectedRaw = LedgerRecordHasher.sha256Bytes(
            of: exactBytes
        )
        let expectedHex = LedgerRecordHasher.sha256Hex(
            of: exactBytes
        )

        for _ in 0..<100 {
            XCTAssertEqual(
                LedgerRecordHasher.sha256Bytes(
                    of: exactBytes
                ),
                expectedRaw
            )
            XCTAssertEqual(
                LedgerRecordHasher.sha256Hex(
                    of: exactBytes
                ),
                expectedHex
            )
        }
    }
}
