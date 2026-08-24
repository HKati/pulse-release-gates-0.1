import Foundation

/// Construction failures for the normalized Device Ledger v0 network-path
/// state.
public enum NetworkPathStateError: Error, Sendable, Equatable {
    /// Every interface reported as used must also be present in the normalized
    /// available-interface set.
    case usedInterfaceNotAvailable(NetworkPathUsedInterfaceType)
}

/// Normalized `NWPath.status` values admitted by the Device Ledger v0
/// observation contract.
public enum NetworkPathStatus: String, Sendable, Equatable, CaseIterable {
    case satisfied
    case unsatisfied
    case requiresConnection = "requires_connection"
    case unknown
}

/// Interface classes admitted in the normalized available-interface list.
///
/// `unknown` represents a future platform interface class that is not named by
/// the v0 contract. No interface name, index, address, endpoint, gateway, SSID,
/// or BSSID is retained.
public enum NetworkPathAvailableInterfaceType: String, Sendable, Equatable, Hashable, CaseIterable {
    case wifi
    case cellular
    case wiredEthernet = "wired_ethernet"
    case loopback
    case other
    case unknown
}

/// Interface classes that can be represented as actively used by the v0
/// producer.
///
/// The contract intentionally has no `unknown` used-interface value. A future
/// interface class may be visible in the available set as `unknown`, but the v0
/// producer cannot claim that unknown class as the path's used interface.
public enum NetworkPathUsedInterfaceType: String, Sendable, Equatable, Hashable, CaseIterable {
    case wifi
    case cellular
    case wiredEthernet = "wired_ethernet"
    case loopback
    case other

    fileprivate var availableInterfaceType: NetworkPathAvailableInterfaceType {
        switch self {
        case .wifi:
            .wifi
        case .cellular:
            .cellular
        case .wiredEthernet:
            .wiredEthernet
        case .loopback:
            .loopback
        case .other:
            .other
        }
    }
}

/// Exact network-state fields used by transition relation-change records.
///
/// Declaration order is the normative Device Ledger v0 relation-change field
/// order.
public enum NetworkPathStateField: String, Sendable, Equatable, CaseIterable {
    case availableInterfaceTypes = "/network_path/available_interface_types"
    case isConstrained = "/network_path/is_constrained"
    case isExpensive = "/network_path/is_expensive"
    case status = "/network_path/status"
    case supportsDNS = "/network_path/supports_dns"
    case supportsIPv4 = "/network_path/supports_ipv4"
    case supportsIPv6 = "/network_path/supports_ipv6"
    case usedInterfaceTypes = "/network_path/used_interface_types"
}

/// Closed normalized representation of one platform-reported network path.
///
/// This type contains only the fields admitted by the Device Ledger v0 iOS
/// observation contract. It does not retain interface names or indexes,
/// addresses, endpoints, gateways, SSIDs, BSSIDs, account identifiers, or any
/// other network identity.
///
/// Available and used interface classes are deduplicated and stored in the
/// exact declared order. Every used interface must also be present in the
/// normalized available-interface set.
///
/// `NetworkPathState` is platform-reported runtime state. It does not identify
/// the process or external actor that initiated a path change, establish a
/// causal path, prove device security, or create device-control or release
/// authority.
public struct NetworkPathState: Sendable, Equatable {
    public let availableInterfaceTypes: [NetworkPathAvailableInterfaceType]
    public let isConstrained: Bool
    public let isExpensive: Bool
    public let status: NetworkPathStatus
    public let supportsDNS: Bool
    public let supportsIPv4: Bool
    public let supportsIPv6: Bool
    public let usedInterfaceTypes: [NetworkPathUsedInterfaceType]

    /// Creates one normalized network-path state.
    ///
    /// Duplicate interface classes are collapsed. The retained arrays follow
    /// the exact enum declaration order, which matches the normative contract:
    ///
    /// available: wifi, cellular, wired_ethernet, loopback, other, unknown
    /// used:      wifi, cellular, wired_ethernet, loopback, other
    public init(
        availableInterfaceTypes: [NetworkPathAvailableInterfaceType],
        isConstrained: Bool,
        isExpensive: Bool,
        status: NetworkPathStatus,
        supportsDNS: Bool,
        supportsIPv4: Bool,
        supportsIPv6: Bool,
        usedInterfaceTypes: [NetworkPathUsedInterfaceType]
    ) throws {
        let availableSet = Set(availableInterfaceTypes)
        let usedSet = Set(usedInterfaceTypes)

        let normalizedAvailable = NetworkPathAvailableInterfaceType.allCases.filter {
            availableSet.contains($0)
        }
        let normalizedUsed = NetworkPathUsedInterfaceType.allCases.filter {
            usedSet.contains($0)
        }

        for usedInterface in normalizedUsed {
            guard availableSet.contains(usedInterface.availableInterfaceType) else {
                throw NetworkPathStateError.usedInterfaceNotAvailable(
                    usedInterface
                )
            }
        }

        self.availableInterfaceTypes = normalizedAvailable
        self.isConstrained = isConstrained
        self.isExpensive = isExpensive
        self.status = status
        self.supportsDNS = supportsDNS
        self.supportsIPv4 = supportsIPv4
        self.supportsIPv6 = supportsIPv6
        self.usedInterfaceTypes = normalizedUsed
    }

    /// Returns the exact canonical value for one transition-comparison field.
    public func canonicalValue(
        for field: NetworkPathStateField
    ) -> CanonicalJSONValue {
        switch field {
        case .availableInterfaceTypes:
            .array(
                availableInterfaceTypes.map {
                    canonicalString($0.rawValue)
                }
            )
        case .isConstrained:
            .boolean(isConstrained)
        case .isExpensive:
            .boolean(isExpensive)
        case .status:
            canonicalString(status.rawValue)
        case .supportsDNS:
            .boolean(supportsDNS)
        case .supportsIPv4:
            .boolean(supportsIPv4)
        case .supportsIPv6:
            .boolean(supportsIPv6)
        case .usedInterfaceTypes:
            .array(
                usedInterfaceTypes.map {
                    canonicalString($0.rawValue)
                }
            )
        }
    }

    /// Returns the exact canonical network-state object embedded in observation
    /// events and observed state snapshots.
    public func canonicalValue() -> CanonicalJSONValue {
        try! .object([
            try! CanonicalJSONObjectMember(
                key: "available_interface_types",
                value: canonicalValue(
                    for: .availableInterfaceTypes
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "is_constrained",
                value: canonicalValue(
                    for: .isConstrained
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "is_expensive",
                value: canonicalValue(
                    for: .isExpensive
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "status",
                value: canonicalValue(
                    for: .status
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "supports_dns",
                value: canonicalValue(
                    for: .supportsDNS
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "supports_ipv4",
                value: canonicalValue(
                    for: .supportsIPv4
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "supports_ipv6",
                value: canonicalValue(
                    for: .supportsIPv6
                )
            ),
            try! CanonicalJSONObjectMember(
                key: "used_interface_types",
                value: canonicalValue(
                    for: .usedInterfaceTypes
                )
            ),
        ])
    }

    /// Returns the exact canonical bytes embedded in a Device Ledger record.
    public func canonicalBytes() -> Data {
        CanonicalJSONEncoder.encode(
            canonicalValue()
        )
    }

    private func canonicalString(
        _ rawValue: String
    ) -> CanonicalJSONValue {
        .string(
            try! CanonicalJSONString(rawValue)
        )
    }
}
