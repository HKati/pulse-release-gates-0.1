import Foundation

/// Observer-owned signing boundary for one already reconstructed 32-byte
/// checkpoint-signature digest.
///
/// Implementations may use a software P-256 key, Secure Enclave-backed P-256
/// key, or a test fixture. The exact observer identity is exposed before any
/// signing operation so the materializer can reject a key/ledger mismatch
/// without invoking the signer.
public protocol DeviceCheckpointSigner: Sendable {
    var observerIdentity: DeviceLedgerObserverIdentity { get }

    /// Signs the exact SHA-256 digest supplied by the checkpoint-signature
    /// materializer and returns a 64-byte IEEE P1363 `r || s` value.
    ///
    /// The implementation must use the private key corresponding to
    /// `observerIdentity.publicKeyX963Uncompressed`.
    func signCheckpointDigest(
        _ digest: Data
    ) async throws -> Data
}

/// Fail-closed materialization errors owned by the signer boundary.
public enum DeviceCheckpointSignatureMaterializationError:
    Error,
    Sendable,
    Equatable
{
    case signerObserverIdentityMismatch
    case signerReturnedInvalidSignature(DeviceP256SignatureError)
}

/// Complete result of one checkpoint-signature materialization.
///
/// The closed ledger remains immutable. Signing creates a separate signature
/// document for later manifest and package assembly.
public struct DeviceCheckpointSignatureMaterialization:
    Sendable,
    Equatable
{
    public let subject: DeviceCheckpointSignatureSubject
    public let signatureInputSHA256: Data
    public let signature: DeviceP256Signature
    public let document: DeviceCheckpointSignatureDocument

    init(
        subject: DeviceCheckpointSignatureSubject,
        signatureInputSHA256: Data,
        signature: DeviceP256Signature,
        document: DeviceCheckpointSignatureDocument
    ) {
        self.subject = subject
        self.signatureInputSHA256 = Data(signatureInputSHA256)
        self.signature = signature
        self.document = document
    }
}

/// Pure checkpoint-signature materialization over one immutable terminal
/// ledger closure.
public enum DeviceCheckpointSignatureMaterializer {
    public static func materialize(
        closure: DeviceTransitionLedgerClosure,
        signer: any DeviceCheckpointSigner
    ) async throws -> DeviceCheckpointSignatureMaterialization {
        guard signer.observerIdentity == closure.document.observerIdentity else {
            throw DeviceCheckpointSignatureMaterializationError
                .signerObserverIdentityMismatch
        }

        let subject = DeviceCheckpointSignatureSubject(
            ledgerID: closure.checkpointSource.ledgerID,
            observerPublicKeyFingerprintSHA256:
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                closure.checkpointRecord.recordSHA256
        )
        let signatureInputSHA256 = subject.signatureInputSHA256

        let returnedBytes = try await signer.signCheckpointDigest(
            signatureInputSHA256
        )

        let signature: DeviceP256Signature
        do {
            signature = try DeviceP256Signature(
                ieeeP1363FixedWidth: returnedBytes
            )
        } catch let error as DeviceP256SignatureError {
            throw DeviceCheckpointSignatureMaterializationError
                .signerReturnedInvalidSignature(error)
        }

        let document = DeviceCheckpointSignatureDocument(
            subject: subject,
            signature: signature
        )

        return DeviceCheckpointSignatureMaterialization(
            subject: subject,
            signatureInputSHA256: signatureInputSHA256,
            signature: signature,
            document: document
        )
    }
}

public extension DeviceTransitionLedgerClosure {
    /// Produces the separate checkpoint-signature document for this exact
    /// immutable terminal closure.
    func materializeCheckpointSignature(
        using signer: any DeviceCheckpointSigner
    ) async throws -> DeviceCheckpointSignatureMaterialization {
        try await DeviceCheckpointSignatureMaterializer.materialize(
            closure: self,
            signer: signer
        )
    }
}
