import Foundation

/// An actor-isolated backend that retains one exact ledger image in memory.
///
/// `InMemoryLedgerBackend` provides process-lifetime persistence. Retained bytes
/// survive individual method calls but are not expected to survive backend
/// deallocation, process termination, or application restart.
///
/// The backend treats ledger bytes as opaque. It does not parse, validate,
/// canonicalize, transform, sign, verify, or reinterpret them.
///
/// Defensive byte snapshots are taken on both replacement and loading so that
/// callers cannot mutate the retained image through shared storage.
///
/// This backend does not establish observation coverage, device security,
/// external validation, device-control authority, release decisions, or release
/// authority.
public actor InMemoryLedgerBackend: LedgerBackend {
    /// Declares that retained bytes exist only for this backend instance or
    /// hosting-process lifetime.
    public nonisolated let persistence: LedgerBackendPersistence = .processLifetime

    private var retainedLedgerBytes: Data?

    /// Creates an in-memory backend.
    ///
    /// - Parameter initialLedgerBytes:
    ///   Optional exact ledger bytes to retain immediately.
    ///   `nil` means that no ledger image is present.
    ///   An empty `Data` value remains distinct from `nil` and is retained
    ///   exactly as supplied.
    public init(initialLedgerBytes: Data? = nil) {
        retainedLedgerBytes = initialLedgerBytes.map { Data($0) }
    }

    /// Returns an exact snapshot of the currently retained ledger bytes.
    ///
    /// Returns `nil` when no ledger image is retained.
    public func loadLedgerBytes() async throws -> Data? {
        retainedLedgerBytes.map { Data($0) }
    }

    /// Atomically replaces the retained ledger image.
    ///
    /// Actor isolation serializes replacement with every load and removal.
    /// The supplied bytes are copied without parsing or transformation.
    public func replaceLedgerBytes(_ bytes: Data) async throws {
        retainedLedgerBytes = Data(bytes)
    }

    /// Removes the retained ledger image.
    ///
    /// Repeated calls are successful and preserve idempotent removal behavior.
    public func removeLedgerBytes() async throws {
        retainedLedgerBytes = nil
    }
}
