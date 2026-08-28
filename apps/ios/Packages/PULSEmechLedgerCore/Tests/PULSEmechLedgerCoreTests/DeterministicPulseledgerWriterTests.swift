import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class DeterministicPulseledgerWriterTests: XCTestCase {
    private func reference() async throws
        -> FixturePulseledgerReferenceMaterialization
    {
        try await FixturePulseledgerCarrierFactory
            .makeReferenceMaterialization()
    }

    private func packageSignatureMaterialization(
        subject: DevicePackageSignatureSubject,
        signature: DeviceP256Signature
    ) -> DevicePackageSignatureMaterialization {
        DevicePackageSignatureMaterialization(
            subject: subject,
            signatureInputSHA256:
                subject.signatureInputSHA256,
            signature: signature,
            document: DevicePackageSignatureDocument(
                subject: subject,
                signature: signature
            )
        )
    }

    private func expectedMemberBytes(
        from value: FixturePulseledgerReferenceMaterialization
    ) -> [String: Data] {
        var result = Dictionary(
            uniqueKeysWithValues:
                value.manifest.payloadMembers.map {
                    ($0.path, $0.exactBytes)
                }
        )
        result[DeviceLedgerManifest.manifestPath] =
            value.manifest.manifest.canonicalBytes()
        result[DeviceLedgerManifest.packageSignaturePath] =
            value.packageSignature.document.canonicalBytes()
        return result
    }

    func testReferenceCarrierMatchesExactCheckedInBytesAndIdentity()
        async throws
    {
        let value = try await reference()
        let expected = try FixturePulseledgerCarrierFactory
            .referenceCarrierBytes()

        XCTAssertEqual(value.carrier.exactBytes, expected)
        XCTAssertEqual(
            value.carrier.sizeBytes,
            FixturePulseledgerCarrierFactory
                .referenceCarrierSizeBytes
        )
        XCTAssertEqual(
            value.carrier.exactBytes.count,
            Int(
                FixturePulseledgerCarrierFactory
                    .referenceCarrierSizeBytes
            )
        )
        XCTAssertEqual(
            value.carrier.carrierSHA256,
            FixturePulseledgerCarrierFactory
                .referenceCarrierSHA256
        )
        XCTAssertEqual(
            LedgerRecordHasher.sha256Hex(
                of: value.carrier.exactBytes
            ),
            value.carrier.carrierSHA256
        )
    }

    func testReferenceCarrierReportsExactDeclarationsAndMemberOrder()
        async throws
    {
        let value = try await reference()

        XCTAssertEqual(
            DevicePulseledgerCarrier.fileExtension,
            ".pulseledger"
        )
        XCTAssertEqual(
            DevicePulseledgerCarrier.mediaType,
            "application/zip"
        )
        XCTAssertEqual(
            DevicePulseledgerCarrier.packageFormat,
            "pulseledger_zip_v0"
        )
        XCTAssertEqual(value.carrier.memberCount, 10)
        XCTAssertEqual(
            value.carrier.memberPaths,
            DeterministicPulseledgerWriter.exactMemberOrder
        )
    }

    func testReferenceCarrierContainsExactBoundMemberPayloads()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )
        let expected = expectedMemberBytes(
            from: value
        )

        XCTAssertEqual(archive.localEntries.count, 10)
        XCTAssertEqual(Set(expected.keys).count, 10)

        for entry in archive.localEntries {
            XCTAssertEqual(
                entry.payload,
                try XCTUnwrap(expected[entry.path]),
                "Unexpected bytes for \(entry.path)"
            )
        }
    }

    func testReferenceCarrierUsesStoredLocalHeadersAndFixedMetadata()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        for entry in archive.localEntries {
            XCTAssertEqual(entry.versionNeeded, 20)
            XCTAssertEqual(entry.flags, 0)
            XCTAssertEqual(entry.compressionMethod, 0)
            XCTAssertEqual(entry.dosTime, 0)
            XCTAssertEqual(entry.dosDate, 0x0021)
            XCTAssertEqual(entry.extraFieldLength, 0)
            XCTAssertEqual(entry.compressedSize, entry.uncompressedSize)
            XCTAssertEqual(
                entry.compressedSize,
                UInt32(entry.payload.count)
            )
        }
    }

    func testReferenceCarrierUsesExactCentralDirectoryMetadata()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        for entry in archive.centralEntries {
            XCTAssertEqual(entry.versionMadeBy, 0x0314)
            XCTAssertEqual(entry.versionNeeded, 20)
            XCTAssertEqual(entry.flags, 0)
            XCTAssertEqual(entry.compressionMethod, 0)
            XCTAssertEqual(entry.dosTime, 0)
            XCTAssertEqual(entry.dosDate, 0x0021)
            XCTAssertEqual(entry.extraFieldLength, 0)
            XCTAssertEqual(entry.commentLength, 0)
            XCTAssertEqual(entry.diskNumberStart, 0)
            XCTAssertEqual(entry.internalAttributes, 0)
            XCTAssertEqual(entry.externalAttributes, 0x81A4_0000)
            XCTAssertEqual(entry.compressedSize, entry.uncompressedSize)
        }
    }

    func testReferenceCarrierLocalAndCentralRecordsMatchExactly()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        XCTAssertEqual(
            archive.localEntries.count,
            archive.centralEntries.count
        )

        for (local, central) in zip(
            archive.localEntries,
            archive.centralEntries
        ) {
            XCTAssertEqual(local.path, central.path)
            XCTAssertEqual(local.flags, central.flags)
            XCTAssertEqual(
                local.compressionMethod,
                central.compressionMethod
            )
            XCTAssertEqual(local.dosTime, central.dosTime)
            XCTAssertEqual(local.dosDate, central.dosDate)
            XCTAssertEqual(local.crc32, central.crc32)
            XCTAssertEqual(
                local.compressedSize,
                central.compressedSize
            )
            XCTAssertEqual(
                local.uncompressedSize,
                central.uncompressedSize
            )
            XCTAssertEqual(
                UInt32(local.localHeaderOffset),
                central.localHeaderOffset
            )
        }
    }

    func testReferenceCarrierCRC32AndPayloadOffsetsAreExact()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        for entry in archive.localEntries {
            XCTAssertEqual(
                entry.crc32,
                StrictStoredZIP.crc32(entry.payload)
            )
            XCTAssertEqual(
                value.carrier.exactBytes.subdata(
                    in: entry.payloadRange
                ),
                entry.payload
            )
        }
    }

    func testReferenceCarrierHasNoGapsOverlapsOrTrailingBytes()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        XCTAssertEqual(
            archive.localEntries.first?.localHeaderOffset,
            0
        )

        for index in 1..<archive.localEntries.count {
            XCTAssertEqual(
                archive.localEntries[index - 1].endOffset,
                archive.localEntries[index].localHeaderOffset
            )
        }

        XCTAssertEqual(
            archive.localEntries.last?.endOffset,
            archive.centralDirectoryOffset
        )
        XCTAssertEqual(
            archive.centralDirectoryOffset +
                archive.centralDirectorySize,
            archive.endOfCentralDirectoryOffset
        )
        XCTAssertEqual(
            archive.endOfCentralDirectoryOffset + 22,
            value.carrier.exactBytes.count
        )
        XCTAssertEqual(archive.archiveCommentLength, 0)
    }

    func testRepeatedMaterializationProducesIdenticalCarrierBytes()
        async throws
    {
        let value = try await reference()

        let first = try value.manifest
            .materializePulseledgerCarrier(
                packageSignature: value.packageSignature
            )
        let second = try value.manifest
            .materializePulseledgerCarrier(
                packageSignature: value.packageSignature
            )

        XCTAssertEqual(first, second)
        XCTAssertEqual(first.exactBytes, value.carrier.exactBytes)
        XCTAssertEqual(
            first.carrierSHA256,
            value.carrier.carrierSHA256
        )
    }

    func testCarrierMaterializationDoesNotMutateInputs()
        async throws
    {
        let value = try await reference()
        let manifestBefore = value.manifest
        let signatureBefore = value.packageSignature

        _ = try value.manifest.materializePulseledgerCarrier(
            packageSignature: value.packageSignature
        )

        XCTAssertEqual(value.manifest, manifestBefore)
        XCTAssertEqual(value.packageSignature, signatureBefore)
    }

    func testWriterRejectsManifestMaterializationMismatch()
        async throws
    {
        let value = try await reference()
        let inconsistent = DeviceLedgerManifestMaterialization(
            payloadMembers:
                Array(value.manifest.payloadMembers.dropLast()),
            manifest: value.manifest.manifest
        )

        XCTAssertThrowsError(
            try inconsistent.materializePulseledgerCarrier(
                packageSignature: value.packageSignature
            )
        ) { error in
            XCTAssertEqual(
                error as? DeterministicPulseledgerWriterError,
                .manifestMaterializationMismatch
            )
        }
    }

    func testWriterRejectsPackageSignatureMaterializationMismatch()
        async throws
    {
        let value = try await reference()
        let inconsistent = DevicePackageSignatureMaterialization(
            subject: value.packageSignature.subject,
            signatureInputSHA256:
                Data(repeating: 0, count: 32),
            signature: value.packageSignature.signature,
            document: value.packageSignature.document
        )

        XCTAssertThrowsError(
            try value.manifest.materializePulseledgerCarrier(
                packageSignature: inconsistent
            )
        ) { error in
            XCTAssertEqual(
                error as? DeterministicPulseledgerWriterError,
                .packageSignatureMaterializationMismatch
            )
        }
    }

    func testWriterRejectsPackageSignatureLedgerMismatch()
        async throws
    {
        let value = try await reference()
        let subject = DevicePackageSignatureSubject(
            ledgerID: try LedgerIdentifier(
                "device-ledger:other"
            ),
            observerPublicKeyFingerprintSHA256:
                value.packageSignature.subject
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                value.packageSignature.subject
                    .signedObjectSHA256
        )
        let inconsistent = packageSignatureMaterialization(
            subject: subject,
            signature: value.packageSignature.signature
        )

        XCTAssertThrowsError(
            try value.manifest.materializePulseledgerCarrier(
                packageSignature: inconsistent
            )
        ) { error in
            XCTAssertEqual(
                error as? DeterministicPulseledgerWriterError,
                .packageSignatureLedgerMismatch
            )
        }
    }

    func testWriterRejectsPackageSignatureObserverMismatch()
        async throws
    {
        let value = try await reference()
        let subject = DevicePackageSignatureSubject(
            ledgerID: value.packageSignature.subject.ledgerID,
            observerPublicKeyFingerprintSHA256:
                try SHA256HexDigest(
                    String(repeating: "0", count: 64)
                ),
            signedObjectSHA256:
                value.packageSignature.subject
                    .signedObjectSHA256
        )
        let inconsistent = packageSignatureMaterialization(
            subject: subject,
            signature: value.packageSignature.signature
        )

        XCTAssertThrowsError(
            try value.manifest.materializePulseledgerCarrier(
                packageSignature: inconsistent
            )
        ) { error in
            XCTAssertEqual(
                error as? DeterministicPulseledgerWriterError,
                .packageSignatureObserverMismatch
            )
        }
    }

    func testWriterRejectsPackageSignatureObjectMismatch()
        async throws
    {
        let value = try await reference()
        let subject = DevicePackageSignatureSubject(
            ledgerID: value.packageSignature.subject.ledgerID,
            observerPublicKeyFingerprintSHA256:
                value.packageSignature.subject
                    .observerPublicKeyFingerprintSHA256,
            signedObjectSHA256:
                try SHA256HexDigest(
                    String(repeating: "0", count: 64)
                )
        )
        let inconsistent = packageSignatureMaterialization(
            subject: subject,
            signature: value.packageSignature.signature
        )

        XCTAssertThrowsError(
            try value.manifest.materializePulseledgerCarrier(
                packageSignature: inconsistent
            )
        ) { error in
            XCTAssertEqual(
                error as? DeterministicPulseledgerWriterError,
                .packageSignatureObjectMismatch
            )
        }
    }

    func testStrictInspectionRejectsTrailingDataAndWrongCRC32()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )

        var trailing = value.carrier.exactBytes
        trailing.append(0)
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                trailing,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )

        var wrongCRC = value.carrier.exactBytes
        let crcOffset = try XCTUnwrap(
            archive.localEntries.first
        ).localHeaderOffset + 14
        wrongCRC[crcOffset] ^= 0x01
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                wrongCRC,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )
    }

    func testStrictInspectionRejectsCompressionTimestampAndDescriptorDrift()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )
        let firstOffset = try XCTUnwrap(
            archive.localEntries.first
        ).localHeaderOffset

        let mutations: [(offset: Int, value: UInt8)] = [
            (firstOffset + 8, 8),
            (firstOffset + 10, 1),
            (firstOffset + 6, 8),
        ]

        for mutation in mutations {
            var bytes = value.carrier.exactBytes
            bytes[mutation.offset] = mutation.value
            XCTAssertThrowsError(
                try StrictStoredZIP.parse(
                    bytes,
                    expectedMemberOrder:
                        DeterministicPulseledgerWriter.exactMemberOrder
                )
            )
        }
    }

    func testStrictInspectionRejectsExtraFieldsAndComments()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )
        let firstOffset = try XCTUnwrap(
            archive.localEntries.first
        ).localHeaderOffset

        var localExtra = value.carrier.exactBytes
        localExtra[firstOffset + 28] = 1
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                localExtra,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )

        var archiveComment = value.carrier.exactBytes
        archiveComment[
            archive.endOfCentralDirectoryOffset + 20
        ] = 1
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                archiveComment,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )
    }

    func testStrictInspectionRejectsDuplicateUnsafeAndDirectoryNames()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )
        let source = archive.localEntries[0]
        let target = archive.localEntries[3]
        let targetCentral = archive.centralEntries[3]
        XCTAssertEqual(source.path.utf8.count, target.path.utf8.count)

        let replacements = [
            source.path,
            "../" + String(repeating: "a", count: 46),
            String(repeating: "d", count: 48) + "/",
        ]

        for replacement in replacements {
            XCTAssertEqual(
                replacement.utf8.count,
                target.nameRange.count
            )
            var bytes = value.carrier.exactBytes
            bytes.replaceSubrange(
                target.nameRange,
                with: replacement.utf8
            )
            bytes.replaceSubrange(
                targetCentral.nameRange,
                with: replacement.utf8
            )

            XCTAssertThrowsError(
                try StrictStoredZIP.parse(
                    bytes,
                    expectedMemberOrder:
                        DeterministicPulseledgerWriter.exactMemberOrder
                )
            )
        }
    }

    func testStrictInspectionRejectsCentralMismatchMissingEntriesAndZIP64()
        async throws
    {
        let value = try await reference()
        let archive = try StrictStoredZIP.parse(
            value.carrier.exactBytes,
            expectedMemberOrder:
                DeterministicPulseledgerWriter.exactMemberOrder
        )
        let firstCentral = try XCTUnwrap(
            archive.centralEntries.first
        )

        var centralMismatch = value.carrier.exactBytes
        centralMismatch[firstCentral.centralHeaderOffset + 10] = 8
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                centralMismatch,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )

        var missingEntry = value.carrier.exactBytes
        missingEntry[
            archive.endOfCentralDirectoryOffset + 10
        ] = 9
        missingEntry[
            archive.endOfCentralDirectoryOffset + 8
        ] = 9
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                missingEntry,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )

        var zip64 = value.carrier.exactBytes
        zip64[
            archive.endOfCentralDirectoryOffset + 10
        ] = 0xFF
        zip64[
            archive.endOfCentralDirectoryOffset + 11
        ] = 0xFF
        XCTAssertThrowsError(
            try StrictStoredZIP.parse(
                zip64,
                expectedMemberOrder:
                    DeterministicPulseledgerWriter.exactMemberOrder
            )
        )
    }
}

private enum StrictStoredZIPError: Error, Equatable {
    case inputTooSmall
    case endOfCentralDirectoryMissing
    case trailingData
    case multiDiskArchive
    case entryCountMismatch
    case zip64Forbidden
    case centralDirectoryBoundsInvalid
    case localHeaderInvalid
    case centralHeaderInvalid
    case unsafeMemberPath(String)
    case duplicateMemberPath(String)
    case memberOrderMismatch
    case unsupportedFlags
    case unsupportedCompression
    case timestampMismatch
    case extraFieldForbidden
    case commentForbidden
    case regularFileAttributesRequired
    case localCentralMismatch(String)
    case crc32Mismatch(String)
    case localGapOrOverlap
    case centralDirectoryGapOrOverlap
}

private struct StrictStoredZIP {
    struct LocalEntry {
        let path: String
        let localHeaderOffset: Int
        let nameRange: Range<Int>
        let payloadRange: Range<Int>
        let endOffset: Int
        let versionNeeded: UInt16
        let flags: UInt16
        let compressionMethod: UInt16
        let dosTime: UInt16
        let dosDate: UInt16
        let crc32: UInt32
        let compressedSize: UInt32
        let uncompressedSize: UInt32
        let extraFieldLength: UInt16
        let payload: Data
    }

    struct CentralEntry {
        let path: String
        let centralHeaderOffset: Int
        let nameRange: Range<Int>
        let endOffset: Int
        let versionMadeBy: UInt16
        let versionNeeded: UInt16
        let flags: UInt16
        let compressionMethod: UInt16
        let dosTime: UInt16
        let dosDate: UInt16
        let crc32: UInt32
        let compressedSize: UInt32
        let uncompressedSize: UInt32
        let extraFieldLength: UInt16
        let commentLength: UInt16
        let diskNumberStart: UInt16
        let internalAttributes: UInt16
        let externalAttributes: UInt32
        let localHeaderOffset: UInt32
    }

    let localEntries: [LocalEntry]
    let centralEntries: [CentralEntry]
    let centralDirectoryOffset: Int
    let centralDirectorySize: Int
    let endOfCentralDirectoryOffset: Int
    let archiveCommentLength: Int

    static func parse(
        _ data: Data,
        expectedMemberOrder: [String]
    ) throws -> StrictStoredZIP {
        let bytes = Array(data)
        guard bytes.count >= 22 else {
            throw StrictStoredZIPError.inputTooSmall
        }

        let eocdOffset = bytes.count - 22
        guard readUInt32(bytes, at: eocdOffset) ==
                0x0605_4B50 else {
            throw StrictStoredZIPError
                .endOfCentralDirectoryMissing
        }

        let diskNumber = readUInt16(
            bytes,
            at: eocdOffset + 4
        )
        let centralDirectoryDisk = readUInt16(
            bytes,
            at: eocdOffset + 6
        )
        let entriesOnDisk = readUInt16(
            bytes,
            at: eocdOffset + 8
        )
        let totalEntries = readUInt16(
            bytes,
            at: eocdOffset + 10
        )
        let centralSize = readUInt32(
            bytes,
            at: eocdOffset + 12
        )
        let centralOffset = readUInt32(
            bytes,
            at: eocdOffset + 16
        )
        let commentLength = readUInt16(
            bytes,
            at: eocdOffset + 20
        )

        guard commentLength == 0 else {
            throw StrictStoredZIPError.commentForbidden
        }
        guard eocdOffset + 22 + Int(commentLength) ==
                bytes.count else {
            throw StrictStoredZIPError.trailingData
        }
        guard diskNumber == 0,
              centralDirectoryDisk == 0 else {
            throw StrictStoredZIPError.multiDiskArchive
        }
        guard entriesOnDisk != 0xFFFF,
              totalEntries != 0xFFFF,
              centralSize != 0xFFFF_FFFF,
              centralOffset != 0xFFFF_FFFF else {
            throw StrictStoredZIPError.zip64Forbidden
        }
        guard entriesOnDisk == totalEntries,
              Int(totalEntries) == expectedMemberOrder.count else {
            throw StrictStoredZIPError.entryCountMismatch
        }

        let centralDirectoryOffset = Int(centralOffset)
        let centralDirectorySize = Int(centralSize)
        guard centralDirectoryOffset >= 0,
              centralDirectorySize >= 0,
              centralDirectoryOffset + centralDirectorySize ==
                eocdOffset else {
            throw StrictStoredZIPError
                .centralDirectoryBoundsInvalid
        }

        let localEntries = try parseLocalEntries(
            bytes,
            count: Int(totalEntries),
            centralDirectoryOffset: centralDirectoryOffset
        )
        let centralEntries = try parseCentralEntries(
            bytes,
            count: Int(totalEntries),
            centralDirectoryOffset: centralDirectoryOffset,
            endOfCentralDirectoryOffset: eocdOffset
        )

        let localPaths = localEntries.map(\.path)
        let centralPaths = centralEntries.map(\.path)
        guard localPaths == expectedMemberOrder,
              centralPaths == expectedMemberOrder else {
            throw StrictStoredZIPError.memberOrderMismatch
        }
        guard Set(localPaths).count == localPaths.count,
              Set(centralPaths).count == centralPaths.count else {
            throw StrictStoredZIPError.duplicateMemberPath(
                "duplicate"
            )
        }

        for (local, central) in zip(
            localEntries,
            centralEntries
        ) {
            guard local.path == central.path,
                  local.versionNeeded == central.versionNeeded,
                  local.flags == central.flags,
                  local.compressionMethod ==
                    central.compressionMethod,
                  local.dosTime == central.dosTime,
                  local.dosDate == central.dosDate,
                  local.crc32 == central.crc32,
                  local.compressedSize == central.compressedSize,
                  local.uncompressedSize == central.uncompressedSize,
                  UInt32(local.localHeaderOffset) ==
                    central.localHeaderOffset else {
                throw StrictStoredZIPError.localCentralMismatch(
                    local.path
                )
            }
        }

        return StrictStoredZIP(
            localEntries: localEntries,
            centralEntries: centralEntries,
            centralDirectoryOffset: centralDirectoryOffset,
            centralDirectorySize: centralDirectorySize,
            endOfCentralDirectoryOffset: eocdOffset,
            archiveCommentLength: Int(commentLength)
        )
    }

    static func crc32(
        _ data: Data
    ) -> UInt32 {
        var crc: UInt32 = 0xFFFF_FFFF
        for byte in data {
            crc ^= UInt32(byte)
            for _ in 0..<8 {
                let mask = UInt32.zero &- (crc & 1)
                crc = (crc >> 1) ^
                    (0xEDB8_8320 & mask)
            }
        }
        return crc ^ 0xFFFF_FFFF
    }

    private static func parseLocalEntries(
        _ bytes: [UInt8],
        count: Int,
        centralDirectoryOffset: Int
    ) throws -> [LocalEntry] {
        var cursor = 0
        var result: [LocalEntry] = []
        result.reserveCapacity(count)

        for _ in 0..<count {
            let headerOffset = cursor
            guard readUInt32(bytes, at: cursor) ==
                    0x0403_4B50 else {
                throw StrictStoredZIPError.localHeaderInvalid
            }
            guard hasRange(bytes, offset: cursor, count: 30) else {
                throw StrictStoredZIPError.localHeaderInvalid
            }

            let versionNeeded = readUInt16(
                bytes,
                at: cursor + 4
            )
            let flags = readUInt16(bytes, at: cursor + 6)
            let compression = readUInt16(
                bytes,
                at: cursor + 8
            )
            let dosTime = readUInt16(
                bytes,
                at: cursor + 10
            )
            let dosDate = readUInt16(
                bytes,
                at: cursor + 12
            )
            let crc = readUInt32(bytes, at: cursor + 14)
            let compressedSize = readUInt32(
                bytes,
                at: cursor + 18
            )
            let uncompressedSize = readUInt32(
                bytes,
                at: cursor + 22
            )
            let nameLength = Int(
                readUInt16(bytes, at: cursor + 26)
            )
            let extraLength = readUInt16(
                bytes,
                at: cursor + 28
            )

            guard versionNeeded == 20 else {
                throw StrictStoredZIPError.localHeaderInvalid
            }
            guard flags == 0 else {
                throw StrictStoredZIPError.unsupportedFlags
            }
            guard compression == 0 else {
                throw StrictStoredZIPError
                    .unsupportedCompression
            }
            guard dosTime == 0,
                  dosDate == 0x0021 else {
                throw StrictStoredZIPError.timestampMismatch
            }
            guard extraLength == 0 else {
                throw StrictStoredZIPError.extraFieldForbidden
            }
            guard compressedSize == uncompressedSize else {
                throw StrictStoredZIPError
                    .unsupportedCompression
            }

            let nameStart = cursor + 30
            let nameRange = nameStart..<(nameStart + nameLength)
            guard hasRange(
                bytes,
                offset: nameRange.lowerBound,
                count: nameRange.count
            ) else {
                throw StrictStoredZIPError.localHeaderInvalid
            }
            let path = try decodeAndValidatePath(
                bytes[nameRange],
                existing: result.map(\.path)
            )

            let payloadStart = nameRange.upperBound
            let payloadEnd = payloadStart + Int(compressedSize)
            guard payloadEnd <= centralDirectoryOffset,
                  hasRange(
                    bytes,
                    offset: payloadStart,
                    count: Int(compressedSize)
                  ) else {
                throw StrictStoredZIPError.localGapOrOverlap
            }
            let payloadRange = payloadStart..<payloadEnd
            let payload = Data(bytes[payloadRange])
            guard crc32(payload) == crc else {
                throw StrictStoredZIPError.crc32Mismatch(path)
            }

            result.append(
                LocalEntry(
                    path: path,
                    localHeaderOffset: headerOffset,
                    nameRange: nameRange,
                    payloadRange: payloadRange,
                    endOffset: payloadEnd,
                    versionNeeded: versionNeeded,
                    flags: flags,
                    compressionMethod: compression,
                    dosTime: dosTime,
                    dosDate: dosDate,
                    crc32: crc,
                    compressedSize: compressedSize,
                    uncompressedSize: uncompressedSize,
                    extraFieldLength: extraLength,
                    payload: payload
                )
            )
            cursor = payloadEnd
        }

        guard cursor == centralDirectoryOffset else {
            throw StrictStoredZIPError.localGapOrOverlap
        }
        return result
    }

    private static func parseCentralEntries(
        _ bytes: [UInt8],
        count: Int,
        centralDirectoryOffset: Int,
        endOfCentralDirectoryOffset: Int
    ) throws -> [CentralEntry] {
        var cursor = centralDirectoryOffset
        var result: [CentralEntry] = []
        result.reserveCapacity(count)

        for _ in 0..<count {
            let headerOffset = cursor
            guard readUInt32(bytes, at: cursor) ==
                    0x0201_4B50,
                  hasRange(bytes, offset: cursor, count: 46) else {
                throw StrictStoredZIPError.centralHeaderInvalid
            }

            let versionMadeBy = readUInt16(
                bytes,
                at: cursor + 4
            )
            let versionNeeded = readUInt16(
                bytes,
                at: cursor + 6
            )
            let flags = readUInt16(bytes, at: cursor + 8)
            let compression = readUInt16(
                bytes,
                at: cursor + 10
            )
            let dosTime = readUInt16(
                bytes,
                at: cursor + 12
            )
            let dosDate = readUInt16(
                bytes,
                at: cursor + 14
            )
            let crc = readUInt32(bytes, at: cursor + 16)
            let compressedSize = readUInt32(
                bytes,
                at: cursor + 20
            )
            let uncompressedSize = readUInt32(
                bytes,
                at: cursor + 24
            )
            let nameLength = Int(
                readUInt16(bytes, at: cursor + 28)
            )
            let extraLength = readUInt16(
                bytes,
                at: cursor + 30
            )
            let commentLength = readUInt16(
                bytes,
                at: cursor + 32
            )
            let diskNumberStart = readUInt16(
                bytes,
                at: cursor + 34
            )
            let internalAttributes = readUInt16(
                bytes,
                at: cursor + 36
            )
            let externalAttributes = readUInt32(
                bytes,
                at: cursor + 38
            )
            let localHeaderOffset = readUInt32(
                bytes,
                at: cursor + 42
            )

            guard versionMadeBy == 0x0314,
                  versionNeeded == 20 else {
                throw StrictStoredZIPError.centralHeaderInvalid
            }
            guard flags == 0 else {
                throw StrictStoredZIPError.unsupportedFlags
            }
            guard compression == 0 else {
                throw StrictStoredZIPError
                    .unsupportedCompression
            }
            guard dosTime == 0,
                  dosDate == 0x0021 else {
                throw StrictStoredZIPError.timestampMismatch
            }
            guard extraLength == 0 else {
                throw StrictStoredZIPError.extraFieldForbidden
            }
            guard commentLength == 0 else {
                throw StrictStoredZIPError.commentForbidden
            }
            guard diskNumberStart == 0,
                  internalAttributes == 0,
                  externalAttributes == 0x81A4_0000 else {
                throw StrictStoredZIPError
                    .regularFileAttributesRequired
            }
            guard compressedSize == uncompressedSize else {
                throw StrictStoredZIPError
                    .unsupportedCompression
            }

            let nameStart = cursor + 46
            let nameRange = nameStart..<(nameStart + nameLength)
            guard hasRange(
                bytes,
                offset: nameRange.lowerBound,
                count: nameRange.count
            ) else {
                throw StrictStoredZIPError.centralHeaderInvalid
            }
            let path = try decodeAndValidatePath(
                bytes[nameRange],
                existing: result.map(\.path)
            )

            let endOffset = nameRange.upperBound
            guard endOffset <= endOfCentralDirectoryOffset else {
                throw StrictStoredZIPError
                    .centralDirectoryGapOrOverlap
            }

            result.append(
                CentralEntry(
                    path: path,
                    centralHeaderOffset: headerOffset,
                    nameRange: nameRange,
                    endOffset: endOffset,
                    versionMadeBy: versionMadeBy,
                    versionNeeded: versionNeeded,
                    flags: flags,
                    compressionMethod: compression,
                    dosTime: dosTime,
                    dosDate: dosDate,
                    crc32: crc,
                    compressedSize: compressedSize,
                    uncompressedSize: uncompressedSize,
                    extraFieldLength: extraLength,
                    commentLength: commentLength,
                    diskNumberStart: diskNumberStart,
                    internalAttributes: internalAttributes,
                    externalAttributes: externalAttributes,
                    localHeaderOffset: localHeaderOffset
                )
            )
            cursor = endOffset
        }

        guard cursor == endOfCentralDirectoryOffset else {
            throw StrictStoredZIPError
                .centralDirectoryGapOrOverlap
        }
        return result
    }

    private static func decodeAndValidatePath(
        _ bytes: ArraySlice<UInt8>,
        existing: [String]
    ) throws -> String {
        guard !bytes.isEmpty,
              bytes.allSatisfy({ $0 < 0x80 }),
              let path = String(
                bytes: bytes,
                encoding: .ascii
              ),
              !path.hasPrefix("/"),
              !path.hasSuffix("/"),
              !path.contains("\\"),
              !bytes.contains(0) else {
            throw StrictStoredZIPError.unsafeMemberPath(
                "invalid"
            )
        }

        let components = path.split(
            separator: "/",
            omittingEmptySubsequences: false
        )
        guard components.allSatisfy({
            !$0.isEmpty && $0 != "." && $0 != ".."
        }) else {
            throw StrictStoredZIPError.unsafeMemberPath(path)
        }
        guard !existing.contains(path) else {
            throw StrictStoredZIPError
                .duplicateMemberPath(path)
        }
        return path
    }

    private static func hasRange(
        _ bytes: [UInt8],
        offset: Int,
        count: Int
    ) -> Bool {
        offset >= 0 &&
            count >= 0 &&
            offset <= bytes.count &&
            count <= bytes.count - offset
    }

    private static func readUInt16(
        _ bytes: [UInt8],
        at offset: Int
    ) -> UInt16 {
        guard hasRange(bytes, offset: offset, count: 2) else {
            return 0
        }
        return UInt16(bytes[offset]) |
            (UInt16(bytes[offset + 1]) << 8)
    }

    private static func readUInt32(
        _ bytes: [UInt8],
        at offset: Int
    ) -> UInt32 {
        guard hasRange(bytes, offset: offset, count: 4) else {
            return 0
        }
        return UInt32(bytes[offset]) |
            (UInt32(bytes[offset + 1]) << 8) |
            (UInt32(bytes[offset + 2]) << 16) |
            (UInt32(bytes[offset + 3]) << 24)
    }
}
