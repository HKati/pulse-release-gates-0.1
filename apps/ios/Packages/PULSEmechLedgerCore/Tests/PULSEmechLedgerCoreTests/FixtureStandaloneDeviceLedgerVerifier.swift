import Foundation
@testable import PULSEmechLedgerCore

enum FixtureStandaloneDeviceLedgerVerifierError:
    Error,
    Sendable,
    Equatable
{
    case repositoryRootUnavailable
    case verifierUnavailable
    case referenceReportUnavailable
    case unsafeCarrierFileName
    case temporaryDirectoryCreationFailed
    case carrierWriteFailed
    case outputCaptureFileCreationFailed
    case outputCaptureReadFailed
    case carrierTooSmall
    case endOfCentralDirectoryMissing
    case zip64Forbidden
    case entryCountMismatch
    case localHeaderInvalid
    case centralHeaderInvalid
    case localCentralMismatch(path: String)
    case memberNotFound(path: String)
    case packageSignatureMarkerMissing
    case unexpectedPackageSignaturePrefix(UInt8)
}

struct StandaloneDeviceLedgerVerifierExecution:
    Sendable,
    Equatable
{
    let terminationStatus: Int32
    let standardOutput: Data
    let standardError: Data

    init(
        terminationStatus: Int32,
        standardOutput: Data,
        standardError: Data
    ) {
        self.terminationStatus = terminationStatus
        self.standardOutput = Data(standardOutput)
        self.standardError = Data(standardError)
    }
}

/// Test-only runner for the separately implemented Python verifier.
///
/// This fixture writes one exact Swift-produced carrier into an isolated
/// temporary directory and executes the repository verifier as a separate
/// process. It does not import producer code into the verifier and does not
/// reinterpret the returned canonical report.
enum FixtureStandaloneDeviceLedgerVerifier {
    static let referenceCarrierFileName =
        "pulsemech_device_transition_ledger_reference_v0.pulseledger"

    static let verifierRelativePath =
        "tools/verify_pulsemech_device_ledger_v0.py"

    static let referenceReportRelativePath =
        "examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json"

    static let expectedObserverFingerprint =
        "f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6"

    static func run(
        carrierBytes: Data,
        carrierFileName: String = referenceCarrierFileName
    ) throws -> StandaloneDeviceLedgerVerifierExecution {
        guard isSafeCarrierFileName(carrierFileName) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .unsafeCarrierFileName
        }

        let repositoryRoot = try repositoryRoot()
        let verifierURL = repositoryRoot.appendingPathComponent(
            verifierRelativePath
        )
        guard FileManager.default.isReadableFile(
            atPath: verifierURL.path
        ) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .verifierUnavailable
        }

        let temporaryDirectory = FileManager.default
            .temporaryDirectory
            .appendingPathComponent(
                "pulsemech-swift-verifier-roundtrip-\(UUID().uuidString)",
                isDirectory: true
            )

        do {
            try FileManager.default.createDirectory(
                at: temporaryDirectory,
                withIntermediateDirectories: false
            )
        } catch {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .temporaryDirectoryCreationFailed
        }
        defer {
            try? FileManager.default.removeItem(
                at: temporaryDirectory
            )
        }

        let carrierURL = temporaryDirectory.appendingPathComponent(
            carrierFileName
        )
        do {
            try carrierBytes.write(
                to: carrierURL,
                options: [.atomic]
            )
        } catch {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .carrierWriteFailed
        }

        let standardOutputURL = temporaryDirectory
            .appendingPathComponent("verifier.stdout")
        let standardErrorURL = temporaryDirectory
            .appendingPathComponent("verifier.stderr")
        let standardOutput = try makeOutputCaptureHandle(
            at: standardOutputURL
        )
        let standardError = try makeOutputCaptureHandle(
            at: standardErrorURL
        )
        defer {
            try? standardOutput.close()
            try? standardError.close()
        }

        let process = Process()
        process.executableURL = URL(
            fileURLWithPath: "/usr/bin/env"
        )
        process.arguments = [
            "python3",
            verifierURL.path,
            carrierURL.path,
            "--expected-observer-fingerprint",
            expectedObserverFingerprint,
        ]
        process.currentDirectoryURL = repositoryRoot

        var environment = ProcessInfo.processInfo.environment
        environment["LANG"] = "C.UTF-8"
        environment["LC_ALL"] = "C.UTF-8"
        environment["TZ"] = "UTC"
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONHASHSEED"] = "0"
        process.environment = environment
        process.standardInput = FileHandle.nullDevice
        process.standardOutput = standardOutput
        process.standardError = standardError

        try process.run()
        process.waitUntilExit()

        return StandaloneDeviceLedgerVerifierExecution(
            terminationStatus: process.terminationStatus,
            standardOutput: try readCapturedOutput(
                from: standardOutput
            ),
            standardError: try readCapturedOutput(
                from: standardError
            )
        )
    }

    private static func makeOutputCaptureHandle(
        at url: URL
    ) throws -> FileHandle {
        guard FileManager.default.createFile(
            atPath: url.path,
            contents: nil
        ) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .outputCaptureFileCreationFailed
        }

        do {
            return try FileHandle(
                forUpdating: url
            )
        } catch {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .outputCaptureFileCreationFailed
        }
    }

    private static func readCapturedOutput(
        from handle: FileHandle
    ) throws -> Data {
        do {
            try handle.seek(toOffset: 0)
            return try handle.readToEnd() ?? Data()
        } catch {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .outputCaptureReadFailed
        }
    }

    static func referenceReportBytes() throws -> Data {
        let path = try repositoryRoot().appendingPathComponent(
            referenceReportRelativePath
        )
        guard FileManager.default.isReadableFile(
            atPath: path.path
        ) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .referenceReportUnavailable
        }
        return try Data(contentsOf: path)
    }

    /// Creates one CRC-consistent carrier mutation by changing the first
    /// Base64 character of the package signature from `O` to `P` and updating
    /// the corresponding local and central CRC32 fields.
    ///
    /// The resulting ZIP remains structurally valid and reaches the package
    /// ECDSA equation check. The manifest, package-signature subject, and every
    /// other member remain unchanged.
    static func crcConsistentPackageSignatureTamper(
        _ carrierBytes: Data
    ) throws -> Data {
        var bytes = Array(carrierBytes)
        let locations = try locateMembers(bytes)
        let targetPath = DeviceLedgerManifest.packageSignaturePath

        guard let target = locations.first(where: {
            $0.path == targetPath
        }) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .memberNotFound(path: targetPath)
        }

        let payload = Data(bytes[target.payloadRange])
        let marker = Data("\"signature_base64\":\"".utf8)
        guard let markerRange = payload.range(of: marker) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .packageSignatureMarkerMissing
        }
        let relativeSignatureIndex = markerRange.upperBound
        guard relativeSignatureIndex < payload.endIndex else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .packageSignatureMarkerMissing
        }
        let signatureIndex =
            target.payloadRange.lowerBound + relativeSignatureIndex
        guard bytes[signatureIndex] == 0x4F else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .unexpectedPackageSignaturePrefix(
                    bytes[signatureIndex]
                )
        }
        bytes[signatureIndex] = 0x50

        let mutatedPayload = Data(bytes[target.payloadRange])
        let mutatedCRC32 = crc32(mutatedPayload)
        writeUInt32(
            mutatedCRC32,
            to: &bytes,
            at: target.localCRC32Offset
        )
        writeUInt32(
            mutatedCRC32,
            to: &bytes,
            at: target.centralCRC32Offset
        )

        return Data(bytes)
    }

    private static func repositoryRoot() throws -> URL {
        if let workspace =
            ProcessInfo.processInfo.environment["GITHUB_WORKSPACE"]
        {
            let candidate = URL(
                fileURLWithPath: workspace,
                isDirectory: true
            )
            if FileManager.default.isReadableFile(
                atPath: candidate.appendingPathComponent(
                    verifierRelativePath
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

        guard FileManager.default.isReadableFile(
            atPath: candidate.appendingPathComponent(
                verifierRelativePath
            ).path
        ) else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .repositoryRootUnavailable
        }
        return candidate
    }

    private static func isSafeCarrierFileName(
        _ value: String
    ) -> Bool {
        let bytes = Array(value.utf8)
        return !bytes.isEmpty &&
            bytes.allSatisfy({ $0 < 0x80 }) &&
            !value.contains("/") &&
            !value.contains("\\") &&
            !bytes.contains(0) &&
            value.hasSuffix(".pulseledger")
    }

    private static func locateMembers(
        _ bytes: [UInt8]
    ) throws -> [ZIPMemberLocation] {
        guard bytes.count >= 22 else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .carrierTooSmall
        }

        let endOfCentralDirectoryOffset = bytes.count - 22
        guard readUInt32(
            bytes,
            at: endOfCentralDirectoryOffset
        ) == 0x0605_4B50 else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .endOfCentralDirectoryMissing
        }

        let entryCount = readUInt16(
            bytes,
            at: endOfCentralDirectoryOffset + 10
        )
        let centralDirectorySize = readUInt32(
            bytes,
            at: endOfCentralDirectoryOffset + 12
        )
        let centralDirectoryOffset = readUInt32(
            bytes,
            at: endOfCentralDirectoryOffset + 16
        )

        guard entryCount != 0xFFFF,
              centralDirectorySize != 0xFFFF_FFFF,
              centralDirectoryOffset != 0xFFFF_FFFF else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .zip64Forbidden
        }
        guard Int(entryCount) ==
                DeterministicPulseledgerWriter
                    .exactMemberOrder.count else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .entryCountMismatch
        }

        let centralOffset = Int(centralDirectoryOffset)
        let centralSize = Int(centralDirectorySize)
        guard centralOffset + centralSize ==
                endOfCentralDirectoryOffset else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .centralHeaderInvalid
        }

        var localLocations: [String: ZIPMemberLocation] = [:]
        var localOrder: [String] = []
        var cursor = 0

        for _ in 0..<Int(entryCount) {
            guard hasRange(bytes, offset: cursor, count: 30),
                  readUInt32(bytes, at: cursor) ==
                    0x0403_4B50 else {
                throw FixtureStandaloneDeviceLedgerVerifierError
                    .localHeaderInvalid
            }

            let compressedSize = Int(
                readUInt32(bytes, at: cursor + 18)
            )
            let nameLength = Int(
                readUInt16(bytes, at: cursor + 26)
            )
            let extraLength = Int(
                readUInt16(bytes, at: cursor + 28)
            )
            let nameStart = cursor + 30
            let payloadStart =
                nameStart + nameLength + extraLength
            let payloadEnd = payloadStart + compressedSize

            guard hasRange(
                bytes,
                offset: nameStart,
                count: nameLength
            ),
            hasRange(
                bytes,
                offset: payloadStart,
                count: compressedSize
            ),
            payloadEnd <= centralOffset,
            let path = String(
                bytes: bytes[nameStart..<(nameStart + nameLength)],
                encoding: .ascii
            ) else {
                throw FixtureStandaloneDeviceLedgerVerifierError
                    .localHeaderInvalid
            }

            localOrder.append(path)
            localLocations[path] = ZIPMemberLocation(
                path: path,
                localHeaderOffset: cursor,
                payloadRange: payloadStart..<payloadEnd,
                localCRC32Offset: cursor + 14,
                centralCRC32Offset: -1
            )
            cursor = payloadEnd
        }

        guard cursor == centralOffset,
              localOrder ==
                DeterministicPulseledgerWriter
                    .exactMemberOrder else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .localHeaderInvalid
        }

        var centralOrder: [String] = []
        cursor = centralOffset

        for _ in 0..<Int(entryCount) {
            guard hasRange(bytes, offset: cursor, count: 46),
                  readUInt32(bytes, at: cursor) ==
                    0x0201_4B50 else {
                throw FixtureStandaloneDeviceLedgerVerifierError
                    .centralHeaderInvalid
            }

            let nameLength = Int(
                readUInt16(bytes, at: cursor + 28)
            )
            let extraLength = Int(
                readUInt16(bytes, at: cursor + 30)
            )
            let commentLength = Int(
                readUInt16(bytes, at: cursor + 32)
            )
            let nameStart = cursor + 46
            let endOffset =
                nameStart + nameLength +
                extraLength + commentLength

            guard hasRange(
                bytes,
                offset: nameStart,
                count: nameLength
            ),
            endOffset <= endOfCentralDirectoryOffset,
            let path = String(
                bytes: bytes[nameStart..<(nameStart + nameLength)],
                encoding: .ascii
            ),
            let local = localLocations[path] else {
                throw FixtureStandaloneDeviceLedgerVerifierError
                    .centralHeaderInvalid
            }

            let localHeaderOffset = Int(
                readUInt32(bytes, at: cursor + 42)
            )
            guard localHeaderOffset ==
                    local.localHeaderOffset else {
                throw FixtureStandaloneDeviceLedgerVerifierError
                    .localCentralMismatch(path: path)
            }

            centralOrder.append(path)
            localLocations[path] = ZIPMemberLocation(
                path: local.path,
                localHeaderOffset: local.localHeaderOffset,
                payloadRange: local.payloadRange,
                localCRC32Offset: local.localCRC32Offset,
                centralCRC32Offset: cursor + 16
            )
            cursor = endOffset
        }

        guard cursor == endOfCentralDirectoryOffset,
              centralOrder == localOrder else {
            throw FixtureStandaloneDeviceLedgerVerifierError
                .centralHeaderInvalid
        }

        return localOrder.compactMap {
            localLocations[$0]
        }
    }

    private static func crc32(
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

    private static func writeUInt32(
        _ value: UInt32,
        to bytes: inout [UInt8],
        at offset: Int
    ) {
        precondition(hasRange(bytes, offset: offset, count: 4))
        bytes[offset] = UInt8(truncatingIfNeeded: value)
        bytes[offset + 1] = UInt8(
            truncatingIfNeeded: value >> 8
        )
        bytes[offset + 2] = UInt8(
            truncatingIfNeeded: value >> 16
        )
        bytes[offset + 3] = UInt8(
            truncatingIfNeeded: value >> 24
        )
    }
}

private struct ZIPMemberLocation:
    Sendable,
    Equatable
{
    let path: String
    let localHeaderOffset: Int
    let payloadRange: Range<Int>
    let localCRC32Offset: Int
    let centralCRC32Offset: Int
}
