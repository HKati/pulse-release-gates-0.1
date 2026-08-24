import XCTest
@testable import PULSEmechLedgerCore

final class CanonicalJSONValueTests: XCTestCase {
    func testCanonicalJSONStringAcceptsEmptyString() throws {
        let value = try CanonicalJSONString("")

        XCTAssertEqual(value.value, "")
        XCTAssertEqual(value.utf8Bytes, [])
    }

    func testCanonicalJSONStringAcceptsEveryASCIIScalar() throws {
        for scalarValue in UInt32(0)...UInt32(0x7F) {
            let scalar = try XCTUnwrap(
                UnicodeScalar(scalarValue)
            )
            let source = String(scalar)
            let value = try CanonicalJSONString(source)

            XCTAssertEqual(value.value, source)
            XCTAssertEqual(
                value.utf8Bytes,
                [UInt8(scalarValue)]
            )
        }
    }

    func testCanonicalJSONStringRejectsNonASCIIScalars() {
        let nonASCIIValues = [
            "é",
            "e\u{0301}",
            "🙂",
            "\u{0080}",
        ]

        for source in nonASCIIValues {
            XCTAssertThrowsError(
                try CanonicalJSONString(source)
            ) { error in
                XCTAssertEqual(
                    error as? CanonicalJSONValueError,
                    .nonASCIIString
                )
            }
        }
    }

    func testStringValueFactoryPreservesExactASCIIContent() throws {
        let source = "line\nquote\"slash\\nul\u{0000}"
        let value = try CanonicalJSONValue.string(source)

        XCTAssertEqual(
            value,
            .string(
                try CanonicalJSONString(source)
            )
        )
    }

    func testStringKeyInitializerRejectsNonASCIIKey() {
        XCTAssertThrowsError(
            try CanonicalJSONObjectMember(
                key: "é",
                value: .null
            )
        ) { error in
            XCTAssertEqual(
                error as? CanonicalJSONValueError,
                .nonASCIIString
            )
        }
    }

    func testObjectRejectsDuplicateKeys() throws {
        let members = [
            try CanonicalJSONObjectMember(
                key: "same",
                value: .integer(1)
            ),
            try CanonicalJSONObjectMember(
                key: "same",
                value: .integer(2)
            ),
        ]

        XCTAssertThrowsError(
            try CanonicalJSONObject(members)
        ) { error in
            XCTAssertEqual(
                error as? CanonicalJSONValueError,
                .duplicateObjectKey("same")
            )
        }
    }

    func testObjectAcceptsEmptyMemberSet() throws {
        let object = try CanonicalJSONObject([])

        XCTAssertTrue(object.members.isEmpty)
    }

    func testObjectSortsKeysByUnsignedLexicographicUTF8Order() throws {
        let object = try CanonicalJSONObject([
            try CanonicalJSONObjectMember(
                key: "b",
                value: .integer(6)
            ),
            try CanonicalJSONObjectMember(
                key: "aa",
                value: .integer(5)
            ),
            try CanonicalJSONObjectMember(
                key: "~",
                value: .integer(7)
            ),
            try CanonicalJSONObjectMember(
                key: "",
                value: .integer(1)
            ),
            try CanonicalJSONObjectMember(
                key: "a",
                value: .integer(4)
            ),
            try CanonicalJSONObjectMember(
                key: "_",
                value: .integer(3)
            ),
            try CanonicalJSONObjectMember(
                key: "A",
                value: .integer(2)
            ),
        ])

        XCTAssertEqual(
            object.members.map(\.key.value),
            [
                "",
                "A",
                "_",
                "a",
                "aa",
                "b",
                "~",
            ]
        )
        XCTAssertEqual(
            object.members.map(\.value),
            [
                .integer(1),
                .integer(2),
                .integer(3),
                .integer(4),
                .integer(5),
                .integer(6),
                .integer(7),
            ]
        )
    }

    func testObjectFactoryReturnsCanonicallyOrderedObjectValue() throws {
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "z",
                value: .boolean(false)
            ),
            try CanonicalJSONObjectMember(
                key: "a",
                value: .boolean(true)
            ),
        ])

        guard case let .object(object) = value else {
            return XCTFail(
                "Expected canonical object value"
            )
        }

        XCTAssertEqual(
            object.members.map(\.key.value),
            [
                "a",
                "z",
            ]
        )
    }

    func testArrayPreservesCallerOrderExactly() throws {
        let expected: [CanonicalJSONValue] = [
            .integer(Int64.max),
            .boolean(false),
            try CanonicalJSONValue.string("first"),
            .null,
            .integer(Int64.min),
        ]
        let value = CanonicalJSONValue.array(expected)

        guard case let .array(observed) = value else {
            return XCTFail(
                "Expected canonical array value"
            )
        }

        XCTAssertEqual(
            observed,
            expected
        )
    }

    func testNestedValuesRemainExactlyRepresentable() throws {
        let child = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "enabled",
                value: .boolean(true)
            ),
            try CanonicalJSONObjectMember(
                key: "sequence",
                value: .integer(7)
            ),
        ])
        let parent = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "items",
                value: .array([
                    child,
                    .null,
                ])
            ),
            try CanonicalJSONObjectMember(
                key: "name",
                value: try CanonicalJSONValue.string(
                    "ledger"
                )
            ),
        ])

        guard case let .object(parentObject) = parent else {
            return XCTFail(
                "Expected parent object"
            )
        }

        XCTAssertEqual(
            parentObject.members.map(\.key.value),
            [
                "items",
                "name",
            ]
        )
        XCTAssertEqual(
            parentObject.members[0].value,
            .array([
                child,
                .null,
            ])
        )
    }

    func testSignedIntegerBoundariesRemainExact() {
        XCTAssertEqual(
            CanonicalJSONValue.integer(
                Int64.min
            ),
            .integer(
                -9_223_372_036_854_775_808
            )
        )
        XCTAssertEqual(
            CanonicalJSONValue.integer(
                Int64.max
            ),
            .integer(
                9_223_372_036_854_775_807
            )
        )
    }
}
