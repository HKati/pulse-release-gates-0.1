import Foundation

/// A backend that intentionally retains no ledger bytes.
///
/// `NullLedgerBackend` provides an explicit no-persistence implementation of
/// `LedgerBackend`. It is suitable where the ledger core must exercise the
/// backend boundary without retaining a ledger image.
///
/// The backend does not inspect, validate, canonicalize, transform, sign, or
/// verify the supplied bytes. It discards them exactly because its declared
/// persistence class is `.none`.
///
/// This backend does not create observation coverage, device-security claims,
/// device-control authority, release decisions, or release authority.
public struct NullLedgerBackend: LedgerBackend, Sendable {
    /// Declares that this backend retains no ledger bytes.
    public let persistence: LedgerBackendPersistence = .none

    public init() {}

    /// Always returns `nil` because no ledger image is retained.
    public func loadLedgerBytes() async throws -> Data? {
        nil
    }

    /// Accepts and intentionally discards the supplied bytes.
    ///
    /// No parsing or byte transformation is performed.
    public func replaceLedgerBytes(_ bytes: Data) async throws {
        _ = bytes
    }

    /// Performs no work because there is no retained ledger image.
    ///
    /// Repeated calls remain successful and therefore preserve the required
    /// idempotent removal behavior.
    public func removeLedgerBytes() async throws {}
}
