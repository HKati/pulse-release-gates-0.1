import Foundation

/// Declares how long a backend retains the exact ledger bytes supplied to it.
///
/// This is an operational property only. It does not establish record validity,
/// device security, observation completeness, external validation, device-control
/// authority, or release authority.
public enum LedgerBackendPersistence: Sendable, Equatable {
    /// The backend retains no ledger bytes. Reads must return `nil`.
    case none

    /// Ledger bytes may be retained only for the lifetime of the backend
    /// instance or the hosting process.
    case processLifetime

    /// Ledger bytes are intended to survive backend recreation according to the
    /// concrete implementation's documented storage contract.
    case persistent
}

/// Persistence boundary for one PULSEmech Device Transition Ledger.
///
/// A backend receives opaque canonical JSON bytes produced by the ledger core.
/// It must not parse and reserialize them, append or remove a trailing newline,
/// add a BOM, or change string normalization, escaping, object-key order, or
/// whitespace.
///
/// A backend is not an observation source, canonicalizer, chain builder, signer,
/// verifier, device-control authority, or release authority.
public protocol LedgerBackend: Sendable {
    /// The retention behavior of this backend.
    var persistence: LedgerBackendPersistence { get }

    /// Returns the exact retained ledger bytes.
    ///
    /// `nil` means that no ledger image is retained. It must not be interpreted
    /// as an empty canonical ledger document.
    func loadLedgerBytes() async throws -> Data?

    /// Replaces the retained ledger image with the exact supplied bytes.
    ///
    /// Backends whose `persistence` is not `.none` must make this replacement
    /// atomic: either every byte becomes readable exactly as supplied, or the
    /// operation throws without exposing a partial replacement.
    ///
    /// A `.none` backend may discard the bytes, but it must continue to report
    /// `.none` and `loadLedgerBytes()` must return `nil`.
    func replaceLedgerBytes(_ bytes: Data) async throws

    /// Removes any retained ledger image.
    ///
    /// The operation must be idempotent.
    func removeLedgerBytes() async throws
}
