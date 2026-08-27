import Foundation
@testable import PULSEmechLedgerCore

enum FixtureCheckpointSignerError: Error, Sendable, Equatable {
    case unexpectedDigest
    case forcedFailure
}

/// Test-only signer boundary.
///
/// This fixture does not claim to be a production private-key implementation.
/// It proves that the Swift materializer passes the exact framed digest and
/// emits the exact Python-reference signature document when supplied with the
/// reference signature bytes.
struct FixtureCheckpointSigner: DeviceCheckpointSigner {
    let observerIdentity: DeviceLedgerObserverIdentity
    let expectedDigest: Data
    let returnedSignature: Data
    let forceFailure: Bool

    init(
        observerIdentity: DeviceLedgerObserverIdentity,
        expectedDigest: Data,
        returnedSignature: Data,
        forceFailure: Bool = false
    ) {
        self.observerIdentity = observerIdentity
        self.expectedDigest = Data(expectedDigest)
        self.returnedSignature = Data(returnedSignature)
        self.forceFailure = forceFailure
    }

    func signCheckpointDigest(
        _ digest: Data
    ) async throws -> Data {
        if forceFailure {
            throw FixtureCheckpointSignerError.forcedFailure
        }
        guard digest == expectedDigest else {
            throw FixtureCheckpointSignerError.unexpectedDigest
        }
        return Data(returnedSignature)
    }

    static func validShapeSignature() -> Data {
        var bytes = Data(repeating: 0, count: 64)
        bytes[31] = 1
        bytes[63] = 1
        return bytes
    }

    static func referenceCheckpointSignature() -> Data {
        Data(
            base64Encoded:
                "BOBikuqSCnXUQnqSzGnB6EmJhvM0Bm7BGg0uX0EeSAMJyAaJRC2P+xS9gVqK8t0zU6zmXRkGqYaLj9nLK+GzgQ=="
        )!
    }
}
