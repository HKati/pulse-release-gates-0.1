import Foundation

/// Fail-closed construction errors for one deterministic Device Ledger v0
/// `.pulseledger` carrier.
public enum DeterministicPulseledgerWriterError:
    Error,
    Sendable,
    Equatable
{
    case manifestMaterializationMismatch
    case packageSignatureMaterializationMismatch
    case packageSignatureLedgerMismatch
    case packageSignatureObserverMismatch
    case packageSignatureObjectMismatch
    case payloadInventoryMismatch
    case payloadMemberBindingMismatch(path: String)
    case unsafeMemberPath(path: String)
    case duplicateMemberPath(path: String)
    case emptyMember(path: String)
    case memberExceedsCarrierLimit(path: String)
    case memberNameLengthExceedsZIP16(path: String)
    case memberSizeExceedsZIP32(path: String)
    case totalUncompressedBytesExceedLimit
    case localHeaderOffsetExceedsZIP32(path: String)
    case centralDirectoryOffsetExceedsZIP32
    case centralDirectorySizeExceedsZIP32
    case carrierExceedsLimit
}

/// Exact deterministic Device Ledger v0 carrier bytes.
///
/// This value records only the bounded carrier identity. It does not verify the
/// carried evidence and does not create release, device-control, or external
/// validation authority.
public struct DevicePulseledgerCarrier:
    Sendable,
    Equatable
{
    public static let fileExtension = ".pulseledger"
    public static let mediaType = "application/zip"
    public static let packageFormat = "pulseledger_zip_v0"

    public let exactBytes: Data
    public let carrierSHA256: SHA256HexDigest
    public let sizeBytes: Int64
    public let memberPaths: [String]

    public var memberCount: Int {
        memberPaths.count
    }

    init(
        exactBytes: Data,
        memberPaths: [String]
    ) {
        self.exactBytes = Data(exactBytes)
        carrierSHA256 = LedgerRecordHasher.sha256Hex(
            of: exactBytes
        )
        sizeBytes = Int64(exactBytes.count)
        self.memberPaths = memberPaths
    }
}

/// Stored-only deterministic ZIP writer for one exact ten-member Device Ledger
/// v0 carrier.
///
/// The writer constructs every local header, central-directory row, CRC32, and
/// end-of-central-directory field directly. It does not delegate byte identity
/// to an opaque archive API.
public enum DeterministicPulseledgerWriter {
    public static let exactMemberOrder: [String] = [
        "contracts/pulsemech_device_canonical_json_v0.json",
        "contracts/pulsemech_ios_observation_contract_v0.json",
        "keys/observer-public-key-v0.bin",
        "ledger/pulsemech_device_transition_ledger_v0.json",
        DeviceLedgerManifest.manifestPath,
        "schemas/pulsemech_device_ledger_manifest_v0.schema.json",
        "schemas/pulsemech_device_signature_v0.schema.json",
        "schemas/pulsemech_device_transition_ledger_v0.schema.json",
        "signatures/checkpoint-signature-v0.json",
        DeviceLedgerManifest.packageSignaturePath,
    ]

    public static func materialize(
        manifestMaterialization:
            DeviceLedgerManifestMaterialization,
        packageSignature:
            DevicePackageSignatureMaterialization
    ) throws -> DevicePulseledgerCarrier {
        let manifest = manifestMaterialization.manifest
        let payloadMembers = manifestMaterialization.payloadMembers

        guard manifest.payloadMembers == payloadMembers else {
            throw DeterministicPulseledgerWriterError
                .manifestMaterializationMismatch
        }

        let expectedPayloadOrder = [
            exactMemberOrder[0],
            exactMemberOrder[1],
            exactMemberOrder[2],
            exactMemberOrder[3],
            exactMemberOrder[5],
            exactMemberOrder[6],
            exactMemberOrder[7],
            exactMemberOrder[8],
        ]
        guard payloadMembers.map(\.path) ==
                expectedPayloadOrder else {
            throw DeterministicPulseledgerWriterError
                .payloadInventoryMismatch
        }

        for member in payloadMembers {
            guard member.sizeBytes ==
                    Int64(member.exactBytes.count),
                  member.sha256 ==
                    LedgerRecordHasher.sha256Hex(
                        of: member.exactBytes
                    ) else {
                throw DeterministicPulseledgerWriterError
                    .payloadMemberBindingMismatch(
                        path: member.path
                    )
            }
        }

        let manifestBytes = manifest.canonicalBytes()
        guard manifest.sizeBytes == Int64(manifestBytes.count),
              manifest.manifestSHA256 ==
                LedgerRecordHasher.sha256Hex(
                    of: manifestBytes
                ) else {
            throw DeterministicPulseledgerWriterError
                .manifestMaterializationMismatch
        }

        guard packageSignature.document.subject ==
                packageSignature.subject,
              packageSignature.document.signature ==
                packageSignature.signature,
              packageSignature.signatureInputSHA256 ==
                packageSignature.subject.signatureInputSHA256 else {
            throw DeterministicPulseledgerWriterError
                .packageSignatureMaterializationMismatch
        }

        guard packageSignature.subject.ledgerID ==
                manifest.ledgerID else {
            throw DeterministicPulseledgerWriterError
                .packageSignatureLedgerMismatch
        }
        guard packageSignature.subject
                .observerPublicKeyFingerprintSHA256 ==
                manifest.observerPublicKeyFingerprintSHA256 else {
            throw DeterministicPulseledgerWriterError
                .packageSignatureObserverMismatch
        }
        guard packageSignature.subject.signedObjectSHA256 ==
                manifest.manifestSHA256 else {
            throw DeterministicPulseledgerWriterError
                .packageSignatureObjectMismatch
        }

        let packageSignatureBytes =
            packageSignature.document.canonicalBytes()
        guard packageSignature.document.sizeBytes ==
                Int64(packageSignatureBytes.count),
              packageSignature.document.documentSHA256 ==
                LedgerRecordHasher.sha256Hex(
                    of: packageSignatureBytes
                ) else {
            throw DeterministicPulseledgerWriterError
                .packageSignatureMaterializationMismatch
        }

        let inputs: [(path: String, exactBytes: Data)] = [
            (
                payloadMembers[0].path,
                payloadMembers[0].exactBytes
            ),
            (
                payloadMembers[1].path,
                payloadMembers[1].exactBytes
            ),
            (
                payloadMembers[2].path,
                payloadMembers[2].exactBytes
            ),
            (
                payloadMembers[3].path,
                payloadMembers[3].exactBytes
            ),
            (
                DeviceLedgerManifest.manifestPath,
                manifestBytes
            ),
            (
                payloadMembers[4].path,
                payloadMembers[4].exactBytes
            ),
            (
                payloadMembers[5].path,
                payloadMembers[5].exactBytes
            ),
            (
                payloadMembers[6].path,
                payloadMembers[6].exactBytes
            ),
            (
                payloadMembers[7].path,
                payloadMembers[7].exactBytes
            ),
            (
                DeviceLedgerManifest.packageSignaturePath,
                packageSignatureBytes
            ),
        ]

        guard inputs.map(\.path) == exactMemberOrder else {
            throw DeterministicPulseledgerWriterError
                .payloadInventoryMismatch
        }

        let members = try validatedMembers(
            from: inputs
        )
        let carrierBytes = try writeStoredZIP(
            members: members
        )

        return DevicePulseledgerCarrier(
            exactBytes: carrierBytes,
            memberPaths: members.map(\.path)
        )
    }

    private static func validatedMembers(
        from inputs: [(path: String, exactBytes: Data)]
    ) throws -> [CarrierMember] {
        guard inputs.count == exactMemberOrder.count else {
            throw DeterministicPulseledgerWriterError
                .payloadInventoryMismatch
        }

        var seenPaths: Set<String> = []
        var totalUncompressedBytes: Int64 = 0
        var members: [CarrierMember] = []
        members.reserveCapacity(inputs.count)

        for input in inputs {
            let path = input.path
            let pathBytes = Array(path.utf8)

            guard isSafeMemberPath(
                path,
                pathBytes: pathBytes
            ) else {
                throw DeterministicPulseledgerWriterError
                    .unsafeMemberPath(path: path)
            }
            guard seenPaths.insert(path).inserted else {
                throw DeterministicPulseledgerWriterError
                    .duplicateMemberPath(path: path)
            }
            guard !input.exactBytes.isEmpty else {
                throw DeterministicPulseledgerWriterError
                    .emptyMember(path: path)
            }

            let sizeBytes = Int64(input.exactBytes.count)
            guard sizeBytes <=
                    DeviceLedgerPayloadMember
                        .maximumSizeBytes else {
                throw DeterministicPulseledgerWriterError
                    .memberExceedsCarrierLimit(path: path)
            }
            guard UInt16(exactly: pathBytes.count) != nil else {
                throw DeterministicPulseledgerWriterError
                    .memberNameLengthExceedsZIP16(path: path)
            }
            guard UInt32(exactly: input.exactBytes.count) != nil else {
                throw DeterministicPulseledgerWriterError
                    .memberSizeExceedsZIP32(path: path)
            }

            let addition = totalUncompressedBytes
                .addingReportingOverflow(sizeBytes)
            guard !addition.overflow,
                  addition.partialValue <=
                    DeviceLedgerManifest
                        .maximumTotalUncompressedBytes else {
                throw DeterministicPulseledgerWriterError
                    .totalUncompressedBytesExceedLimit
            }
            totalUncompressedBytes = addition.partialValue

            members.append(
                CarrierMember(
                    path: path,
                    pathBytes: pathBytes,
                    exactBytes: input.exactBytes,
                    crc32: crc32(input.exactBytes)
                )
            )
        }

        return members
    }

    private static func isSafeMemberPath(
        _ path: String,
        pathBytes: [UInt8]
    ) -> Bool {
        guard !pathBytes.isEmpty,
              pathBytes.allSatisfy({ $0 < 0x80 }),
              !path.hasPrefix("/"),
              !path.hasSuffix("/"),
              !path.contains("\\"),
              !pathBytes.contains(0) else {
            return false
        }

        let components = path.split(
            separator: "/",
            omittingEmptySubsequences: false
        )
        return components.allSatisfy {
            !$0.isEmpty && $0 != "." && $0 != ".."
        }
    }

    private static func writeStoredZIP(
        members: [CarrierMember]
    ) throws -> Data {
        var output = Data()
        let estimatedPayloadBytes = members.reduce(0) {
            $0 + $1.exactBytes.count
        }
        output.reserveCapacity(
            estimatedPayloadBytes + 2_048
        )

        var centralRows: [CentralRow] = []
        centralRows.reserveCapacity(members.count)

        for member in members {
            guard let localHeaderOffset = UInt32(
                exactly: output.count
            ) else {
                throw DeterministicPulseledgerWriterError
                    .localHeaderOffsetExceedsZIP32(
                        path: member.path
                    )
            }
            let nameLength = UInt16(member.pathBytes.count)
            let size = UInt32(member.exactBytes.count)

            output.appendZIPUInt32(localHeaderSignature)
            output.appendZIPUInt16(versionNeeded)
            output.appendZIPUInt16(generalPurposeFlags)
            output.appendZIPUInt16(storedCompressionMethod)
            output.appendZIPUInt16(fixedDOSTime)
            output.appendZIPUInt16(fixedDOSDate)
            output.appendZIPUInt32(member.crc32)
            output.appendZIPUInt32(size)
            output.appendZIPUInt32(size)
            output.appendZIPUInt16(nameLength)
            output.appendZIPUInt16(0)
            output.append(contentsOf: member.pathBytes)
            output.append(member.exactBytes)

            centralRows.append(
                CentralRow(
                    member: member,
                    localHeaderOffset: localHeaderOffset
                )
            )
        }

        guard let centralDirectoryOffset = UInt32(
            exactly: output.count
        ) else {
            throw DeterministicPulseledgerWriterError
                .centralDirectoryOffsetExceedsZIP32
        }
        let centralDirectoryStart = output.count

        for row in centralRows {
            let member = row.member
            let nameLength = UInt16(member.pathBytes.count)
            let size = UInt32(member.exactBytes.count)

            output.appendZIPUInt32(centralDirectorySignature)
            output.appendZIPUInt16(versionMadeBy)
            output.appendZIPUInt16(versionNeeded)
            output.appendZIPUInt16(generalPurposeFlags)
            output.appendZIPUInt16(storedCompressionMethod)
            output.appendZIPUInt16(fixedDOSTime)
            output.appendZIPUInt16(fixedDOSDate)
            output.appendZIPUInt32(member.crc32)
            output.appendZIPUInt32(size)
            output.appendZIPUInt32(size)
            output.appendZIPUInt16(nameLength)
            output.appendZIPUInt16(0)
            output.appendZIPUInt16(0)
            output.appendZIPUInt16(0)
            output.appendZIPUInt16(0)
            output.appendZIPUInt32(unixRegularFile0644)
            output.appendZIPUInt32(row.localHeaderOffset)
            output.append(contentsOf: member.pathBytes)
        }

        guard let centralDirectorySize = UInt32(
            exactly: output.count - centralDirectoryStart
        ) else {
            throw DeterministicPulseledgerWriterError
                .centralDirectorySizeExceedsZIP32
        }
        let memberCount = UInt16(members.count)

        output.appendZIPUInt32(endOfCentralDirectorySignature)
        output.appendZIPUInt16(0)
        output.appendZIPUInt16(0)
        output.appendZIPUInt16(memberCount)
        output.appendZIPUInt16(memberCount)
        output.appendZIPUInt32(centralDirectorySize)
        output.appendZIPUInt32(centralDirectoryOffset)
        output.appendZIPUInt16(0)

        guard Int64(output.count) <=
                DeviceLedgerManifest.maximumCarrierBytes else {
            throw DeterministicPulseledgerWriterError
                .carrierExceedsLimit
        }

        return output
    }

    private static func crc32(
        _ bytes: Data
    ) -> UInt32 {
        var crc: UInt32 = 0xFFFF_FFFF

        for byte in bytes {
            crc ^= UInt32(byte)
            for _ in 0..<8 {
                let mask = UInt32.zero &- (crc & 1)
                crc = (crc >> 1) ^
                    (0xEDB8_8320 & mask)
            }
        }

        return crc ^ 0xFFFF_FFFF
    }

    private static let localHeaderSignature: UInt32 =
        0x0403_4B50
    private static let centralDirectorySignature: UInt32 =
        0x0201_4B50
    private static let endOfCentralDirectorySignature: UInt32 =
        0x0605_4B50
    private static let versionMadeBy: UInt16 = 0x0314
    private static let versionNeeded: UInt16 = 20
    private static let generalPurposeFlags: UInt16 = 0
    private static let storedCompressionMethod: UInt16 = 0
    private static let fixedDOSTime: UInt16 = 0
    private static let fixedDOSDate: UInt16 = 0x0021
    private static let unixRegularFile0644: UInt32 =
        0x81A4_0000
}

public extension DeviceLedgerManifestMaterialization {
    /// Materializes the exact deterministic Device Ledger v0 ZIP carrier from
    /// this canonical manifest and its bound package-signature materialization.
    ///
    /// This method does not write a filesystem object, invoke a verifier, or
    /// create release, device-control, or external validation authority.
    func materializePulseledgerCarrier(
        packageSignature:
            DevicePackageSignatureMaterialization
    ) throws -> DevicePulseledgerCarrier {
        try DeterministicPulseledgerWriter.materialize(
            manifestMaterialization: self,
            packageSignature: packageSignature
        )
    }
}

private struct CarrierMember {
    let path: String
    let pathBytes: [UInt8]
    let exactBytes: Data
    let crc32: UInt32

    init(
        path: String,
        pathBytes: [UInt8],
        exactBytes: Data,
        crc32: UInt32
    ) {
        self.path = path
        self.pathBytes = pathBytes
        self.exactBytes = Data(exactBytes)
        self.crc32 = crc32
    }
}

private struct CentralRow {
    let member: CarrierMember
    let localHeaderOffset: UInt32
}

private extension Data {
    mutating func appendZIPUInt16(
        _ value: UInt16
    ) {
        append(UInt8(truncatingIfNeeded: value))
        append(UInt8(truncatingIfNeeded: value >> 8))
    }

    mutating func appendZIPUInt32(
        _ value: UInt32
    ) {
        append(UInt8(truncatingIfNeeded: value))
        append(UInt8(truncatingIfNeeded: value >> 8))
        append(UInt8(truncatingIfNeeded: value >> 16))
        append(UInt8(truncatingIfNeeded: value >> 24))
    }
}
