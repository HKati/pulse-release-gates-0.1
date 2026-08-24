import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NullLedgerBackendTests: XCTestCase {
    func testDeclaresNoPersistence() {
        let backend = NullLedgerBackend()

        XCTAssertEqual(backend.persistence, .none)
    }

    func testProtocolExistentialPreservesNoPersistenceContract() async throws {
        let backend: any LedgerBackend = NullLedgerBackend()

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertEqual(backend.persistence, .none)
        XCTAssertNil(loaded)
    }

    func testLoadAlwaysReturnsNoLedgerImage() async throws {
        let backend = NullLedgerBackend()

        let firstLoad = try await backend.loadLedgerBytes()
        let secondLoad = try await backend.loadLedgerBytes()

        XCTAssertNil(firstLoad)
        XCTAssertNil(secondLoad)
    }

    func testReplacingNonemptyBytesDoesNotRetainLedgerImage() async throws {
        let backend = NullLedgerBackend()
        let opaqueBytes = Data([
            0xEF,
            0xBB,
            0xBF,
            0x7B,
            0x7D,
            0x0D,
            0x0A,
            0x00,
            0xFF,
        ])

        try await backend.replaceLedgerBytes(opaqueBytes)
        let loaded = try await backend.loadLedgerBytes()

        XCTAssertNil(loaded)
    }

    func testReplacingEmptyBytesDoesNotCreateEmptyLedgerImage() async throws {
        let backend = NullLedgerBackend()

        try await backend.replaceLedgerBytes(Data())
        let loaded = try await backend.loadLedgerBytes()

        XCTAssertNil(loaded)
    }

    func testReplacementDoesNotMutateCallerOwnedBytes() async throws {
        let backend = NullLedgerBackend()
        let expected = Data([
            0x10,
            0x20,
            0x30,
            0x40,
        ])
        var callerBytes = expected

        try await backend.replaceLedgerBytes(callerBytes)

        XCTAssertEqual(callerBytes, expected)

        callerBytes[0] = 0xFF
        callerBytes.append(0xEE)

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertNil(loaded)
    }

    func testRemovalIsIdempotent() async throws {
        let backend = NullLedgerBackend()

        try await backend.removeLedgerBytes()
        let afterFirstRemoval = try await backend.loadLedgerBytes()

        try await backend.removeLedgerBytes()
        let afterSecondRemoval = try await backend.loadLedgerBytes()

        XCTAssertNil(afterFirstRemoval)
        XCTAssertNil(afterSecondRemoval)
    }

    func testRepeatedReplaceLoadAndRemoveCyclesRemainStateless() async throws {
        let backend = NullLedgerBackend()

        for marker in UInt8(0)..<UInt8(32) {
            try await backend.replaceLedgerBytes(
                Data([
                    marker,
                    0x00,
                    0xFF,
                ])
            )
            let afterReplacement = try await backend.loadLedgerBytes()

            XCTAssertNil(afterReplacement)

            try await backend.removeLedgerBytes()
            let afterRemoval = try await backend.loadLedgerBytes()

            XCTAssertNil(afterRemoval)
        }
    }
}
