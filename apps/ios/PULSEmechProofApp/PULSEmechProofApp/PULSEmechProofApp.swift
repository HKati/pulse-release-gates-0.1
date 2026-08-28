import CoreTransferable
import SwiftUI
import UniformTypeIdentifiers

@main
struct PULSEmechProofApp: App {
    var body: some Scene {
        WindowGroup {
            BoundedProofView()
        }
    }
}

@MainActor
final class BoundedProofViewModel: ObservableObject {
    enum Phase {
        case idle
        case running
        case completed(BoundedProofRunResult)
        case failed(String)
    }

    @Published private(set) var phase: Phase = .idle

    func runIfNeeded() {
        guard case .idle = phase else {
            return
        }
        run()
    }

    func run() {
        guard !isRunning else {
            return
        }

        phase = .running

        Task {
            do {
                let result = try await BoundedReferenceProofRunner.run()
                phase = .completed(result)
            } catch {
                phase = .failed(error.localizedDescription)
            }
        }
    }

    private var isRunning: Bool {
        if case .running = phase {
            return true
        }
        return false
    }
}

struct BoundedProofView: View {
    @StateObject private var model =
        BoundedProofViewModel()

    var body: some View {
        NavigationStack {
            Group {
                switch model.phase {
                case .idle,
                     .running:
                    runningView
                case let .completed(result):
                    resultView(result)
                case let .failed(message):
                    failureView(message)
                }
            }
            .navigationTitle("PULSEmech Proof")
            .navigationBarTitleDisplayMode(.inline)
        }
        .task {
            model.runIfNeeded()
        }
    }

    private var runningView: some View {
        VStack(spacing: 18) {
            ProgressView()
                .controlSize(.large)

            Text("Materializing bounded proof")
                .font(.headline)

            Text(
                "Exact evidence chain → signed ledger → canonical manifest → deterministic .pulseledger → carrier-bound standalone-verifier result"
            )
            .multilineTextAlignment(.center)
            .foregroundStyle(.secondary)
        }
        .padding(28)
    }

    private func failureView(
        _ message: String
    ) -> some View {
        VStack(spacing: 18) {
            Image(systemName: "xmark.octagon")
                .font(.system(size: 42))

            Text("Bounded proof failed closed")
                .font(.headline)

            Text(message)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)

            Button("Run again") {
                model.run()
            }
            .buttonStyle(.borderedProminent)
        }
        .padding(28)
    }

    private func resultView(
        _ result: BoundedProofRunResult
    ) -> some View {
        ScrollView {
            LazyVStack(
                alignment: .leading,
                spacing: 18
            ) {
                proofStatusCard(result)
                observedRelationSection(result)
                exactIdentitySection(result)
                verifierSection(result)
                claimBoundarySection(result)
                exportSection(result)
            }
            .padding()
        }
        .refreshable {
            model.run()
        }
    }

    private func proofStatusCard(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 10
        ) {
            Label(
                "Carrier-bound reproduction complete",
                systemImage: "checkmark.seal"
            )
            .font(.headline)

            Text(result.verifierResult)
                .font(.system(.body, design: .monospaced))
                .textSelection(.enabled)

            Text(
                "The app generated the exact artifact. The displayed result comes from the separately implemented verifier report bound to the same carrier SHA-256."
            )
            .font(.subheadline)
            .foregroundStyle(.secondary)
        }
        .proofCard()
    }

    private func observedRelationSection(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            sectionTitle(
                "Observed relation",
                systemImage: "point.3.connected.trianglepath.dotted"
            )

            metricRow(
                "Records",
                value: "\(result.recordCount)"
            )
            metricRow(
                "Sessions / clock epochs",
                value:
                    "\(result.sessionCount) / \(result.clockEpochCount)"
            )
            metricRow(
                "Session boundaries",
                value: "\(result.sessionBoundaryCount)"
            )
            metricRow(
                "Continuous relation",
                value: "\(result.continuousCoverageCount)"
            )
            metricRow(
                "Observation gap",
                value: "\(result.interruptedCoverageCount)"
            )
            metricRow(
                "Event-bound transition",
                value: "\(result.eventBoundTransitionCount)"
            )
            metricRow(
                "Endpoint-difference-only transition",
                value:
                    "\(result.endpointDifferenceOnlyTransitionCount)"
            )
        }
        .proofCard()
    }

    private func exactIdentitySection(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 14
        ) {
            sectionTitle(
                "Exact artifact identities",
                systemImage: "number"
            )

            digestRow(
                "Checkpoint SHA-256",
                value: result.checkpointSHA256
            )
            digestRow(
                "Ledger SHA-256",
                value: result.ledgerSHA256
            )
            digestRow(
                "Manifest SHA-256",
                value: result.manifestSHA256
            )
            digestRow(
                "Carrier SHA-256",
                value: result.carrierSHA256
            )

            metricRow(
                "Carrier size",
                value:
                    "\(result.carrierSizeBytes) bytes"
            )
        }
        .proofCard()
    }

    private func verifierSection(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            sectionTitle(
                "Separate verifier binding",
                systemImage: "arrow.triangle.2.circlepath"
            )

            metricRow(
                "Carrier SHA-256 match",
                value:
                    result.verifierCarrierBindingMatches
                    ? "exact"
                    : "mismatch"
            )
            metricRow(
                "Checks",
                value:
                    "\(result.verifierCheckCount) passed"
            )
            metricRow(
                "Checkpoint signature",
                value:
                    result.checkpointSignatureStatus
            )
            metricRow(
                "Package signature",
                value:
                    result.packageSignatureStatus
            )
            metricRow(
                "Implementation relation",
                value:
                    result.verifierImplementationRelation
            )
            metricRow(
                "Producer code imported",
                value:
                    result.producerCodeImportedByVerifier
                    ? "yes"
                    : "no"
            )

            digestRow(
                "Verifier-bound carrier",
                value:
                    result.verifierCarrierSHA256
            )
        }
        .proofCard()
    }

    private func claimBoundarySection(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            sectionTitle(
                "Declared boundary",
                systemImage: "scope"
            )

            metricRow(
                "Observer identity scope",
                value:
                    result.observerIdentityScope
            )
            metricRow(
                "Key-origin profile",
                value:
                    result.observerKeyOriginProfile
            )
            metricRow(
                "Declared unavailability",
                value:
                    result.declaredUnavailabilityPresent
                    ? "present"
                    : "absent"
            )
            metricRow(
                "Authority effect",
                value:
                    result.authorityEffect
            )
            metricRow(
                "External validation claim",
                value:
                    result.externalValidationClaim
            )

            Text(
                "No device-security, physical-measurement, continuous-monitoring, causal-completion, malware-absence, external-approval, or release-authority claim is created."
            )
            .font(.footnote)
            .foregroundStyle(.secondary)
        }
        .proofCard()
    }

    private func exportSection(
        _ result: BoundedProofRunResult
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 12
        ) {
            sectionTitle(
                "Exact artifact",
                systemImage: "shippingbox"
            )

            Text(result.carrierFileName)
                .font(.system(.footnote, design: .monospaced))
                .textSelection(.enabled)

            ShareLink(
                item: PulseledgerTransferArtifact(
                    fileName:
                        result.carrierFileName,
                    exactBytes:
                        result.carrierBytes
                ),
                preview: SharePreview(
                    Text(result.carrierFileName)
                )
            ) {
                Label(
                    "Export exact .pulseledger",
                    systemImage:
                        "square.and.arrow.up"
                )
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)

            Button("Run bounded proof again") {
                model.run()
            }
            .frame(maxWidth: .infinity)
            .buttonStyle(.bordered)
        }
        .proofCard()
    }

    private func sectionTitle(
        _ title: String,
        systemImage: String
    ) -> some View {
        Label(
            title,
            systemImage: systemImage
        )
        .font(.headline)
    }

    private func metricRow(
        _ label: String,
        value: String
    ) -> some View {
        HStack(
            alignment: .firstTextBaseline,
            spacing: 12
        ) {
            Text(label)
                .foregroundStyle(.secondary)

            Spacer(minLength: 12)

            Text(value)
                .multilineTextAlignment(.trailing)
                .textSelection(.enabled)
        }
        .font(.subheadline)
    }

    private func digestRow(
        _ label: String,
        value: String
    ) -> some View {
        VStack(
            alignment: .leading,
            spacing: 5
        ) {
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)

            Text(value)
                .font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
        }
    }
}

private struct PulseledgerTransferArtifact:
    Transferable,
    Sendable
{
    let fileName: String
    let exactBytes: Data

    init(
        fileName: String,
        exactBytes: Data
    ) {
        self.fileName = fileName
        self.exactBytes = Data(exactBytes)
    }

    static var transferRepresentation:
        some TransferRepresentation
    {
        FileRepresentation(
            exportedContentType:
                .zip
        ) { artifact in
            let directory = FileManager.default
                .temporaryDirectory
                .appendingPathComponent(
                    "pulsemech-proof-export-\(UUID().uuidString)",
                    isDirectory: true
                )

            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: false
            )

            let fileURL = directory
                .appendingPathComponent(
                    artifact.fileName,
                    isDirectory: false
                )

            try artifact.exactBytes.write(
                to: fileURL,
                options: .atomic
            )

            return SentTransferredFile(
                fileURL
            )
        }
    }
}

private extension View {
    func proofCard() -> some View {
        padding(16)
            .frame(
                maxWidth: .infinity,
                alignment: .leading
            )
            .background(
                .regularMaterial,
                in: RoundedRectangle(
                    cornerRadius: 18,
                    style: .continuous
                )
            )
    }
}
