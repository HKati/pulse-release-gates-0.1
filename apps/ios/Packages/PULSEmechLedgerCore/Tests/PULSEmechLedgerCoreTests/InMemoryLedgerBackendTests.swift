import Foundation
import XCTest
@testable import PULSEmechLedgerCore

@MainActor
final class InMemoryLedgerBackendTests: XCTestCase {
    func testDeclaresProcessLifetimePersistence() {
        let backend = InMemoryLedgerBackend()

        XCTAssertEqual(backend.persistence, .processLifetime)
    }

    func testDefaultInitializationRetainsNoLedgerImage() async throws {
        let backend = InMemoryLedgerBackend()

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertNil(loaded)
    }

    func testEmptyLedgerImageRemainsDistinctFromNoLedgerImage() async throws {
        let backend = InMemoryLedgerBackend(initialLedgerBytes: Data())

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertNotNil(loaded)
        XCTAssertEqual(loaded, Data())
    }

    func testInitializationRetainsExactOpaqueBytes() async throws {
        let expected = Data([
            0x00,
            0x7B,
            0x22,
            0x5C,
            0x0A,
            0xFF,
        ])
        let backend = InMemoryLedgerBackend(initialLedgerBytes: expected)

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertEqual(loaded, expected)
    }

    func testReplacementPreservesExactBytesWithoutInterpretation() async throws {
        let backend = InMemoryLedgerBackend(
            initialLedgerBytes: Data([0x01])
        )
        let replacement = Data([
            0xEF,
            0xBB,
            0xBF,
            0x7B,
            0x7D,
            0x0D,
            0x0A,
            0x00,
        ])

        try await backend.replaceLedgerBytes(replacement)
        let loaded = try await backend.loadLedgerBytes()

        XCTAssertEqual(loaded, replacement)
    }

    func testReplacementDoesNotShareMutableCallerState() async throws {
        let backend = InMemoryLedgerBackend()
        let expected = Data([
            0x10,
            0x20,
            0x30,
            0x40,
        ])
        var callerBytes = expected

        try await backend.replaceLedgerBytes(callerBytes)

        callerBytes[0] = 0xFF
        callerBytes.append(0xEE)

        let loaded = try await backend.loadLedgerBytes()

        XCTAssertEqual(loaded, expected)
    }

    func testLoadedSnapshotDoesNotShareMutableBackendState() async throws {
        let expected = Data([
            0xAA,
            0xBB,
            0xCC,
            0xDD,
        ])
        let backend = InMemoryLedgerBackend(
            initialLedgerBytes: expected
        )

        let firstLoad = try await backend.loadLedgerBytes()
        var callerSnapshot = try XCTUnwrap(firstLoad)

        callerSnapshot[0] = 0x00
        callerSnapshot.removeLast()

        let secondLoad = try await backend.loadLedgerBytes()

        XCTAssertEqual(secondLoad, expected)
    }

    func testReplacementExposesOnlyTheCompleteNewImage() async throws {
        let initial = Data(
            repeating: 0x11,
            count: 4_096
        )
        let replacement = Data(
            repeating: 0xEE,
            count: 8_192
        )
        let backend = InMemoryLedgerBackend(
            initialLedgerBytes: initial
        )

        let before = try await backend.loadLedgerBytes()

        try await backend.replaceLedgerBytes(replacement)

        let after = try await backend.loadLedgerBytes()

        XCTAssertEqual(before, initial)
        XCTAssertEqual(after, replacement)
    }

    func testRemovalIsIdempotentAndRestoresNoImageState() async throws {
        let backend = InMemoryLedgerBackend(
            initialLedgerBytes: Data([
                0x01,
                0x02,
            ])
        )

        try await backend.removeLedgerBytes()
        let afterFirstRemoval = try await backend.loadLedgerBytes()

        try await backend.removeLedgerBytes()
        let afterSecondRemoval = try await backend.loadLedgerBytes()

        XCTAssertNil(afterFirstRemoval)
        XCTAssertNil(afterSecondRemoval)
    }
}
