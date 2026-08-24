import Foundation
import XCTest
@testable import PULSEmechLedgerCore

final class CanonicalJSONEncoderTests: XCTestCase {
    private func assertEncoding(
        _ value: CanonicalJSONValue,
        equals expected: String,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        XCTAssertEqual(
            Array(CanonicalJSONEncoder.encode(value)),
            Array(expected.utf8),
            file: file,
            line: line
        )
    }

    func testEncodesNullAndBooleansExactly() {
        assertEncoding(.null, equals: "null")
        assertEncoding(.boolean(true), equals: "true")
        assertEncoding(.boolean(false), equals: "false")
    }

    func testEncodesSignedIntegerLexicalFormsExactly() {
        let vectors: [(Int64, String)] = [
            (Int64.min, "-9223372036854775808"),
            (-1, "-1"),
            (0, "0"),
            (1, "1"),
            (Int64.max, "9223372036854775807"),
        ]

        for (value, expected) in vectors {
            assertEncoding(
                .integer(value),
                equals: expected
            )
        }
    }

    func testEncodesEmptyStringArrayAndObjectExactly() throws {
        assertEncoding(
            try .string(""),
            equals: "\"\""
        )
        assertEncoding(
            .array([]),
            equals: "[]"
        )
        assertEncoding(
            .object(
                try CanonicalJSONObject([])
            ),
            equals: "{}"
        )
    }

    func testEncodesAllControlCharactersWithMandatoryForms() throws {
        let source = String(
            decoding: Array(UInt8(0x00)...UInt8(0x1F)),
            as: UTF8.self
        )
        let expected =
            "\"\\u0000\\u0001\\u0002\\u0003\\u0004\\u0005\\u0006\\u0007" +
            "\\b\\t\\n\\u000b\\f\\r" +
            "\\u000e\\u000f\\u0010\\u0011\\u0012\\u0013\\u0014\\u0015" +
            "\\u0016\\u0017\\u0018\\u0019\\u001a\\u001b\\u001c\\u001d" +
            "\\u001e\\u001f\""

        assertEncoding(
            try .string(source),
            equals: expected
        )
    }

    func testEscapesQuotationMarkAndReverseSolidusButNotForwardSlash() throws {
        assertEncoding(
            try .string("quote\"reverse\\forward/"),
            equals: "\"quote\\\"reverse\\\\forward/\""
        )
    }

    func testEmitsEveryOtherASCIIByteDirectly() throws {
        let escapedBytes: Set<UInt8> = [
            0x00, 0x01, 0x02, 0x03,
            0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B,
            0x0C, 0x0D, 0x0E, 0x0F,
            0x10, 0x11, 0x12, 0x13,
            0x14, 0x15, 0x16, 0x17,
            0x18, 0x19, 0x1A, 0x1B,
            0x1C, 0x1D, 0x1E, 0x1F,
            0x22,
            0x5C,
        ]

        for byte in UInt8(0x20)...UInt8(0x7F)
        where !escapedBytes.contains(byte) {
            let value = try CanonicalJSONValue.string(
                String(
                    decoding: [byte],
                    as: UTF8.self
                )
            )
            let encoded = CanonicalJSONEncoder.encode(value)

            XCTAssertEqual(
                Array(encoded),
                [0x22, byte, 0x22],
                "Unexpected escaping for ASCII byte \(byte)"
            )
        }
    }

    func testObjectKeysUseTheSameEscapingContractAsStringValues() throws {
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "\\",
                value: .integer(4)
            ),
            try CanonicalJSONObjectMember(
                key: "/",
                value: .integer(3)
            ),
            try CanonicalJSONObjectMember(
                key: "\"",
                value: .integer(2)
            ),
            try CanonicalJSONObjectMember(
                key: "\n",
                value: .integer(1)
            ),
        ])

        assertEncoding(
            value,
            equals: "{\"\\n\":1,\"\\\"\":2,\"/\":3,\"\\\\\":4}"
        )
    }

    func testEncodesObjectInCanonicalKeyOrderWithoutWhitespace() throws {
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "b",
                value: .integer(4)
            ),
            try CanonicalJSONObjectMember(
                key: "aa",
                value: .integer(3)
            ),
            try CanonicalJSONObjectMember(
                key: "a",
                value: .integer(2)
            ),
            try CanonicalJSONObjectMember(
                key: "A",
                value: .integer(1)
            ),
            try CanonicalJSONObjectMember(
                key: "",
                value: .integer(0)
            ),
        ])

        assertEncoding(
            value,
            equals: "{\"\":0,\"A\":1,\"a\":2,\"aa\":3,\"b\":4}"
        )
    }

    func testPreservesArrayOrderExactly() throws {
        let value = CanonicalJSONValue.array([
            .integer(3),
            .boolean(false),
            try .string("two"),
            .null,
            .integer(-1),
        ])

        assertEncoding(
            value,
            equals: "[3,false,\"two\",null,-1]"
        )
    }

    func testEncodesNestedValuesExactly() throws {
        let metadata = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "z",
                value: .integer(0)
            ),
            try CanonicalJSONObjectMember(
                key: "a",
                value: .integer(1)
            ),
        ])
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "meta",
                value: metadata
            ),
            try CanonicalJSONObjectMember(
                key: "items",
                value: .array([
                    .null,
                    .integer(-1),
                    try .string("x"),
                ])
            ),
            try CanonicalJSONObjectMember(
                key: "active",
                value: .boolean(true)
            ),
        ])

        assertEncoding(
            value,
            equals: "{\"active\":true,\"items\":[null,-1,\"x\"],\"meta\":{\"a\":1,\"z\":0}}"
        )
    }

    func testOutputHasNoBOMWhitespaceOrTrailingNewline() throws {
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "ledger",
                value: try .string("value")
            ),
        ])
        let encoded = CanonicalJSONEncoder.encode(value)
        let bytes = Array(encoded)

        XCTAssertFalse(bytes.starts(with: [0xEF, 0xBB, 0xBF]))
        XCTAssertEqual(bytes.last, 0x7D)
        XCTAssertFalse(bytes.contains(0x0A))
        XCTAssertFalse(bytes.contains(0x0D))
        XCTAssertFalse(bytes.contains(0x20))
    }

    func testRepeatedEncodingIsByteIdentical() throws {
        let value = try CanonicalJSONValue.object([
            try CanonicalJSONObjectMember(
                key: "array",
                value: .array([
                    .integer(Int64.min),
                    .boolean(true),
                    try .string("line\nquote\"slash\\/"),
                ])
            ),
            try CanonicalJSONObjectMember(
                key: "null",
                value: .null
            ),
        ])
        let expected = CanonicalJSONEncoder.encode(value)

        for _ in 0..<100 {
            XCTAssertEqual(
                CanonicalJSONEncoder.encode(value),
                expected
            )
        }
    }
}
