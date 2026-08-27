import Foundation

/// Observer-owned signing boundary for one already reconstructed 32-byte
/// package-signature digest.
///
/// Implementations may use a software P-256 key, Secure Enclave-backed P-256
/// key, or a test fixture. The exact observer identity is exposed before any
/// signing operation so the materializer can reject a key/ledger mismatch
/// without invoking the signer.
public protocol DevicePackageSigner: Sendable {
    var observerIdentity: DeviceLedgerObserverIdentity { get }

    /// Signs the exact SHA-256 digest supplied by the package-signature
    /// materializer and returns a 64-byte IEEE P1363 `r || s` value.
    ///
    /// The implementation must use the private key corresponding to
    /// `observerIdentity.publicKeyX963Uncompressed`.
    func signPackageDigest(
        _ digest: Data
    ) async throws -> Data
}

/// Fail-closed materialization errors owned by the package-signer boundary.
public enum DevicePackageSignatureMaterializationError:
    Error,
    Sendable,
    Equatable
{
    case manifestMaterializationMismatch
    case manifestClosureLedgerMismatch
    case manifestClosureObserverMismatch
    case signerObserverIdentityMismatch
    case signerReturnedInvalidSignature(DeviceP256SignatureError)
}

/// Complete result of one package-signature materialization.
///
/// The terminal ledger closure and manifest remain immutable. Signing creates
/// one separate package-signature document for later deterministic carrier
/// assembly.
public struct DevicePackageSignatureMaterialization:
    Sendable,
    Equatable
{
    public let subject: DevicePackageSignatureSubject
    public let signatureInputSHA256: Data
    public let signature: DeviceP256Signature
    public let document: DevicePackageSignatureDocument

    init(
        subject: DevicePackageSignatureSubject,
        signatureInputSHA256: Data,
        signature: DeviceP256Signature,
        document: DevicePackageSignatureDocument
    ) {
        self.subject = subject
        self.signatureInputSHA256 = Data(signatureInputSHA256)
        self.signature = signature
        self.document = document
    }
}

/// Pure package-signature materialization over one immutable terminal ledger
/// closure and its exact canonical manifest materialization.
public enum DevicePackageSignatureMaterializer {
    public static func materialize(
        closure: DeviceTransitionLedgerClosure,
        manifestMaterialization:
            DeviceLedgerManifestMaterialization,
        signer: any DevicePackageSigner
    ) async throws -> DevicePackageSignatureMaterialization {
        let manifest = manifestMaterialization.manifest

        guard manifest.payloadMembers ==
                manifestMaterialization.payloadMembers else {
            throw DevicePackageSignatureMaterializationError
                .manifestMaterializationMismatch
        }

        guard let ledgerMember =
                manifestMaterialization.payloadMember(
                    at:
                        "ledger/pulsemech_device_transition_ledger_v0.json"
                ),
              manifest.createdUnixNS ==
                closure.checkpointPayload.createdUnixNS,
              manifest.ledgerID ==
                closure.checkpointSource.ledgerID,
              manifest.recordStatus ==
                closure.checkpointSource.recordStatus,
              manifest.ledgerSHA256 ==
                closure.document.ledgerSHA256,
              manifest.ledgerSizeBytes ==
                closure.document.sizeBytes,
              manifest.recordCount ==
                Int64(closure.document.records.count),
              manifest.checkpointRecordSHA256 ==
                closure.checkpointRecord.recordSHA256,
              ledgerMember.sha256 ==
                closure.document.ledgerSHA256,
              ledgerMember.sizeBytes ==
                closure.document.sizeBytes,
              ledgerMember.exactBytes ==
                closure.document.canonicalBytes() else {
            throw DevicePackageSignatureMaterializationError
                .manifestClosureLedgerMismatch
        }

        let closureObserverIdentity =
            closure.document.observerIdentity

        guard let observerMember =
                manifestMaterialization.payloadMember(
                    at: "keys/observer-public-key-v0.bin"
                ),
              closureObserverIdentity.publicKeyFingerprintSHA256 ==
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
              manifest.observerPublicKeyFingerprintSHA256 ==
                closureObserverIdentity
                    .publicKeyFingerprintSHA256,
              observerMember.sha256 ==
                closureObserverIdentity
                    .publicKeyFingerprintSHA256,
              observerMember.sizeBytes == 65,
              observerMember.exactBytes ==
                closureObserverIdentity
                    .publicKeyX963Uncompressed else {
            throw DevicePackageSignatureMaterializationError
                .manifestClosureObserverMismatch
        }

        guard signer.observerIdentity ==
                closureObserverIdentity else {
            throw DevicePackageSignatureMaterializationError
                .signerObserverIdentityMismatch
        }

        let subject = DevicePackageSignatureSubject(
            ledgerID: manifest.ledgerID,
            observerPublicKeyFingerprintSHA256:
                manifest.observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                manifest.manifestSHA256
        )
        let signatureInputSHA256 =
            subject.signatureInputSHA256

        let returnedBytes = try await signer.signPackageDigest(
            signatureInputSHA256
        )

        let signature: DeviceP256Signature
        do {
            signature = try DeviceP256Signature(
                ieeeP1363FixedWidth: returnedBytes
            )
        } catch let error as DeviceP256SignatureError {
            throw DevicePackageSignatureMaterializationError
                .signerReturnedInvalidSignature(error)
        }

        let document = DevicePackageSignatureDocument(
            subject: subject,
            signature: signature
        )

        return DevicePackageSignatureMaterialization(
            subject: subject,
            signatureInputSHA256: signatureInputSHA256,
            signature: signature,
            document: document
        )
    }
}

public extension DeviceTransitionLedgerClosure {
    /// Produces the separate package-signature document for the exact canonical
    /// manifest belonging to this immutable terminal closure.
    ///
    /// This method does not write ZIP headers, assemble carrier bytes, or
    /// export a `.pulseledger` file.
    func materializePackageSignature(
        manifest:
            DeviceLedgerManifestMaterialization,
        using signer: any DevicePackageSigner
    ) async throws -> DevicePackageSignatureMaterialization {
        try await DevicePackageSignatureMaterializer.materialize(
            closure: self,
            manifestMaterialization: manifest,
            signer: signer
        )
    }
}
