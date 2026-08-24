import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class NetworkPathStateTests: XCTestCase {
    private func canonicalString(
        _ value: String
    ) -> CanonicalJSONValue {
        try! .string(value)
    }

    private func referenceWiFiState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: false,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .wifi,
            ]
        )
    }

    private func referenceCellularState() throws -> NetworkPathState {
        try NetworkPathState(
            availableInterfaceTypes: [
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: true,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .cellular,
            ]
        )
    }

    func testContractRawValuesAndDeclaredOrdersAreExact() {
        XCTAssertEqual(
            NetworkPathStatus.allCases.map(\.rawValue),
            [
                "satisfied",
                "unsatisfied",
                "requires_connection",
                "unknown",
            ]
        )
        XCTAssertEqual(
            NetworkPathAvailableInterfaceType.allCases.map(\.rawValue),
            [
                "wifi",
                "cellular",
                "wired_ethernet",
                "loopback",
                "other",
                "unknown",
            ]
        )
        XCTAssertEqual(
            NetworkPathUsedInterfaceType.allCases.map(\.rawValue),
            [
                "wifi",
                "cellular",
                "wired_ethernet",
                "loopback",
                "other",
            ]
        )
        XCTAssertEqual(
            NetworkPathStateField.allCases.map(\.rawValue),
            [
                "/network_path/available_interface_types",
                "/network_path/is_constrained",
                "/network_path/is_expensive",
                "/network_path/status",
                "/network_path/supports_dns",
                "/network_path/supports_ipv4",
                "/network_path/supports_ipv6",
                "/network_path/used_interface_types",
            ]
        )
    }

    func testInitializerDeduplicatesAndAppliesNormativeInterfaceOrder() throws {
        let state = try NetworkPathState(
            availableInterfaceTypes: [
                .unknown,
                .other,
                .cellular,
                .wifi,
                .cellular,
                .wiredEthernet,
                .loopback,
                .wifi,
            ],
            isConstrained: true,
            isExpensive: false,
            status: .requiresConnection,
            supportsDNS: false,
            supportsIPv4: true,
            supportsIPv6: false,
            usedInterfaceTypes: [
                .other,
                .cellular,
                .wifi,
                .other,
                .wiredEthernet,
                .loopback,
            ]
        )

        XCTAssertEqual(
            state.availableInterfaceTypes,
            [
                .wifi,
                .cellular,
                .wiredEthernet,
                .loopback,
                .other,
                .unknown,
            ]
        )
        XCTAssertEqual(
            state.usedInterfaceTypes,
            [
                .wifi,
                .cellular,
                .wiredEthernet,
                .loopback,
                .other,
            ]
        )
    }

    func testInputOrderAndDuplicatesDoNotChangeCanonicalIdentity() throws {
        let first = try NetworkPathState(
            availableInterfaceTypes: [
                .cellular,
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: true,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .cellular,
                .cellular,
            ]
        )
        let second = try NetworkPathState(
            availableInterfaceTypes: [
                .wifi,
                .cellular,
            ],
            isConstrained: false,
            isExpensive: true,
            status: .satisfied,
            supportsDNS: true,
            supportsIPv4: true,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .cellular,
            ]
        )

        XCTAssertEqual(first, second)
        XCTAssertEqual(
            first.canonicalBytes(),
            second.canonicalBytes()
        )
    }

    func testEveryUsedInterfaceMustAlsoBeAvailable() {
        let vectors: [(
            used: NetworkPathUsedInterfaceType,
            available: NetworkPathAvailableInterfaceType
        )] = [
            (.wifi, .cellular),
            (.cellular, .wifi),
            (.wiredEthernet, .wifi),
            (.loopback, .wifi),
            (.other, .wifi),
        ]

        for vector in vectors {
            XCTAssertThrowsError(
                try NetworkPathState(
                    availableInterfaceTypes: [
                        vector.available,
                    ],
                    isConstrained: false,
                    isExpensive: false,
                    status: .unknown,
                    supportsDNS: false,
                    supportsIPv4: false,
                    supportsIPv6: false,
                    usedInterfaceTypes: [
                        vector.used,
                    ]
                )
            ) { error in
                XCTAssertEqual(
                    error as? NetworkPathStateError,
                    .usedInterfaceNotAvailable(
                        vector.used
                    )
                )
            }
        }
    }

    func testUnknownCanBeAvailableWithoutCreatingUnknownUsedClaim() throws {
        let state = try NetworkPathState(
            availableInterfaceTypes: [
                .unknown,
            ],
            isConstrained: false,
            isExpensive: false,
            status: .unknown,
            supportsDNS: false,
            supportsIPv4: false,
            supportsIPv6: false,
            usedInterfaceTypes: []
        )

        XCTAssertEqual(
            state.availableInterfaceTypes,
            [
                .unknown,
            ]
        )
        XCTAssertTrue(
            state.usedInterfaceTypes.isEmpty
        )
        XCTAssertEqual(
            state.canonicalBytes(),
            Data(
                #"{"available_interface_types":["unknown"],"is_constrained":false,"is_expensive":false,"status":"unknown","supports_dns":false,"supports_ipv4":false,"supports_ipv6":false,"used_interface_types":[]}"#.utf8
            )
        )
    }

    func testEmptyInterfaceInventoriesRemainExplicitEmptyArrays() throws {
        let state = try NetworkPathState(
            availableInterfaceTypes: [],
            isConstrained: true,
            isExpensive: true,
            status: .unsatisfied,
            supportsDNS: false,
            supportsIPv4: false,
            supportsIPv6: false,
            usedInterfaceTypes: []
        )

        XCTAssertTrue(
            state.availableInterfaceTypes.isEmpty
        )
        XCTAssertTrue(
            state.usedInterfaceTypes.isEmpty
        )
        XCTAssertEqual(
            state.canonicalBytes(),
            Data(
                #"{"available_interface_types":[],"is_constrained":true,"is_expensive":true,"status":"unsatisfied","supports_dns":false,"supports_ipv4":false,"supports_ipv6":false,"used_interface_types":[]}"#.utf8
            )
        )
    }

    func testReferenceWiFiStateMatchesExactPythonProducerBytes() throws {
        let state = try referenceWiFiState()
        let expected =
            #"{"available_interface_types":["wifi","cellular"],"is_constrained":false,"is_expensive":false,"status":"satisfied","supports_dns":true,"supports_ipv4":true,"supports_ipv6":true,"used_interface_types":["wifi"]}"#
        let bytes = state.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            208
        )
    }

    func testReferenceCellularStateMatchesExactPythonProducerBytes() throws {
        let state = try referenceCellularState()
        let expected =
            #"{"available_interface_types":["wifi","cellular"],"is_constrained":false,"is_expensive":true,"status":"satisfied","supports_dns":true,"supports_ipv4":true,"supports_ipv6":true,"used_interface_types":["cellular"]}"#
        let bytes = state.canonicalBytes()

        XCTAssertEqual(
            bytes,
            Data(expected.utf8)
        )
        XCTAssertEqual(
            bytes.count,
            211
        )
    }

    func testPerFieldCanonicalValuesMatchNormalizedState() throws {
        let state = try NetworkPathState(
            availableInterfaceTypes: [
                .other,
                .wifi,
                .unknown,
            ],
            isConstrained: true,
            isExpensive: false,
            status: .requiresConnection,
            supportsDNS: true,
            supportsIPv4: false,
            supportsIPv6: true,
            usedInterfaceTypes: [
                .other,
                .wifi,
            ]
        )

        XCTAssertEqual(
            state.canonicalValue(
                for: .availableInterfaceTypes
            ),
            .array([
                canonicalString("wifi"),
                canonicalString("other"),
                canonicalString("unknown"),
            ])
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .isConstrained
            ),
            .boolean(true)
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .isExpensive
            ),
            .boolean(false)
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .status
            ),
            canonicalString(
                "requires_connection"
            )
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .supportsDNS
            ),
            .boolean(true)
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .supportsIPv4
            ),
            .boolean(false)
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .supportsIPv6
            ),
            .boolean(true)
        )
        XCTAssertEqual(
            state.canonicalValue(
                for: .usedInterfaceTypes
            ),
            .array([
                canonicalString("wifi"),
                canonicalString("other"),
            ])
        )
    }

    func testCanonicalObjectContainsOnlyTheEightDeclaredFields() throws {
        let state = try referenceWiFiState()

        guard case let .object(object) = state.canonicalValue() else {
            return XCTFail(
                "Expected canonical network-state object"
            )
        }

        XCTAssertEqual(
            object.members.map(\.key.value),
            [
                "available_interface_types",
                "is_constrained",
                "is_expensive",
                "status",
                "supports_dns",
                "supports_ipv4",
                "supports_ipv6",
                "used_interface_types",
            ]
        )
    }

    func testCanonicalOutputHasNoBOMWhitespaceOrTrailingNewline() throws {
        let bytes = Array(
            try referenceWiFiState().canonicalBytes()
        )

        XCTAssertFalse(
            bytes.starts(with: [
                0xEF,
                0xBB,
                0xBF,
            ])
        )
        XCTAssertEqual(
            bytes.first,
            0x7B
        )
        XCTAssertEqual(
            bytes.last,
            0x7D
        )
        XCTAssertFalse(
            bytes.contains(0x20)
        )
        XCTAssertFalse(
            bytes.contains(0x0A)
        )
        XCTAssertFalse(
            bytes.contains(0x0D)
        )
    }

    func testRepeatedConstructionAndEncodingAreByteIdentical() throws {
        let expected = try referenceCellularState().canonicalBytes()

        for _ in 0..<100 {
            let state = try NetworkPathState(
                availableInterfaceTypes: [
                    .cellular,
                    .wifi,
                    .cellular,
                ],
                isConstrained: false,
                isExpensive: true,
                status: .satisfied,
                supportsDNS: true,
                supportsIPv4: true,
                supportsIPv6: true,
                usedInterfaceTypes: [
                    .cellular,
                    .cellular,
                ]
            )

            XCTAssertEqual(
                state.canonicalBytes(),
                expected
            )
        }
    }
}
