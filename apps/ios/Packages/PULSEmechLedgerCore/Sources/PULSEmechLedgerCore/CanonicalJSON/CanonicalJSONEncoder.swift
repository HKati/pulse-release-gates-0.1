import Foundation

/// Serializes validated `CanonicalJSONValue` values into the exact canonical
/// JSON byte representation required by the PULSEmech Device Ledger v0
/// profile.
///
/// The encoder does not use `JSONEncoder` or `JSONSerialization`. It emits one
/// deterministic UTF-8 byte sequence with no BOM, no insignificant whitespace,
/// and no trailing newline.
public enum CanonicalJSONEncoder {
    /// Encodes one validated canonical JSON value.
    public static func encode(
        _ value: CanonicalJSONValue
    ) -> Data {
        var output: [UInt8] = []
        append(
            value,
            to: &output
        )
        return Data(output)
    }

    private static let lowercaseHexDigits: [UInt8] = Array(
        "0123456789abcdef".utf8
    )

    private static func append(
        _ value: CanonicalJSONValue,
        to output: inout [UInt8]
    ) {
        switch value {
        case .null:
            output.append(contentsOf: [
                0x6E,
                0x75,
                0x6C,
                0x6C,
            ])

        case let .boolean(boolean):
            if boolean {
                output.append(contentsOf: [
                    0x74,
                    0x72,
                    0x75,
                    0x65,
                ])
            } else {
                output.append(contentsOf: [
                    0x66,
                    0x61,
                    0x6C,
                    0x73,
                    0x65,
                ])
            }

        case let .integer(integer):
            output.append(
                contentsOf: String(integer).utf8
            )

        case let .string(string):
            append(
                string,
                to: &output
            )

        case let .array(values):
            output.append(0x5B)

            for (index, child) in values.enumerated() {
                if index > 0 {
                    output.append(0x2C)
                }

                append(
                    child,
                    to: &output
                )
            }

            output.append(0x5D)

        case let .object(object):
            output.append(0x7B)

            for (index, member) in object.members.enumerated() {
                if index > 0 {
                    output.append(0x2C)
                }

                append(
                    member.key,
                    to: &output
                )
                output.append(0x3A)
                append(
                    member.value,
                    to: &output
                )
            }

            output.append(0x7D)
        }
    }

    private static func append(
        _ string: CanonicalJSONString,
        to output: inout [UInt8]
    ) {
        output.append(0x22)

        for byte in string.utf8Bytes {
            switch byte {
            case 0x08:
                output.append(contentsOf: [
                    0x5C,
                    0x62,
                ])

            case 0x09:
                output.append(contentsOf: [
                    0x5C,
                    0x74,
                ])

            case 0x0A:
                output.append(contentsOf: [
                    0x5C,
                    0x6E,
                ])

            case 0x0C:
                output.append(contentsOf: [
                    0x5C,
                    0x66,
                ])

            case 0x0D:
                output.append(contentsOf: [
                    0x5C,
                    0x72,
                ])

            case 0x22:
                output.append(contentsOf: [
                    0x5C,
                    0x22,
                ])

            case 0x5C:
                output.append(contentsOf: [
                    0x5C,
                    0x5C,
                ])

            case 0x00...0x07,
                 0x0B,
                 0x0E...0x1F:
                output.append(contentsOf: [
                    0x5C,
                    0x75,
                    0x30,
                    0x30,
                    lowercaseHexDigits[Int(byte >> 4)],
                    lowercaseHexDigits[Int(byte & 0x0F)],
                ])

            default:
                output.append(byte)
            }
        }

        output.append(0x22)
    }
}
