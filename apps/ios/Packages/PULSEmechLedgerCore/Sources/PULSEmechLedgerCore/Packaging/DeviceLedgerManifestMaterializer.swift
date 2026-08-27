import Foundation

/// Fail-closed relation errors for Device Ledger v0 manifest materialization.
public enum DeviceLedgerManifestMaterializationError:
    Error,
    Sendable,
    Equatable
{
    case closureDocumentBindingMismatch
    case checkpointSignatureMaterializationMismatch
    case checkpointSignatureLedgerMismatch
    case checkpointSignatureObserverMismatch
    case checkpointSignatureObjectMismatch
    case observerPublicKeyBindingMismatch
    case payloadMemberInvalid(DeviceLedgerPayloadMemberError)
    case payloadMembersExceedTotalUncompressedLimit
    case manifestInvalid(DeviceLedgerManifestError)
    case manifestExceedsMemberLimit
    case payloadAndManifestExceedTotalUncompressedLimit
}

/// Complete deterministic result before package signing and ZIP assembly.
///
/// `payloadMembers` retains exact bytes in the normative manifest inventory
/// order. `manifest` is the exact canonical object whose SHA-256 becomes the
/// signed object of the later package-signature layer.
public struct DeviceLedgerManifestMaterialization:
    Sendable,
    Equatable
{
    public let payloadMembers: [DeviceLedgerPayloadMember]
    public let manifest: DeviceLedgerManifest

    init(
        payloadMembers: [DeviceLedgerPayloadMember],
        manifest: DeviceLedgerManifest
    ) {
        self.payloadMembers = payloadMembers
        self.manifest = manifest
    }

    public func payloadMember(
        at path: String
    ) -> DeviceLedgerPayloadMember? {
        payloadMembers.first {
            $0.path == path
        }
    }
}

/// Pure deterministic manifest construction over one immutable terminal ledger
/// closure and its exact checkpoint-signature materialization.
public enum DeviceLedgerManifestMaterializer {
    public static func materialize(
        closure: DeviceTransitionLedgerClosure,
        checkpointSignature:
            DeviceCheckpointSignatureMaterialization,
        contractMembers:
            DeviceLedgerManifestContractMembers
    ) throws -> DeviceLedgerManifestMaterialization {
        guard closure.document.checkpointSource ==
                closure.checkpointSource,
              closure.document.checkpointPayload ==
                closure.checkpointPayload,
              closure.document.checkpointRecord ==
                closure.checkpointRecord,
              closure.document.records.last ==
                closure.checkpointRecord,
              Int64(closure.document.records.count) ==
                closure.checkpointSource.closedRecordCount + 1 else {
            throw DeviceLedgerManifestMaterializationError
                .closureDocumentBindingMismatch
        }

        guard checkpointSignature.document.subject ==
                checkpointSignature.subject,
              checkpointSignature.document.signature ==
                checkpointSignature.signature,
              checkpointSignature.signatureInputSHA256 ==
                checkpointSignature.subject.signatureInputSHA256 else {
            throw DeviceLedgerManifestMaterializationError
                .checkpointSignatureMaterializationMismatch
        }

        guard checkpointSignature.subject.ledgerID ==
                closure.checkpointSource.ledgerID else {
            throw DeviceLedgerManifestMaterializationError
                .checkpointSignatureLedgerMismatch
        }
        guard checkpointSignature.subject
                .observerPublicKeyFingerprintSHA256 ==
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256,
              closure.document.observerIdentity
                .publicKeyFingerprintSHA256 ==
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256 else {
            throw DeviceLedgerManifestMaterializationError
                .checkpointSignatureObserverMismatch
        }
        guard checkpointSignature.subject.signedObjectSHA256 ==
                closure.checkpointRecord.recordSHA256 else {
            throw DeviceLedgerManifestMaterializationError
                .checkpointSignatureObjectMismatch
        }

        let observerPublicKeyBytes =
            closure.document.observerIdentity
                .publicKeyX963Uncompressed
        guard observerPublicKeyBytes.count == 65,
              LedgerRecordHasher.sha256Hex(
                  of: observerPublicKeyBytes
              ) ==
                closure.checkpointSource
                    .observerPublicKeyFingerprintSHA256 else {
            throw DeviceLedgerManifestMaterializationError
                .observerPublicKeyBindingMismatch
        }

        let ledgerBytes = closure.document.canonicalBytes()
        let checkpointSignatureBytes =
            checkpointSignature.document.canonicalBytes()

        var payloadMembers: [DeviceLedgerPayloadMember] = []
        payloadMembers.reserveCapacity(
            DeviceLedgerManifestPayloadMemberKind.allCases.count
        )

        for kind in DeviceLedgerManifestPayloadMemberKind.allCases {
            let exactBytes: Data

            if let staticBytes = contractMembers.exactBytes(
                for: kind
            ) {
                exactBytes = staticBytes
            } else {
                switch kind {
                case .observerPublicKey:
                    exactBytes = observerPublicKeyBytes
                case .transitionLedger:
                    exactBytes = ledgerBytes
                case .checkpointSignature:
                    exactBytes = checkpointSignatureBytes
                case .canonicalizationProfile,
                     .observationContract,
                     .manifestSchema,
                     .signatureSchema,
                     .transitionLedgerSchema:
                    preconditionFailure(
                        "Validated static manifest member is unavailable"
                    )
                }
            }

            do {
                payloadMembers.append(
                    try DeviceLedgerPayloadMember(
                        kind: kind,
                        exactBytes: exactBytes
                    )
                )
            } catch let error as DeviceLedgerPayloadMemberError {
                throw DeviceLedgerManifestMaterializationError
                    .payloadMemberInvalid(error)
            }
        }

        let payloadTotal = payloadMembers.reduce(Int64(0)) {
            $0 + $1.sizeBytes
        }
        guard payloadTotal <=
                DeviceLedgerManifest
                    .maximumTotalUncompressedBytes else {
            throw DeviceLedgerManifestMaterializationError
                .payloadMembersExceedTotalUncompressedLimit
        }

        let manifest: DeviceLedgerManifest
        do {
            manifest = try DeviceLedgerManifest(
                createdUnixNS:
                    closure.checkpointPayload.createdUnixNS,
                ledgerID:
                    closure.checkpointSource.ledgerID,
                recordStatus:
                    closure.checkpointSource.recordStatus,
                ledgerSHA256:
                    closure.document.ledgerSHA256,
                ledgerSizeBytes:
                    closure.document.sizeBytes,
                recordCount:
                    Int64(closure.document.records.count),
                checkpointRecordSHA256:
                    closure.checkpointRecord.recordSHA256,
                observerPublicKeyFingerprintSHA256:
                    closure.checkpointSource
                        .observerPublicKeyFingerprintSHA256,
                checkpointSignatureDocumentSHA256:
                    checkpointSignature.document.documentSHA256,
                checkpointSignatureDocumentSizeBytes:
                    checkpointSignature.document.sizeBytes,
                payloadMembers: payloadMembers
            )
        } catch let error as DeviceLedgerManifestError {
            throw DeviceLedgerManifestMaterializationError
                .manifestInvalid(error)
        }

        guard manifest.sizeBytes <=
                DeviceLedgerPayloadMember.maximumSizeBytes else {
            throw DeviceLedgerManifestMaterializationError
                .manifestExceedsMemberLimit
        }
        guard payloadTotal + manifest.sizeBytes <=
                DeviceLedgerManifest
                    .maximumTotalUncompressedBytes else {
            throw DeviceLedgerManifestMaterializationError
                .payloadAndManifestExceedTotalUncompressedLimit
        }

        return DeviceLedgerManifestMaterialization(
            payloadMembers: payloadMembers,
            manifest: manifest
        )
    }
}

public extension DeviceTransitionLedgerClosure {
    /// Materializes the exact package payload inventory and canonical manifest
    /// for this immutable closure and checkpoint signature.
    ///
    /// This method does not invoke a package signer and does not create ZIP
    /// bytes. Those remain later, separate boundaries.
    func materializePackageManifest(
        checkpointSignature:
            DeviceCheckpointSignatureMaterialization,
        contractMembers:
            DeviceLedgerManifestContractMembers
    ) throws -> DeviceLedgerManifestMaterialization {
        try DeviceLedgerManifestMaterializer.materialize(
            closure: self,
            checkpointSignature: checkpointSignature,
            contractMembers: contractMembers
        )
    }
}
