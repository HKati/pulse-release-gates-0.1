import Foundation
@testable import PULSEmechLedgerCore

enum FixturePulseledgerCarrierFactoryError:
    Error,
    Sendable,
    Equatable
{
    case repositoryRootUnavailable
}

/// Complete deterministic reference path used by the carrier regressions.
///
/// Every value is produced through the existing production materializers. The
/// fixture supplies only the already established synthetic reference inputs and
/// deterministic test-signature bytes.
struct FixturePulseledgerReferenceMaterialization:
    Sendable,
    Equatable
{
    let closure: DeviceTransitionLedgerClosure
    let checkpointSignature:
        DeviceCheckpointSignatureMaterialization
    let manifest: DeviceLedgerManifestMaterialization
    let packageSignature:
        DevicePackageSignatureMaterialization
    let carrier: DevicePulseledgerCarrier
}

enum FixturePulseledgerCarrierFactory {
    static let referenceCarrierFileName =
        "pulsemech_device_transition_ledger_reference_v0.pulseledger"

    static let referenceCarrierSizeBytes: Int64 =
        133_568

    static let referenceCarrierSHA256 = try! SHA256HexDigest(
        "a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3"
    )

    static func makeReferenceMaterialization() async throws
        -> FixturePulseledgerReferenceMaterialization
    {
        let closure = try await FixtureDeviceLedgerManifestFactory
            .makeReferenceClosure()
        let checkpointSignature =
            try await FixtureDeviceLedgerManifestFactory
                .makeReferenceCheckpointSignature(
                    closure: closure
                )
        let manifest = try closure.materializePackageManifest(
            checkpointSignature: checkpointSignature,
            contractMembers:
                FixtureDeviceLedgerManifestFactory
                    .contractMembers()
        )
        let packageSignature = try await makeReferencePackageSignature(
            closure: closure,
            manifest: manifest
        )
        let carrier = try manifest.materializePulseledgerCarrier(
            packageSignature: packageSignature
        )

        return FixturePulseledgerReferenceMaterialization(
            closure: closure,
            checkpointSignature: checkpointSignature,
            manifest: manifest,
            packageSignature: packageSignature,
            carrier: carrier
        )
    }

    static func makeReferencePackageSignature(
        closure: DeviceTransitionLedgerClosure,
        manifest: DeviceLedgerManifestMaterialization
    ) async throws -> DevicePackageSignatureMaterialization {
        let subject = DevicePackageSignatureSubject(
            ledgerID: manifest.manifest.ledgerID,
            observerPublicKeyFingerprintSHA256:
                manifest.manifest
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                manifest.manifest.manifestSHA256
        )
        let signer = FixturePackageSigner(
            observerIdentity:
                closure.document.observerIdentity,
            expectedDigest:
                subject.signatureInputSHA256,
            returnedSignature:
                FixturePackageSigner.referencePackageSignature()
        )

        return try await closure.materializePackageSignature(
            manifest: manifest,
            using: signer
        )
    }

    static func referenceCarrierBytes() throws -> Data {
        try Data(
            contentsOf: try repositoryRoot().appendingPathComponent(
                "examples/device_transition_ledger/\(referenceCarrierFileName)"
            )
        )
    }

    private static func repositoryRoot() throws -> URL {
        if let workspace =
            ProcessInfo.processInfo.environment["GITHUB_WORKSPACE"]
        {
            let candidate = URL(
                fileURLWithPath: workspace,
                isDirectory: true
            )
            if FileManager.default.fileExists(
                atPath: candidate.appendingPathComponent(
                    "examples/device_transition_ledger/\(referenceCarrierFileName)"
                ).path
            ) {
                return candidate
            }
        }

        var candidate = URL(
            fileURLWithPath: #filePath
        )
        for _ in 0..<7 {
            candidate.deleteLastPathComponent()
        }

        guard FileManager.default.fileExists(
            atPath: candidate.appendingPathComponent(
                "examples/device_transition_ledger/\(referenceCarrierFileName)"
            ).path
        ) else {
            throw FixturePulseledgerCarrierFactoryError
                .repositoryRootUnavailable
        }

        return candidate
    }
}
