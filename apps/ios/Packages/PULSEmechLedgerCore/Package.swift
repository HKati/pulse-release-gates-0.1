// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "PULSEmechLedgerCore",
    platforms: [
        .iOS(.v13),
    ],
    products: [
        .library(
            name: "PULSEmechLedgerCore",
            targets: [
                "PULSEmechLedgerCore",
            ]
        ),
    ],
    targets: [
        .target(
            name: "PULSEmechLedgerCore"
        ),
        .testTarget(
            name: "PULSEmechLedgerCoreTests",
            dependencies: [
                "PULSEmechLedgerCore",
            ]
        ),
    ],
    swiftLanguageModes: [
        .v6,
    ]
)
