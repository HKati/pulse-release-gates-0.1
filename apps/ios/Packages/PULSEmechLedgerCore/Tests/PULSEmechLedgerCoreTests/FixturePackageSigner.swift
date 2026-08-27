import Foundation
@testable import PULSEmechLedgerCore

enum FixturePackageSignerError: Error, Sendable, Equatable {
    case unexpectedDigest
    case forcedFailure
}

/// Actor-isolated test probe for exact package-signer invocation evidence.
actor FixturePackageSignerInvocationRecorder {
    private var receivedDigests: [Data] = []

    func record(_ digest: Data) {
        receivedDigests.append(
            Data(digest)
        )
    }

    var invocationCount: Int {
        receivedDigests.count
    }

    func snapshot() -> [Data] {
        receivedDigests.map {
            Data($0)
        }
    }
}

/// Test-only package-signer boundary.
///
/// This fixture does not claim to be a production private-key
/// implementation. It proves that the package-signature materializer:
///
/// - admits only the exact framed package digest;
/// - invokes the signer only after closure, manifest, observer, and signer
///   bindings are established;
/// - emits the exact Python-reference package-signature document when
///   supplied with the reference signature bytes;
/// - rejects malformed or non-canonical signer output through the production
///   `DeviceP256Signature` boundary.
struct FixturePackageSigner: DevicePackageSigner {
    let observerIdentity: DeviceLedgerObserverIdentity
    let expectedDigest: Data
    let returnedSignature: Data
    let forceFailure: Bool
    let invocationRecorder:
        FixturePackageSignerInvocationRecorder?

    init(
        observerIdentity: DeviceLedgerObserverIdentity,
        expectedDigest: Data,
        returnedSignature: Data,
        forceFailure: Bool = false,
        invocationRecorder:
            FixturePackageSignerInvocationRecorder? = nil
    ) {
        self.observerIdentity = observerIdentity
        self.expectedDigest = Data(expectedDigest)
        self.returnedSignature = Data(returnedSignature)
        self.forceFailure = forceFailure
        self.invocationRecorder = invocationRecorder
    }

    func signPackageDigest(
        _ digest: Data
    ) async throws -> Data {
        if let invocationRecorder {
            await invocationRecorder.record(
                digest
            )
        }

        if forceFailure {
            throw FixturePackageSignerError.forcedFailure
        }

        guard digest == expectedDigest else {
            throw FixturePackageSignerError.unexpectedDigest
        }

        return Data(returnedSignature)
    }

    /// Canonical low-S shape used when a test needs a valid signature
    /// representation without asserting the reference signature identity.
    static func validShapeSignature() -> Data {
        var bytes = Data(
            repeating: 0,
            count: 64
        )
        bytes[31] = 1
        bytes[63] = 1
        return bytes
    }

    /// Exact deterministic package signature produced by the Python reference
    /// signer for:
    ///
    /// signing-input SHA-256:
    /// fcd90dc41a07d24146f04938d6ca43a88c17c0f0e2d526d4f04dbb4e2ff7012e
    static func referencePackageSignature() -> Data {
        Data(
            base64Encoded:
                "OAI79AEDhcp/XMZwhT7SXlj0lz0GOAfUMOe3f8UTXocdN4A1tOszsQUIUH2dIRAjSsXwtCDpw/wKsNGS4AoZlQ=="
        )!
    }
}
