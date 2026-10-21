# PULSEbox v0 Technical Plan

## Repository preservation note

This English repository edition preserves the Hungarian technical plan dated
2026-10-13, design revision **0.2**, for the **PULSEbox v0** project. The original
[source document](pulsebox_v0/source/PULSEbox_v0_muszaki_terv_2026-10-13.docx)
is retained byte-for-byte. The [source manifest](pulsebox_v0/SOURCE_MANIFEST.json)
records both file identities and the historical repository baseline.

**Status:** design proposal; the proposed PULSEbox components and profiles are
not activated by this documentation change. All 54 negative cases below are
planned cases, with execution status `NOT_RUN`. This preservation work has
`authority_effect: none`.

Repository observations in this plan remain bound to the original
`d44bf963cbac377366e95ae7ac9e3603fff894a4` snapshot. They are historical design
inputs. Implementation and acceptance require their own current evidence,
authorization and review. The two phases are an isolated execution decision
and a separate decision to export the frozen result as data to a registered
test receiver.

## Physical execution boundary for the PULSEmech decision chain

**Design revision:** 0.2  
**Source date:** 2026-10-13  
**Authoring organization:** E•PARADOX LABS  
**Historical repository baseline:** `HKati/pulse-release-gates-0.1` at `d44bf963cbac377366e95ae7ac9e3603fff894a4`.

**Status: design only; not implemented or tested.** The PULSEbox components, contracts, tests and hardware parameters in this document are design proposals. Later demonstrator and prototype evidence may establish whether the requirements are met; this plan is not that evidence.

PULSEbox is a technically feasible direction: it connects an evidence-bound decision to an execution interface that actually holds the authority for the designated operation. The physical box derives its value from separately controlled resources, a small trusted control system and access enforcement at the target. An enclosure and two network connectors do not, by themselves, close bypass paths.

The proposed v0 introduces two separate decisions: permission for an isolated trial run, followed by permission to export the exact bytes of an observed and recorded result. Export goes to a designated receiver that performs no automatic execution. The v0 does not start a program on the user's everyday workstation or write to a production repository.

### Required clarifications to the initial concept

| Topic | Requirement in this plan |
| --- | --- |
| Output digest | The digest of a new result exists only after execution and output freezing. The proposal binds the output contract in advance. |
| Isolation | Unknown code runs inside a VM or microVM boundary with a separate kernel. A container may provide an additional internal layer. |
| Authorization | Separate `execute` and `promote` decisions, each with its own single-use capability. |
| Evidence | A `PASS` reported by the model or the guest is not, on its own, an authenticated gate value. |
| Log | A tamper-evident log, with completeness and external anchoring treated as separate conditions. |
| Manual switch | `ALLOW ONCE` supplies consent for one specific decision; it cannot override invalid evidence. |
| Diagram | Declaration, observation and decision effect each have a separate contract. |

The execution plane is the Execution Gate. In v0, it is accompanied by a Device Gate baseline that protects the box's own managed ports and device inventory. Coverage of an entire room, independently powered devices and hidden radio paths is a later, separate boundary requiring its own evidence. Sections 13–17 develop this physical threat and its evidence requirements through the OpenAI case.

## 1. Exact threat model

The protected assets are the designated target area, the authorities managed by the broker, the identities of the policy and verifier, the use state of authorizations, and the binding between a decision and its observed effect. The first v0 target is a data directory on a separate test receiver. No protection claim is made for the user's entire everyday workstation.

### Attacker capabilities

- The attacker may fully control the model's response, the submitted package, source files, dependencies enclosed in the package and application execution. Privilege escalation within the guest is also assumed.
- The attacker may submit a forged `status.json`, a misleading test, a malformed archive, prompt injection content, an old result or evidence from another run.
- The attacker may attempt network escape, credential theft, parser exploitation, resource exhaustion, timing races, authorization replay and deception of the user.
- The network may drop, delay or duplicate packets. Processes may stop, the box may lose power and the clock may be wrong.
- The threat model includes an insider with legitimate building or workstation access but no authority to connect a new device, make recordings or change the box's policy. Such a person may place an unknown peripheral, a recorder drawing external power or an independent radio device. A known identity does not authorize every operation.

### Conditions of the guarantee

The box's firmware, host kernel and virtualization layer, the controller and broker, key management, the authorization database, and the target receiver and its access controls must remain trusted. Together, they form the trusted computing base (TCB). The guest and submitted application tests are outside this base. A controller defect or compromise of the TCB may invalidate the guarantee.

| Claim | Condition and limitation |
| --- | --- |
| Blocking unauthorized export | Every write passes through the receiver's controlled endpoint; the attacker has no alternative write authority. |
| Keeping secrets out of the guest | The v0 guest receives neither production secrets nor access to general-purpose broker calls that use secrets. |
| Precisely bound operation | Authorization binds the input, execution profile, target and output manifest; it does not prove the semantics of every internal application instruction. |
| Limiting new attacks | Closing unauthorized effect interfaces reduces the available opportunities. It does not establish the absence of unknown hypervisor or firmware vulnerabilities. |
| Human administration | The owner's recovery authority is a separate trust domain. An administrative bypass is not a protected model operation. |

Excluded claims are protection of the cloud provider, a general proof that code is malware-free, flawless program correctness, protection of the whole workstation, guaranteed availability and robot safety certification. The VM is itself a defense layer with its own attack surface. [W1–W4]

## 2. v0 boundary and operation profile

The v0 supports one workflow: run a frozen input package in a known runtime image, without a network or secrets, then place the selected result package as data on a preregistered test receiver. Export does not automatically grant authority for later execution.

| Profile | Permitted operation | Limitation |
| --- | --- | --- |
| `sandbox.run.v0` | One launch of a fixed runtime profile. | Only the VM's disposable disks are writable; there is no real external side effect. |
| `artifact.promote.v0` | Transfer the files of a sealed manifest as data. | Only into a new run directory on a preregistered receiver; no overwrite, merge or execution. |
| Later profiles | Repository operations, service APIs, networked tests or actuators. | In v0, these receive `BLOCK` as unknown operations; they require separate design. |

### Initial sizing limits

The initial policy, to be revisited after measurement, is one run at a time; at most 64 MiB of input and 100 MiB of extracted content; 4,096 files; 32 MiB of export; 1 MiB each for stdout and stderr; 120 seconds of execution; 2 vCPUs; and 2 GiB of guest memory. Ingress, parsing and logging receive separate quotas. These limits are not proposal fields that the model may override.

Only regular files and directories are permitted in an export directory. Symlinks, hardlinks, device files, sockets, FIFOs, execute permissions, extended attributes, ownership changes and arbitrary destination paths must not be transferred. A filename or MIME type is not security evidence. The receiver does not automatically open the content.

### Security boundary in everyday use

The user may manually upload a package created in the cloud to the box. This does not require integration with a model provider. A cloud agent that already has its own GitHub, filesystem or remote command execution authority can fall entirely within the PULSEbox boundary only after that authority is revoked or excluded at the protected target.

The first receiver may be a separate Linux test VM with a minimal import service. The browser on the user's everyday machine accesses only the management interface. If a receiver is later deployed on that machine, its privileges and parser surface require the same scrutiny. Manually launching a downloaded package is a new, separate operation.

### v0 acceptance claim

For the specified TCB, policy, runtime image and target receiver, every supported trial run and export must have a verified authorization bound to the same subject. Prohibited attempts and attempts with missing evidence must not write to the protected target area. The positive claim concerns the authorized operation, not the general harmlessness of the code.

## 3. Hardware and software architecture

PULSEbox is an application-level execution intermediary. It is not a transparent Ethernet bridge and does not depend on general decryption of encrypted traffic. Two network connectors may separate management from the target-side connection; the security property comes from authority controls and receiver validation. Separating the decision point from the enforcement point is consistent with NIST's PDP–PEP distinction. [W1]

| Domain | Components | Trust rule |
| --- | --- | --- |
| Proposal side | Cloud model, browser and uploaded package. | Cannot supply policy, an authenticated gate result or execution authority. |
| Intake | Bounded ingress, content-addressed store and isolated archive checker. | Bounded byte handling; an untrusted parser never receives signing or export authority. |
| Control | Policy and verifier registry, PULSE adapter, gate checker and decision signer. | Produces status only from trusted inputs; the run cannot write into this domain. |
| Enforcement | Supervisor, capability state store and operation broker. | Starts execution or exports only with a precisely bound, unused authorization. |
| Trial execution | VM or microVM with a separate kernel; optional container inside it. | Disposable and free of secrets; no host mount, management network or broker API. |
| Result examination | Sealed output, separate verifier environment and host observer. | Treats the guest's result as a claim; has no promotion authority. |
| Target side | Registered receiver, its own operation log and exclusive writer identity. | The target revalidates the export and makes it visible conditionally and atomically. |
| Human side | Local interface and physical switch. | May supply consent for a specific valid decision; cannot remove mandatory conditions. |

### Separating data from control

An upload enters the content-addressed store. The controller uses the object's digest, not the uploader's path. The supervisor receives a closed execution configuration. The VM's output becomes a new quarantine object. The verifier produces evidence from this object and the host's observations. The second decision applies to the sealed output manifest. The receiver accepts only objects matching that manifest.

Authenticated, typed messages pass between trusted interfaces. Any serial or vsock channel exposed to the guest may handle only a bounded data protocol; it must not relay general commands to the host. Root privileges in the guest must not grant access to the box's root domain.

### 3.1. Physical prototype baseline

| Element | Proposed initial choice | Condition to verify |
| --- | --- | --- |
| Computer | 64-bit x86 mini PC with at least four CPU cores. | KVM and hardware virtualization are actually usable; operation remains stable under load. |
| Memory | 16 GiB minimum; 32 GiB provides more headroom. | The controller's reserved budget remains separate from the guest quota. |
| Storage | At least 256 GB SSD; encrypted volume. | Durable transaction writes, storage quotas and recovery after power loss are tested. |
| Network | Two wired interfaces. | No automatic bridge, NAT or IP forwarding between domains. |
| Root of trust | TPM 2.0 and a verified boot chain. | The supported key algorithm, measurement procedure and recovery procedure are established. |
| Radios and peripherals | Wi-Fi and Bluetooth disabled or absent. | No USB, PCI or raw disk passthrough to the guest; no USB network bypass. |
| Controls | Latching `LOCK`, status indication and momentary `ALLOW ONCE` switch. | Power-on and controller failure lead to `LOCK`; the display identifies the specific request. |
| Supervision | Hardware watchdog; optional uninterruptible power supply. | A watchdog event must not cause automatic re-execution or export. |

This is a sizing baseline, not a list of selected products to purchase or a performance promise. A fanless design may be selected only after measuring thermal load. The v0 does not require a GPU because the model runs elsewhere.

#### Software profile

A minimal Linux host uses pinned kernel and VMM versions, with a guest kernel and read-only runtime image selected by digest. The reference profile may be a KVM-based microVM. With Firecracker, host isolation equivalent to the jailer and resource limits are required; the VMM alone does not filter guest networking. The v0 therefore gives the running application no virtual network device. [W2]

A rootless container, `no-new-privileges`, seccomp and an LSM profile are useful additional layers. A conventional container sharing the host kernel is not, by itself, the selected trust boundary. Seccomp filtering is not a complete sandbox either. [W3, W4]

The TPM may participate in key use and binding that use to boot state. It does not prove that a signed decision is correct, and it does not prevent every malicious signing request on an already compromised host. Key isolation also requires a narrow signing API and a verified policy. [W7]

## 4. Shared basis of the package contracts

The following fields are proposed normative contracts, not existing PULSEbox schemas. Every package is a closed, versioned object. An unknown schema, prohibited extra field, wrong type or missing required field results in `BLOCK`. A single pinned adapter interprets the consequential fields.

| Common field or rule | Requirement |
| --- | --- |
| `schema` and `version` | Exact registered contract identifier and version; no silent version change. |
| `installation_id` and `boot_epoch` | Installation identity and broker-generated boot epoch; authorizations from an earlier epoch are invalid. |
| `run_id` and `parent_binding` | Identifier assigned by intake; an explicit `root` marker for a root run, otherwise the parent run and parent package digest. |
| Digest references | SHA-256, 64 lowercase hexadecimal characters and byte length; content must be rehashed during full verification. |
| `policy_binding` | Policy ID, version, byte digest, gate registry digest, selected profile and materialized required-set digest. |
| `producer_binding` | Trusted component identity, source or binary digest and configuration digest; a self-reported producer label is insufficient. |
| Time data | Informational UTC and boot-bound monotonic time. Expiry checks must not rely solely on an adjustable wall clock. |
| Evidence reference | Type, producer, subject, run, digest, size, observation boundary and verifier result are all required. |
| `device_context_binding` | Topology digest, device state report digest and `inventory_epoch`; the evidence is valid for the specific operational boundary. |
| No self-reference | The package digest belongs in the external envelope. A hash and signature are not included in their own hash input. |

### Canonical bytes and signatures

The proposal is to reuse the reviewed PULSEmech Device Ledger canonical JSON profile unchanged and bound by digest: UTF-8, NFC under Unicode 14, 64-bit integers, no duplicate keys and no normalization collisions. This is not RFC 8785 JCS: the existing profile normalizes and uses UTF-8 byte ordering, while JCS specifies different rules. The two formats must not be described as interchangeable. [R6, W5]

The proposed signature envelope is JWS ES256, with fixed `alg`, `kid` and package-type fields. A local trust registry resolves the key; a submitted package cannot select a new trusted key. An explicit adapter and test vectors handle the different ECDSA encodings used by the TPM and JWS. Capability redemption remains a separate, stateful check. [W6]

The original bytes of retained source and output files must not be normalized. Canonical metadata is a separate object, and each path it contains must map unambiguously to the original file. For a nonportable or conflicting name, v0 rejects the input rather than silently renaming it.

### 4.1. Proposal contract

The model's raw submission is not an authenticated proposal package. Ingress first preserves the raw bytes, then binds the intake record to the authenticated submitter session. The `admitted_proposal` below is an immutable input validated under local policy. The model identifier is provenance metadata only.

| Field group | Type and meaning |
| --- | --- |
| `proposal_id` and `raw_submission` | Broker-assigned ID; digest and size of the raw submission. |
| `artifact_manifest` | For each file: relative path, type `file`, size, digest and input role; digest of the complete manifest. |
| `operation` | `sandbox.run.v0` in v0; the permitted entrypoint and argument array are bound exactly. |
| `runtime_binding` | Digests of the runtime profile, guest kernel, image, dependency inventory and supervisor configuration. |
| `execution_context` | Working directory, complete environment-variable allowlist, locale, resource limits and deadlines. |
| `network_profile` and `secret_profile` | Must be `no_network` and `no_secrets`. An unknown or general-purpose proxy request must be rejected. |
| `target_intent` | Preregistered receiver ID and type of new export area; this does not yet authorize export. |
| `output_contract` | Permitted result types, name and size limits, verifier list and contract digest. |
| `expected_output` | Optional advance byte expectation when the specific result is already known. Its absence must not be replaced with an invented digest. |
| `requested_evidence` | The model may request checks; only the local trusted profile determines the mandatory evidence set. |
| `source_binding` | Source snapshot digest; for Git-based input, repository identity, commit and an inventory of the actual file contents. |
| `lifetime` and `parent_binding` | Lifetime of the admitted request, parent run and contracted parent result, or an explicit root relationship. |

#### Preventing discrepancies between verification and use

The supervisor receives only verified objects from the content-addressed store, according to the frozen manifest. It rechecks the input disk image digest before execution. An opened object must not be replaced after verification by another file with the same name. The profile must not contain a mutable tag, a `latest` reference or dependency downloads during execution.

An exact launch command does not mean that every subsequent internal effect is known in advance. The application may compute new data or start child processes within the guest, subject to the resource profile. Authorization of external operations reaching the protected boundary remains the broker's responsibility.

### 4.2. Decision contract

A `decision` package records the result of evidence verification and policy application. It has two phases: `execute` before the trial run and `promote` after it. The two decisions bind to the same root proposal, but have different subjects and mandatory gate sets.

| Field | Requirement |
| --- | --- |
| `phase` and `verdict` | `phase = execute` or `promote`; `verdict = ALLOW` or `BLOCK`. `REVIEW` is a workflow state, not execution authority. |
| `subject_digest` | For `execute`, the identity of the `admitted_proposal`; for `promote`, the identity of the sealed result and output manifest. |
| `evidence_manifest_digest` | Sealed manifest of the evidence actually used; the raw evidence must also be retained. |
| `policy_binding` | Identity of the locally selected policy, registry, profile and nonempty required-set. |
| `verifier_binding` | Exact version, binary or source digest, configuration and result of each verifier that was run. |
| `status_digest` and `gate_results` | Status produced by the trusted adapter; value, evidence reference and error code for each gate. |
| `hard_blockers` | List of mandatory failures. Missing evidence, an unknown authority field or an invalid digest cannot be overridden by a human button press. |
| `consent_requirement` | Mandatory human consent in the `promote` phase, bound to a specific `decision_digest` and target. |
| `validity` and `revocation_epoch` | Lifetime, boot epoch, policy epoch and revocation state. |
| `signature` | Signature from a registered decision-signing key; no authority effect before verification. |

#### Required order for producing a decision

The adapter first strictly validates the packages and producer bindings, then recomputes the gate values derived from evidence. It materializes the required-set from policy and binds it to the status. Only then may it call the original strict gate checker. Exit code `0` may support an `ALLOW` decision only as part of this complete chain of preconditions. [R2–R5]

The checker does not independently verify signatures, policy correctness or the status producer. Passing a submitted `status.json` directly to it is therefore prohibited. The adapter also rejects duplicate JSON keys before invoking the checker. The earlier CI-bound `release_decision_v0` package does not automatically become a local execution authorization.

If the log or signature cannot be written durably, `ALLOW` must not be issued. The system must not claim that a `BLOCK` record lost to a power failure had already been created. Recovery records an evidence gap in that case.

### 4.3. Capability contract and redemption

A single-use capability consists of a high-entropy random handle of at least 256 bits and a broker-side authorization record. Neither the model nor the guest receives it. For `execute`, the authenticated supervisor may use the record bound to it; for `promote`, the registered receiver and export broker may use the record bound to them.

| Authorization record | Requirement |
| --- | --- |
| `capability_id` and `handle_hash` | Unique ID; the secret handle may be stored in the redemption database only as a verification hash. |
| `decision_digest` and `operation_digest` | Exactly one `ALLOW` decision and one normalized operation identity. |
| `audience` and `peer_identity` | Only the named supervisor or sink adapter; a stolen handle must not be usable under a different identity. |
| `subject` and `target` | Digest of the input to execute or the manifest to export; exact receiver and target area. |
| `precondition` | An `absent` expectation for a new target directory; a specific prior-state digest or strong version precondition for a later modifying profile. |
| `max_uses` and `delegation` | `max_uses = 1`; transfer, widening and issuance of subauthorizations are prohibited. |
| `validity` | Boot-bound monotonic expiry. The initial redemption window is 60 seconds; the execution deadline is a separate field. |
| `consent_binding` | Physical or local consent bound to the specific decision and target; mandatory for `promote`. |
| `state` | `ISSUED`, `RESERVED`, `COMPLETED`, `REVOKED`, `EXPIRED` or `INDETERMINATE`. |
| `transaction_binding` | Binding between a unique operation transaction identifier, the durable advance log and the target-side receipt. |

#### Atomic use

In one durable transaction, the broker checks the authorized peer, freshness, policy epoch, subject and target precondition, then transitions the record from `ISSUED` to `RESERVED`. Only one concurrent redemption of the same capability may succeed. Execution may begin only after a successful durable reservation.

A successful receipt leads to `COMPLETED`. A crash or an uncertain network response leads to `INDETERMINATE`, without automatic retry. After reboot, every unfinished authorization belonging to the previous boot is invalid. Separate reconciliation uses the target-side `transaction_id` and receipt.

This aims for at most one authorization-use attempt and idempotent state reconciliation at the supported receiver. It does not promise exactly-once side effects on arbitrary external APIs under network failure. The v0 does not support an operation without the receiver's required transaction contract.

### 4.4. Result and export receipt contracts

| Result field | Meaning and verification boundary |
| --- | --- |
| `proposal` and `execute_decision` | Digests of the input and trial-run decision; supervisor ID, boot and capability ID. |
| `runtime_observation` | Binding to the image and configuration actually launched, with host-recorded start and stop. |
| `termination` | Exit code, timeout, kill, crash or unknown termination. Exit code `0` alone is not export authorization. |
| `output_manifest` | Paths, sizes and digests of the frozen regular files; total size, file count and manifest digest. |
| `stdout` and `stderr` | References to bounded raw byte objects. The interface displays them with escaping. |
| `effect_observation` | Boundary observations and deny events available to the host; application-reported internal events are recorded separately. |
| `coverage` | Profile-bound `required_observations`, `observed`, `missing` and `collector_errors`; `unknown` must not be rewritten as `false` or `PASS`. |
| `verification_results` | For each verifier: subject, version, input digest and `PASS`, `FAIL` or `UNRESOLVED`; guest-supplied results carry a provenance label. |
| `cleanup_receipt` | Verification of shutdown, detachment and removal of the VM and its associated resources. |
| `pre_result_log_head` | Log head and sequence before result creation. Recording the result is the next event; no circular hash. |

#### Required receiver procedure

The receiver authenticates the broker; verifies the `promote` decision, bindings of gates and consent, and the authorization's online use state; then copies the files into its own private temporary area. It does not open arbitrary archive formats in a privileged context. It rehashes the transferred files, checks paths and prior state, then atomically makes a new run directory visible.

The export receipt contains `transaction_id`, the receiver identity, the `promote` decision and capability IDs, the requested and actual manifest digests, the target's prior and resulting states, and a result of `committed`, `not_committed` or `indeterminate`. Only the state actually observed may be asserted.

Automatic execution, hooks, indexing plugins and active HTML previews are prohibited at the target. An authorized export may still contain logically defective or malicious code as data. Running that code later is a separate authorization operation. A `noexec` flag alone is insufficient because an interpreter can read the file as data.

## 5. Authority model and bypass paths

Non-bypassability applies to the designated target and attacker identities. Every path from such an identity to a protected effect must pass through the controlled enforcement point. A configuration inventory and active negative trials must jointly support this claim; not seeing an operation in a network log does not, by itself, prove that the path is absent.

| Effect interface | Exclusive authorized actor | Alternative path to close |
| --- | --- | --- |
| Starting a guest | Supervisor with a valid `execute` capability. | Direct Docker socket, general-purpose SSH, host shell, unrestricted libvirt or VMM API. |
| Writing the target directory | Receiver service's dedicated OS identity. | Another writer account, shared mount, SMB or NFS, sync client or agent tool. |
| Initiating export | Operation broker and registered receiver. | A cloud connector's direct target authority, another proxy or another export API. |
| Changing policy | Separate administrative release process. | Model-supplied policy, writable registry or replaceable required-set. |
| Using a key | Narrow broker or signing service. | Environment secret, guest key, general-purpose signing or HTTP proxy. |
| Repository operations, later | Dedicated target adapter with server-side restrictions. | PAT, SSH key, App token, browser administration or another automation write path. |

### Security invariants

- **P1:** A protected effect may arise only from a valid decision bound to the same subject and a single-use authorization.
- **P2:** Neither the model nor the guest may write policy, an authenticated gate result or export authority.
- **P3:** The authorized and used input, runtime, target and output match by digest.
- **P4:** No `promote` is permitted when mandatory evidence is missing, an observer fails or cleanup cannot be established.
- **P5:** An operation with an uncertain outcome must not restart automatically.
- **P6:** After `LOCK`, a policy change, expiry or a boot change, affected unused authorizations are invalid.

Hiding a secret is insufficient: a broker that sends requests to arbitrary URLs could execute an attacker's request using its own key. A later API adapter must therefore bind the exact HTTP method, target identity, normalized path, body digest and response rule. Redirects, DNS rebinding and credential forwarding require separate prohibition or a new decision. No such general-purpose call exists in v0.

## 6. Isolated execution lifecycle

| Stage | Required action | On failure |
| --- | --- | --- |
| 1. Intake | Size limits, raw-byte preservation and strict format validation; archives processed in a separate parser environment. | Rejection and a bounded quarantine record. |
| 2. Freeze | Establish the manifest and subject identity; seal the input and runtime disk images. | `BLOCK`; no launch. |
| 3. Preliminary decision | Verify producer and policy bindings, sandbox profile and required-set. | `REVIEW` if needed, but no capability. |
| 4. Reservation | Persist the `execute` capability as `RESERVED`; verify the exact launch configuration. | Close or reconcile without restarting. |
| 5. Isolated launch | Fresh VM, limits, readable input and disposable writable output; no guest network. | Abort the run; quarantine. |
| 6. Execution | Host supervision, deadline, memory and I/O quotas; continuous `LOCK` checking. | Stop; no export if the observer fails. |
| 7. Seal output | Stop every guest process; make output unwritable; isolated extraction, hashing and manifest creation. | Quarantine; do not export uncertain bytes. |
| 8. Verification | Separate verifier environment; compare host evidence with output; check the complete profile. | `FAIL` or `UNRESOLVED`; no `promote`. |
| 9. Cleanup | Remove the VM, mounts, networking and temporary resources, and verify removal. | `FAULT_LOCKED`; no new run until corrected. |
| 10. Export decision | Exact output manifest, target state and human consent; separate `promote` capability. | The result remains in quarantine. |
| 11. Target-side commit | Receiver validation, conditional atomic publication and authenticated receipt. | `INDETERMINATE` if commit status cannot be established. |
| 12. Closure | Bind the receipt, gate state and log head; close the authorization. | No unsupported `SUCCESS` assertion. |

The host must not mount, with privileges, a filesystem that the guest can arbitrarily modify. Output extraction takes place in a separately isolated helper process or helper VM, using a bounded, simple file-transfer protocol. The trusted store writes and hashes the final output object.

Deleting a disposable disk does not automatically mean physical data destruction. The v0 therefore provides no secrets to the guest. Storage encryption, per-run keys and retention periods are separate data-handling protections. Only quota-limited quarantine objects needed for evidence are retained.

## 7. Reusing PULSEmech elements

The observations below are based on reading commit `d44bf963cbac377366e95ae7ac9e3603fff894a4` of `HKati/pulse-release-gates-0.1`. This plan does not modify that source. Reuse does not automatically transfer properties established in CI to the device's new operating environment.

| Existing element | Reusable part | New proof obligation |
| --- | --- | --- |
| Authority chain and tuple [R1] | Bind subject, evidence, artifact, policy, required-set, verifier, status and terminal decision. | Actual enforcement by the supervisor and receiver that replace the CI result. |
| `check_gates.py` [R2] | Accept only literal `true`; reject missing gates and invalid status. | Authenticated status producer, strict parser and complete prior evidence validation. |
| Policy materializer [R3] | Derive a list from the declared gate set; reject an empty or missing non-advisory set. | PULSEbox profile, registry, digest binding and adapter; the minimal YAML parser is not a general policy interpreter. |
| Gate policy [R4] | Separate required and advisory roles. | A new, separately approved box profile. Current AI release gates do not automatically cover machine operations. |
| Recorded evidence verifier [R5] | Methods for run, subject, policy and producer bindings, reconstruction and replay. | New box evidence types; the current production release verifier is not a universal sandbox verifier. |
| Device canonical JSON [R6] | Exact canonicalization profile and the basis of existing test vectors. | Verification of new package types, a new trust registry, key lifecycle and hardware use. |
| Release decision schema [R7] | A pattern for carrying decision conditions and errors in structured form. | Separate `execute` and `promote` schemas; the `stage` and `prod` labels are not operation capabilities. |
| Whole System Discovery [R8] | Precise handling of obligations, relations, partiality and observation boundaries. | Separate runtime observer and explicit authority adapter; the original `authority_effect` remains `none`. |

At the pinned baseline, policy 0.1.7 treats an unknown status gate as `WARN` and contains inactive candidate sets. PULSEbox does not change that behavior retroactively. In its own closed authority contracts, an unknown operation, schema or mandatory gate identity is blocking; a separate diagnostic namespace cannot grant authorization.

The Device Ledger's signing and reproduction pattern is a useful foundation, but it is not evidence of an operating PULSEbox hardware key chain. Certified or actual TPM origin can be supported only by the prototype's own retained measurements and key registration.

## 8. Required new components

| Component | Responsibility | Output |
| --- | --- | --- |
| Ingress and parser isolation | Bounded submission, safe archive processing and separation of raw and canonical metadata. | Intake receipt and admitted proposal. |
| Object store | Byte-faithful storage, digests, quarantine, quotas and retention rules. | Input and output objects with immutable identities. |
| Box policy adapter | Connect box schemas, required-set and new evidence types to the existing checker. | Evidence manifest, status, `execute` or `promote` decision. |
| Capability broker | Narrow operation contract, identity and durable single-use authorization handling. | Reservation, revocation, state and receipt binding. |
| VM supervisor | Launch a closed profile; enforce resource limits and `LOCK`; provide trusted boundary observations. | Launch, shutdown, resource and cleanup evidence. |
| Output and verifier adapter | Extract stopped output, create a manifest and run the verifier separately. | Bound result and observation completeness. |
| Target receiver | Manifest validation, target precondition, exclusive writing and atomic commit. | Target-side export receipt and idempotent reconciliation. |
| Log and checkpoint | Sequence, hash linkage, signed checkpoint and external anchoring. | Verifiable event sequence with explicit gaps. |
| Local interface and switch | Display the exact subject; provide one-time consent and blocking. | Consent bound to a decision digest, or a `LOCK` event. |
| Trust bootstrap and updater | Key registry, measured boot, signed updates, rollback and recovery. | Versioned, verifiable TCB identity. |

### Minimal dependencies between components

The broker does not execute a shell supplied in the proposal. The supervisor constructs the VM launch from a closed template. The verifier may write only a report, which the decision signer also validates. The logger receives no target write authority. The interface cannot access secret handles. The recovery interface is outside the normal execution API and separated both physically and by privilege.

The narrow initial profile keeps the system's size manageable: one runtime environment, one result contract and one receiver type. It does not require its own language model, a GPU, a general agent platform or a universal network inspector.

## 9. Fail-closed state machine

Device state and individual run state are separate objects. Device states are `BOOT_LOCKED`, `READY`, `LOCKED` and `FAULT_LOCKED`. After boot, transition to `READY` is permitted only with a verified TCB, valid policy, working log, fresh authorization epoch and registered receiver. The switch state must never override `FAULT_LOCKED`.

| Run state | Condition for progression | Next state |
| --- | --- | --- |
| `RECEIVED` | Format, quota and subject binding are valid. | `BOUND`; otherwise `QUARANTINED`. |
| `BOUND` | The `execute` gates pass. | `EXEC_AUTHORIZED`; otherwise `BLOCKED` or `REVIEW`. |
| `REVIEW` | New or clarified bound evidence arrives and is rechecked. | `BOUND` or `RESULT_BOUND`; no direct path to `RUNNING`. |
| `EXEC_AUTHORIZED` | A valid capability is durably `RESERVED`. | `RUNNING`; `BLOCKED` on expiry or prohibition. |
| `RUNNING` | Normal termination, sealed output and valid observation. | `RESULT_BOUND`; otherwise `QUARANTINED`. |
| `RESULT_BOUND` | Verifier, cleanup and target binding are valid. | `PROMOTION_REVIEW`; otherwise `BLOCKED`. |
| `PROMOTION_REVIEW` | The `promote` gates and exact consent are valid. | `PROMOTE_AUTHORIZED`. |
| `PROMOTE_AUTHORIZED` | Authorization reservation and target precondition are valid. | `COMMITTING`. |
| `COMMITTING` | The receiver committed the bound result and supplied an authenticated receipt. | `COMPLETED`; `INDETERMINATE` for an uncertain response. |
| `INDETERMINATE` | Separate reconciliation against target-side state and `transaction_id`. | `COMPLETED` or `NOT_COMMITTED`; no blind rerun. |
| `BLOCKED` or `QUARANTINED` | A corrected package, new digest and new decision are required. | A new run; the old decision must not be rewritten. |

### Exact meaning of the physical controls

`LOCK` prevents new authorizations from being issued, revokes redeemable authorizations and interrupts a running trial. It does not undo an external effect that has already committed. Target-side serialization is required at the boundary before and after commit; if the ordering cannot be established, the state remains `INDETERMINATE`.

`REVIEW` permits only examination of the evidence and specific effect. The momentary `ALLOW ONCE` signal binds to a displayed decision, target, manifest and short time window; it does not leave a general `ALLOW` mode switched on. The actual failure modes of the relay, watchdog and GPIO must be checked in the physical prototype. This is not yet a robotics emergency stop.

### 9.1. Logging, observation and updates

#### What the log can prove

Every relevant record contains installation and boot identifiers, an increasing sequence number, the previous record's hash, event type, run and operation identities, subject references, producer identity, monotonic time and informational UTC. The chain is closed by signed checkpoints. The separate target receiver also durably records the pre-export checkpoint and commit receipt.

The appropriate description is a tamper-evident log with verified appends. A signed local file alone does not establish completeness, absence of deletion or the true wall-clock time. External anchoring and state reconciliation are needed against rollback of the whole chain and issuance of divergent views. Transparency logs also treat the append-only property and the risk of divergent views separately. [W8]

The TPM-bound boot epoch, durable authorization state store and receiver's earlier checkpoint jointly guard against restoring old authorizations. An execute-only run log without an external checkpoint is local evidence; it must not be described as an externally verified complete history. If a mandatory checkpoint cannot be written, there is no export.

#### Observation boundary

The observable v0 claim covers the VM configuration, launch and shutdown; permitted or denied I/O at the host boundary; actual output bytes; and the target-side receipt. It does not claim a complete syscall history inside the guest or observation of the provider's internal path. A test log produced by the guest remains self-reported.

The `coverage` rule does not mean that everything was observed. It means that every observation required by the selected profile is available. A collector error, lost record or missing cleanup blocks export. An empty error list cannot replace an observation requirement missing from the profile.

#### Updates and recovery

Updating the box is a separate administrative operation. It requires a preregistered update trust root separate from the normal decision key, a signed image manifest, an exact digest, a supported version and a minimum permitted rollback version. The running system's own PULSE decision cannot be the sole approval for a new trust root selected by that same system.

Before an update: enter `LOCK`, resolve active operations, revoke capabilities and create a checkpoint. Use A/B system partitions, verified boot, a startup self-test and, if needed, rollback only to a previously accepted version. Recovery is a separate owner procedure requiring physical access; it creates a new boot epoch and a verifiable administrative event.

## 10 Proposed gates and test rules

The following gate identifiers are proposals for PULSEbox's own profile. They are not existing, activated repository gates. Each phase's materialized required set must be nonempty, versioned and bound to a digest. Diagnostic metrics must be stored separately.

| Required execute gate | What it establishes |
|---|---|
| `box_proposal_bound` | Binding of the schema, raw and admitted objects, exact input manifest and current run. |
| `box_policy_bound` | Identity of the local policy, registry, required set and verifier. |
| `box_runtime_pinned` | Agreement between the runtime image, kernel, launch profile and actual configuration. |
| `box_isolation_ready` | A trusted supervisor, a no-network profile, absence of secrets, quotas and closed host interfaces. |
| `box_audit_ready` | A durable log and capability state store, with a valid boot epoch. |
| `box_operation_allowed` | A known, narrow operation and target profile, with no request for a prohibited side effect. |

| Additional promote gate | What it establishes |
|---|---|
| `box_result_bound` | Binding between the execute decision, actual runtime and finalized output. |
| `box_observation_complete` | Every host observation required by this profile is present, without errors. |
| `box_output_contract_ok` | Files, quotas, the output contract and required verifier results satisfy the requirements. |
| `box_cleanup_verified` | Destruction of the trial runner's resources has been verified. |
| `box_target_ready` | The registered receiver and exact target precondition are valid, and the checkpoint can be recorded. |
| `box_consent_bound` | Approval applies to the specific promote decision, output and target. |

The capability's current usage state, expiry, LOCK state and target pre-state must be checked again at actual redemption. These cannot be frozen permanently into an earlier gate value of PASS.

Both phases also require `box_device_context_bound`: the state of the relevant managed ports and the topology epoch must satisfy the profile. A relevant new device, port change or observation failure creates a new epoch and revokes affected capabilities, subject to the boundaries in sections 14–16.

### Acceptance of test evidence

For every test, preserve the pinned TCB and policy, input object, injected fault, expected and actual decisions, target pre-state and post-state, log and verifier report. In negative tests, the protected target's write observer checks that the prohibited effect did not occur. The following matrices describe proposed tests; their status in this design is **NOT_RUN**. The expected behavior is an acceptance requirement, not a reported test result.

### 10.1 Negative tests for admission and launch

| ID | Attack or failure | Expected behavior |
|---|---|---|
| N01 | Missing required field, unknown schema or unknown operation. | BLOCK before issuing a capability. |
| N02 | Duplicate JSON key, invalid UTF-8 or an NFC name collision. | Strict rejection, with no alternative parser interpretation. |
| N03 | `1`, a string, `null` or a missing gate in place of `true`. | The checker does not return PASS. |
| N04 | A fabricated, model-produced status or producer-trust label. | The adapter does not accept it as an authority input. |
| N05 | Empty required set, omitted gate or a different policy digest. | BLOCK; no reduced condition set. |
| N06 | A `../` path, absolute name, symlink, hardlink or device file. | The parser rejects it; no host file is written. |
| N07 | Archive bomb, excessive file count or oversized stdout. | Termination at the quota limit; the controller remains operational. |
| N08 | Bytes replaced under the same filename after verification. | Digest or object-identity mismatch; no launch. |
| N09 | Evidence from another run, parent, boot or installation. | Binding failure; no inherited PASS. |
| N10 | An image tag moves, or the runtime is modified. | Only the pinned digest may be used; a mismatch causes BLOCK. |
| N11 | Environment variables or the working directory alter the launch. | The normalized operation digest differs; launch is prohibited. |
| N12 | The guest reaches the Docker socket, a host mount or a management API. | Access is actually denied; successful access means the profile has failed. |
| N13 | IPv4, IPv6, DNS, link-local, a metadata endpoint or radio egress. | No guest network path exists; an active boundary test establishes this. |
| N14 | Root inside the VM and creation of a different namespace. | No host or target rights are obtained; the VM boundary remains effective. |
| N15 | Fork, memory, disk or CPU overload. | Termination at the quota limit; no export; capacity remains available to the controller. |
| N16 | Reading a secret through the environment, a file, a log or a broker call. | The canary secret does not appear in the guest or its output. |
| N17 | Deceptive UI content and active HTML in the log. | Escaped display; no new command or consent is created. |
| N18 | The guest forges the supervisor protocol. | Type and identity checks reject it; no host operation occurs. |

The parser, broker protocol and receiver are separate fuzzing targets. Controlled reproduction of known isolation failures may take place in a separate test environment. Passing the negative-test matrix does not prove the absence of every unknown kernel vulnerability.

### 10.2 Negative tests for capabilities and target effects

| ID | Attack or failure | Expected behavior |
|---|---|---|
| N19 | The same capability is submitted twice, concurrently. | Exactly one transition to RESERVED; the other request is denied. |
| N20 | A capability is used with a different audience, peer, target or operation. | Redemption is denied; the protected target remains unchanged. |
| N21 | An expired capability or a wall clock that has been set back. | Denial based on monotonic time and the boot epoch. |
| N22 | A new boot or restoration of an old state-store snapshot. | An old capability does not become valid again; antirollback protection and receiver reconciliation apply. |
| N23 | The policy or trust registry changes after the decision. | The affected capability becomes invalid; a new decision is required. |
| N24 | Invalid JWS, unknown key, `alg` substitution or a fixture key. | Signature or trust verification causes BLOCK. |
| N25 | A fabricated guest-test PASS or an omitted output file. | The bound manifest and trusted verifier do not accept it. |
| N26 | The observer stops or loses a record. | Coverage is incomplete; no promote. |
| N27 | Output is modified after execution or verification. | The hash differs; export is prohibited. |
| N28 | A VM or mount remains after cleanup. | FAULT_LOCKED; no export and no next run. |
| N29 | Export to a different target or an existing target directory. | The receiver's target precondition blocks it. |
| N30 | Partial transfer, lost receipt or a disconnected connection. | No partial result becomes visible; an uncertain commit is INDETERMINATE. |
| N31 | Power loss before reservation, after reservation or during target commit. | No blind retry; durable state and reconciliation by target-side `transaction_id`. |
| N32 | LOCK during launch, execution or at the commit boundary. | New effects are prohibited; the race is resolved or remains indeterminate, and an earlier commit is not denied. |
| N33 | ALLOW ONCE applies to another request or an old screen. | Decision and consent bindings differ; denial. |
| N34 | The log fills up, is deleted, is rolled back or forks. | Checkpoint or completeness mismatch; no new export. |
| N35 | The receiver is bypassed through another identity or connector. | Writing is denied; success means the entire protection profile has failed. |
| N36 | A harmful program is presented as exportable data but requests execution. | It may be examined as data; v0 grants no permission for target-side execution. |
| N37 | An unapproved or older system update. | The update trust root and minimum-version rule reject it. |
| N38 | The diagram turns a partial or unavailable signal into ALLOW. | Recalculation and policy prohibit authority escalation. |

## 11 Build and acceptance stages

The sequence reduces the risk of unsupported assurance claims. First demonstrate the two decisions and target-side enforcement, then the claims bound to hardware. There are no measured implementation or test data yet on which to base calendar estimates.

| Stage | Deliverable | Condition for proceeding |
|---|---|---|
| D0 Contracts | Schemas, threat model, operation profile and required set finalized from this plan. | No unresolved authority ambiguity; the two decisions and treatment of unknown states are explicit. |
| D1 Software decision demonstrator | Content binding, trusted evidence adapter, two decisions, a single-use capability and a test receiver. | Exact bytes in a positive example; rejection of digest substitution, fabricated status and concurrent replay. No hardware assurance yet. |
| D2 Actual isolated execution | A fresh VM, a no-network and no-secrets profile, output finalization, a separate verifier and cleanup. | Relevant N01–N18 and N25–N28 tests; guest root cannot access a protected resource. |
| D3 Transactions and failures | Durable capability state, receiver commit and receipt, restart and reconciliation. | N19–N35; no unintended second side effect after power or network failure. |
| D4 Physical prototype | A separate machine, TPM key, boot measurement, switch, watchdog and update path. | Actual physical fault injection, rollback trial, hardware-origin verification and LOCK testing. |
| D5 Independent verification | Carrier and event verification by another verifying process or machine. | The decision can be reconstructed; limitations and observation gaps are reproduced as well. |
| D6 Additional target profile | A separate repository, API or later actuator profile. | Its own contract, bypass-path inventory, target-side enforcement and negative tests; no automatic inheritance of rights. |

### Concrete objective of the first demonstration

A small, deliberately simple processing package produces a sorted result file from input text. With an execute capability, it runs in a fresh VM. The box finalizes and verifies the result. After a separate ALLOW ONCE, a file with the identical bytes appears at the test receiver. Throughout the run, the VM has neither secrets nor a network.

The first demonstration should include five broken variants of the same example: substituted input, fabricated status, a network attempt, output modified after verification and a capability redeemed twice. For each variant, the receiver establishes that the prohibited effect did not occur. This is the smallest meaningful end-to-end PULSEbox evidence demonstration proposed by this plan.

Acceptance of the physical prototype requires every relevant negative test to pass and separately documented attack testing against the broker, parser and receiver. Performance, LOCK latency and recovery time must be measured rather than promised in advance.

## 12 Later integration of the Paradoxon diagram

The diagram's future role is a versioned declaration about a defined system boundary. It specifies components, identities, permitted edges, transitions, conditions and observation obligations. The diagram's signature binds the declaration's origin and integrity. Separate evidence must support agreement with the actual system.

| Integration point | Contract and limitation |
|---|---|
| Profile compile | The diagram digest and compiler/verifier version enter the policy; the required set of edges and observations is derived from them. |
| Proposal binding | The proposal is bound to the diagram version and requested path; the model cannot alter the permitted graph. |
| Runtime observation | The observer records actual component and edge identities within the declared scope; it cannot invent an edge it has not observed. |
| Transition assessment | The Transition Meter assesses the transition from bound observations. The diagram itself creates no new sensing capability. |
| Authority adapter | A separately approved policy converts the measurement result into a gate value; the measurement record has no execution right on its own. |
| Independent replay | The same diagram, policy, observation manifest and verifier are required. A new measurement cannot silently replace a missing historical measurement. |

### Preserve the existing Whole System Discovery statuses

In the pinned source, `candidate_match_status` includes `VERIFIED_COMPLETE_MATCH`, `VERIFIED_PARTIAL_MATCH`, `PLAUSIBLE_UNVERIFIED_MATCH` and `CONFLICTING_MATCH`; a missing prerequisite yields `NOT_EVALUATED`. `retrieval.retrieval_status` is separate: `not_evaluated`, `available` or `unavailable`. `result.search_outcome` may, for example, be `NO_VERIFIED_MATCH` or `RETRIEVAL_UNAVAILABLE`. These fields describe different subjects. [R8]

The initial combination of `PARTIAL_MATCH` / `NO_MATCH` / `RETRIEVAL_UNAVAILABLE` therefore is not a suitable shared runtime enum. PULSEbox needs a separate observation state, such as `COMPLETE`, `INCOMPLETE`, `UNAVAILABLE` or `CONFLICTING`, with its own precise meaning. The original discovery record retains `authority_effect = none`.

If required runtime evidence is missing, the operation remains blocked, while the UI may open a REVIEW task. Unavailability of an external search that is not required for the current operation does not, by itself, disable all operation. The relevant required set must be fixed in advance and cannot be weakened after execution.

The plan assigns distinct roles: the diagram declares the permitted system and proof obligations; observers supply data; the Transition Meter assesses; the PULSEmech policy decides; and PULSEbox and the target receiver enforce the specific authorization. Merely asserting that the graph is complete does not close alternative paths.

## 13 The OpenAI case as an example of evidence formation

The design cites a DOJ release dated 13 October 2026 describing criminal proceedings against an employee. According to that release, a concealed audio recorder was found in the USB port of a television in an executive meeting room, its contents were encrypted, and employment did not confer authorization to access that meeting room. The conduct described in the proceedings consists of allegations, not final findings of guilt. [C1], [C2]

| Reported time | Publicly reported allegation or event | Evidence category |
|---|---|---|
| Around 28 September | OpenAI placed the alleged installation around this time. | Reconstructed time; distinct from direct observation of installation. |
| Around 30 September | Physical discovery of the device at the rear of the television. | A physical observation described by the release. |
| Before the discovery | CCTV presence and internal-search data. | Circumstances from multiple sources; binding them together is a separate task. |
| 5 October | Footage of a person looking behind the television and discovery of a similar second device. | Separate events, each requiring its own time and object bindings. |
| 9 and 13 October | Arrest, followed by the release and initial court appearance. | Procedural events; they do not automatically establish the evidentiary strength of a technical conclusion. |

The reported role of OpenAI's models, and the reported absence of indications of unauthorized access to or removal of model weights, source code or customer data, are treated as company statements. The X post identifies the statement; reporting that quotes it supplies a fuller text. This does not establish every information path or clarify the contents of any audio recording. [C3], [C4]

### Distinguishing statements from direct evidence

The directly accessible object in this case study is the public statement. Raw CCTV, the original device, a forensic copy and the internal audit log are separate evidence not examined here. A PULSEbox record must therefore label their description `source_statement`, rather than adopt it as the box's own `directly_observed` measurement.

An actual preservation record would cover the inventory identifier, discovery location, photographs of the port and device, collecting person or sensor, time and its uncertainty, chain of custody, forensic-copy digest, measurement instrument and examination procedure. A digital hash alone does not establish the identity of a physical object.

An observation may be a recorded fact within its own boundary. A model may add a hypothesis and proposed investigation. Policy permits or denies technical access. Legal classification belongs to the authorized legal process. These four roles cannot be collapsed into a single score.

### 13.1 Physical attack paths and the v0 boundary

The input to an audio recording may be sound propagating through the room. That input does not pass through a repository, the machine's network interface or an AI execution capability. A peripheral's digital connection and physical acquisition of information are therefore separate boundaries. Physical introduction of a device can create a new sensor outside the authorization graph.

| Path | Protection required by the proposed v0 profile | Remaining boundary |
|---|---|---|
| A new USB data connection on the box | No new external USB authorization during normal operation. Default-deny before or early in boot, a port inventory and restrictions on physical access. | USB descriptor processing is itself an attack surface; a late userspace denial does not prevent every case. |
| A peripheral using power only | An unused managed port is physically closed and, where this can be verified, its power is also switched off. | Blocking data lines does not disable VBUS. A voltage measurement is required to substantiate a claim about power. |
| A port on a television or other external appliance | Only an endpoint separately brought under management is within scope; the v0 box does not automatically manage every port in the room. | The state of an unmanaged TV port is `unobserved`; it cannot be reported as `closed`. |
| Its own battery and radio | Explicit recording of the risk and observation gap; v0 makes no claim of room-wide closure. | The device may continue operating after external power is removed. The wired broker cannot automatically switch it off. |
| Local recording followed by later removal | An inventory of ports and access to devices, with a separate physical custody procedure. | Absence of live RF traffic does not rule out storage followed by manual removal. |
| New rights for an insider | Separate authorization for the person, role, device enrollment and policy administration. | Physical presence, a known name or an employee badge does not authorize a new data path. |

A device using power only is a general counterexample. The DOJ release alone does not establish whether the particular recorder also used USB data lines or which radio data path, if any, was actually active. Such a fact cannot be added to this case by inference.

Later versions would address an external port controller, hardware power and data disconnection, authenticated peripheral enrollment, managed switch ports, external device attestation, a physical inspection process and RF examination by appropriately qualified specialists. An RF examination also has boundaries in time, location, frequency and sensitivity; it does not prove the absence of every dormant or passive device.

## 14 Relationship between the Execution Gate and Device Gate

| Plane | Subject of the decision | Enforcement |
|---|---|---|
| Execution Gate | A specific proposal, execution or export. | Supervisor and target receiver, using an execute or promote capability. |
| Device Gate | The permitted function of a managed component and port, its topology binding and observable connections. | Host device authorization, a managed port controller and, later, an authenticated device adapter. |
| Shared policy binding | The device context and `topology_epoch` required for the operation. | The broker may issue an operation capability only with relevant, valid device evidence. |

Device authorization does not authorize code execution, and an execute ALLOW does not authorize admission of a new device. The v0 Device Gate is deliberately narrow: a frozen baseline device inventory, prohibition of new external peripherals during normal operation, and monitoring of port state and relevant topology changes. A dynamic, general `device.admit` capability belongs to a possible later profile.

### Device identity contract

| Field | Required meaning |
|---|---|
| `device_record_id` and `identity_evidence` | A local inventory object, with separate `claimed_identity` and `verified_identity`. The model cannot fill in a missing verified identity. |
| `assurance_profile` | `descriptor_only`, `controlled_enrollment` or `hardware_attested`; policy states which is sufficient for the particular function. |
| `descriptor_snapshot` | Original bytes and digests of manufacturer, product, serial-number, MAC and interface data. These are copyable claims, not cryptographic identities. |
| `cryptographic_binding` | Where available: registered public key, issuer and trust policy, fresh nonce, firmware measurement and verification result. Absence is explicitly `unavailable`. |
| `endpoint_binding` | Host identity, controller, physical port inventory, hub chain, interface, direction, function and observation epoch. |
| `physical_binding` | Enrollment procedure, device label, image or measurement, and custody relationship; the assurance level is a separate field. |
| Power and data state | Separate `requested`, `commanded` and `independently_observed` states; issuing a command is distinct from measuring its effect. |
| Validity and custody | Who enrolled the device and under what authority, when the binding is valid, and which change or disconnection invalidates it. |

Linux USB authorization and tools such as USBGuard can help prohibit use. A matching descriptor or serial number does not prevent identity spoofing; the Linux documentation specifically warns about this. A cryptographic device key also does not, by itself, establish a physical port location or the absence of another built-in radio. [W9], [W10]

### 14.1 Topology and device observation

Like the device identity records, the topology artifact uses the canonical format, signature and versioning rules in section 4. New or changed topology requires a new policy check. The visual drawing is a view of that machine-readable object; an image file alone is not an executable contract.

| Topology field | Content |
|---|---|
| `scope_id` and `scope_boundary` | The exact boundary of the protected machine, box, ports and, where applicable, room, including excluded areas and the time window. |
| `nodes` | Stable component ID, permitted identity profile, function, owner role, entry points and observation points. |
| `edges` | Source, target, specific port and function, direction, conditions, permitted state transitions and enforcement point. |
| `edge_type` | At least `power`, `data`, `control`, `acoustic_capture`, `radio_egress` and `physical_transfer` as distinct types. |
| `rights_owners` | Who may authorize a connection, execution, data access and export, with separate administrative roles. |
| `required_observations` | For every important edge: producer, measured property, freshness, evidence type and acceptance rule. |
| `alternative_paths` | Declared possible bypass paths, with evidence ruling them out or a statement that they are unobservable. The unlisted world cannot be treated as closed. |
| Trust and lifecycle | Topology digest, schema, signer, policy and compiler digest, epoch, validity and revocation. |

### Observation record

`device_observation` binds the raw event to the topology: `event_id`, `observer_id` and software or sensor version, `observed_at`, time uncertainty, physical or logical endpoint, raw-object digest, measurement method, coverage interval, gap list and observable properties. A separate field records whether the event is a connection, disconnection, descriptor change, port-power measurement, radio observation or human on-site inspection.

An unexpected USB device appears as an observed new node only if a sensor, host, port controller or authenticated on-site inspection actually detected it. An object drawing only power may not enumerate. A complete inventory at one instant does not establish continuous completeness, and a fresh signature does not refresh an old observation.

### Evidentiary limits of graph closure

Appropriate evidence must exist for every required edge, and a status must be given for every relevant bypass path. Completeness of the requirement set is itself a proof obligation. If the protected subject is speech in a meeting room, a microphone, local storage, radio and physical removal may be relevant; closing the wired network does not establish their status.

## 15 Transition Meter axes for physical paths

The canonical Transition Meter at the pinned baseline specifies six separate status axes. The Device Gate preserves them and uses separate physical-path assessment fields beneath them. The label `NO_MATCH` does not replace a record with multiple axes. [R9]

| Canonical axis | Example for a physical device path |
|---|---|
| Observation | An authenticated port event may be `directly_observed`; an installation time derived from multiple sources is `reconstructed`; a model's guess about device origin is `hypothesized`. |
| Binding | `bound` requires the specific device, host, port, time and evidence to be properly associated. A USB serial number alone leaves the record `partially_bound` or `unbound`. |
| Consistency | `consistent`, `ambiguous`, `conflicting` or `internally_incomplete`. Divergent CCTV and device clocks cannot be reconciled silently without a justification. |
| Reproduction | `reproduced` describes a verifier result repeated from the pinned bytes; with `bounded_replay_only`, the physical event itself has not been repeated. |
| Causal | `sequence_only` or `correlated` is not `sufficiency_supported`. Finding the device does not establish who installed it or what data it removed. |
| Authority | The measurement and discovery record remains `none` or `diagnostic`. A Device Gate access decision is a separate authority object bound by policy. |

### Detailed assessment fields for the PULSEbox physical profile

| Field | Required assessment |
|---|---|
| `relation_change_observation_status` | Which observed relationship changed? Examples include a device appearing after an empty port, or an active data path following a disabled interface. |
| `transition_path_verification_status` | Which edges of introduction, connection, operation and possible data release are verified, reconstructed or missing? |
| `endpoint_binding_status` | Do all related records concern the same physical object, port, host and data sink? |
| `time_order_status` | Observed sequence, monotonic time, synchronized clocks and uncertainty intervals; exact time and ordering are distinct properties. |
| `alternative_path_closure_status` | Examination of wired, radio, cellular, local-storage and manual-removal paths; a missing path status prevents a claim of complete closure. |
| `reconstruction_reproducibility_status` | Does the raw evidence yield the same bound path assessment? Replay does not restore an unobserved physical event. |
| `causal_sufficiency_status` | Is there a set of conditions actually sufficient for the specific recording or removal of data? Encrypted content particularly limits this assessment. |
| `causal_necessity_status` | Can other causes or data paths be excluded? One discovered recorder does not establish exclusivity. |

## 16 Device states and decision consequences

The requested labels `NO_MATCH`, `PARTIAL_MATCH` and `RETRIEVAL_UNAVAILABLE` have the following narrow meanings only within PULSEbox's new proposed device-admission profile. They do not replace the Whole System Discovery candidate or retrieval enums. Match state, evidence availability and authorization outcome remain separate fields. The table also distinguishes an assessment not performed from a complete match.

| State | Meaning | Decision consequence |
|---|---|---|
| `NO_MATCH` | An observed device or connection does not match the permitted topology, function or identity. | BLOCK for the function in question. Deny data access and, under a separate rule, disable power to the managed port; lock the relevant run. |
| `PARTIAL_MATCH` | A verified binding exists, but at least one required identity, endpoint or path-closure condition is incomplete. | No ALLOW. A REVIEW task may be opened while the denial remains in force. |
| `RETRIEVAL_UNAVAILABLE` | The declared evidence-acquisition attempt has concluded, but the required result is unavailable within the recorded boundary. | The required permission is BLOCK; neither absence of a device nor absence of data removal can be asserted. |
| `NOT_EVALUATED` | The required assessment has not been performed. | BLOCK when it is a required prerequisite; it cannot be relabeled as unavailable or `NO_MATCH`. |
| `COMPLETE_MATCH` | Every required condition is verified within the specified scope and time window. | A narrow permission is possible only with a separate policy decision, freshness and current-state checks; this is not a claim of complete room security. |

### Permissible statements about data removal

| Statement | Required basis |
|---|---|
| We found no evidence of data release. | Specify the evidence type sought, search boundary and time window. This is a search result. |
| No data release occurred along the examined paths. | Complete, trustworthy observation of those paths, or an enforced and verified prohibition on transfer; zero log matches alone are insufficient. |
| Every relevant alternative path is closed. | An established, appropriate scope and requirement set, with closure evidence for every necessary path and a validity period. |
| Some paths were not observable. | Explicitly list the affected paths, missing sensor or access, and the consequence. |
| Complete path closure cannot be established. | At least one relevant obligation is unresolved or outside observation. Partial results remain valid within their bounds. |

A technical BLOCK is neither an accusation nor a finding of guilt. Absence of policy-required evidence may be sufficient to deny access; it does not imply malicious intent. A model inference may be retained as a `lead` or `hypothesis` record, with model, input and output bindings, but cannot replace a direct measurement.

## 17 Physical negative tests and acceptance criteria

The tests model these boundaries in an owned laboratory, using authorized devices and synthetic data. They do not call for surveillance of people or reenactment of the OpenAI case. The D-series tests supplement the N01–N38 matrix. All 54 tests—N01–N38 and D01–D16—are proposed, **NOT_RUN** tests in this design; the following results are expected outcomes.

| ID | Test | Expected outcome |
|---|---|---|
| D01 | Unknown USB mass storage, HID or USB network adapter. | Default denial; no new function usable by a driver and no target right. |
| D02 | A copy of an allowed descriptor, serial number and MAC address. | No automatic admission; the identity gap or conflict is explicit. |
| D03 | A composite device later exposes a new interface or a new hub. | The new function is denied and `topology_epoch` changes; no silent inheritance of rights. |
| D04 | A USB device operates solely from the power line and does not enumerate. | No false assertion of device-list completeness; a separate measurement verifies removal of power on a managed prohibited port. |
| D05 | The same situation on an unmanaged television port. | `out-of-scope` or `unobserved`; the box claims neither detection nor prevention. |
| D06 | A test device with its own battery and radio egress. | No claim of complete path closure. If the operation requires room-level closure, BLOCK. |
| D07 | Delayed radio transmission, or local storage followed by later manual removal. | RF silence does not become `exfiltration=false`; alternative paths remain unresolved. |
| D08 | Forged attestation, an old nonce or a relayed response. | Forged and stale evidence is rejected; with a relay, physical endpoint binding is incomplete without a separate assessment. |
| D09 | An employee badge or known login is used with unauthorized device enrollment. | A person's identity grants no new device or administrator right. |
| D10 | Another administrator account, SSH, USB boot or a connector bypasses the boundary. | Denial or demonstrated discovery of the bypass; success means the protection profile has failed. |
| D11 | A port event occurs before the collector starts, or the collector fails. | BOOT_LOCKED or a coverage gap; no retrospectively invented continuous observation. |
| D12 | The disable command succeeds, but VBUS or the data switch does not disconnect. | `commanded` and `observed` differ; FAULT_LOCKED, with no claim of closure. |
| D13 | A device is replaced between the device decision and capability redemption. | An epoch or endpoint change invalidates the capability. |
| D14 | The model names a perpetrator with certainty from CCTV. | It remains a hypothesis; no automatic identity or legal verdict. |
| D15 | Encrypted storage cannot be read, but the report claims that its content is empty. | Content is unavailable; the false no-data claim is rejected. |
| D16 | A new diagram omits a radio or physical bypass path. | The required-set completeness assessment rejects the weakening or records the scope limitation. |

### 17.1 Diagram integration and development gaps

#### Connecting the two planes

The future Paradoxon diagram is derived from the signed topology artifact. A verified compiler produces the Device Gate and Execution Gate conditions from it. A separate verifier assesses raw observations; PULSEmech decides using the required set for the particular operation. The digests of the diagram, measurement record, decision and capability are bound to the same topology epoch.

A change to firmware, device, port, radio or permissions invalidates the earlier measurement context according to an impact rule. There is no automatic path that turns a diagram rewritten by a model into active topology. Owner approval, signature, contract validation and a new requirements inventory are required.

On a relevant device change, `inventory_epoch` increments. Affected capabilities that have not yet been redeemed become invalid. An active trial run is interrupted; a commit follows the reconciliation rules in section 9. Detection and enforcement latency must be measured. Physical acquisition of information that occurred before the response cannot be prohibited retroactively.

#### Boundary of the existing Device Ledger

The pinned reference has `record_status = synthetic_reference`, `identity_scope = fixture_installation` and `key_origin_profile = fixture_software_p256`. Its verifier report maintains the boundaries `authority_effect = none`, `creates_device_control_authority = false`, `physical_measurement_claim = none` and `device_security_claim = none`. A correctly signed package and successful replay do not constitute live device discovery. [R10], [R11]

Before v0, the following must therefore remain explicit development gaps: binding a live producer to a physical endpoint; verified enrollment of a TPM- or Secure Enclave-origin key; measurement of port state; handling of observation gaps; and actual target-side enforcement of device rights. The demonstrator and preserved Device Ledger can provide a foundation, but they do not replace these measurements.

| Build stage | Device Gate addition | Acceptance boundary |
|---|---|---|
| D0–D1 | Identity, port, topology and observation schemas; synthetic adapters and decision states. | Fixture labels remain; neither physical detection nor TPM origin may be claimed. |
| D2–D3 | Actual host inventory, default-deny, relevant event observation, capability epoch and receiver binding. | D01–D03, D09–D11 and D13; denial of data access is not denial of power or radio access. |
| D4 | Physical port closure, measurable power state, boot binding, watchdog and actual device enrollment. | D04, D08 and D12; actual evidence supports device origin and the level of physical binding. |
| D5–D6 | Separate review, external ports, room and RF examination profiles where required. | D05–D07 and D14–D16; stronger claims are limited to boundaries actually observed and managed. |

Engineering priority: build the Execution Gate and the box's own basic Device Gate first. Physical information protection for the entire room must be designed as a separate profile. This preserves the feasibility of v0 while keeping devices physically introduced outside the digital topology within the threat model.

## Sources and verified baseline

**Source snapshot: 13 October 2026, design revision 0.2.** At the source inspection recorded by the original design, the repository's `main` branch resolved to commit `d44bf963cbac377366e95ae7ac9e3603fff894a4`. The sources provide the basis for reuse and architectural requirements. The PULSEbox components, contracts, tests and hardware parameters in this document are design proposals. This repository adaptation preserves that historical source baseline; it does not present the proposed system as implemented or the proposed tests as completed.

### Pinned PULSEmech sources

- **R1.** [PULSEmech Technical Overview][R1]
- **R2.** [Strict terminal gate checker][R2]
- **R3.** [Policy-to-require-list materializer][R3]
- **R4.** [Gate policy 0.1.7][R4]
- **R5.** [Recorded release evidence verifier contract][R5]
- **R6.** [Device canonical JSON contract][R6]
- **R7.** [Release decision v0 schema][R7]
- **R8.** [Whole System Discovery v0][R8]
- **R9.** [Canonical Transition Meter and its six status axes][R9]
- **R10.** [README and the Device Ledger reference boundary][R10]
- **R11.** [Device Ledger reference verifier report][R11]

### Primary technical sources

- **W1.** [NIST SP 800-207 Zero Trust Architecture][W1]
- **W2.** [Firecracker production host setup][W2]
- **W3.** [gVisor Security Model][W3]
- **W4.** [Linux kernel Seccomp BPF][W4]
- **W5.** [RFC 8785 JSON Canonicalization Scheme][W5]
- **W6.** [RFC 7515 JSON Web Signature][W6]
- **W7.** [Microsoft Trusted Platform Module fundamentals][W7]
- **W8.** [RFC 9162 Certificate Transparency Version 2][W8]
- **W9.** [Linux kernel USB authorization][W9]
- **W10.** [USBGuard rule language][W10]

External documentation is a live source. A later implementation must record its selected system-component versions, configurations and digests in its own dependency inventory. The plan claims neither standards certification nor a completed security product.

### Public sources for the case study

- **C1.** [DOJ Office of Public Affairs release dated 13 October 2026][C1]
- **C2.** [DOJ Northern District of California release dated 13 October 2026][C2]
- **C3.** [Identified original reference to the OpenAI Newsroom X post][C3]
- **C4.** [The Verge report quoting the OpenAI statement][C4]

The original source review recorded that the DOJ releases' text was accessible through search. Direct opening of the X post did not provide complete readable content; the post's original reference and indexed excerpt are treated separately from the fuller company statement quoted in reporting. This is not access to the company's raw internal investigation evidence.

The legal status is preserved together with the limitation in the authority's release: a complaint contains allegations and is not a judgment of guilt. The plan's technical access decisions are not intended to make legal determinations about people.

[R1]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/PULSEMECH_TECHNICAL_OVERVIEW.md
[R2]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/PULSE_safe_pack_v0/tools/check_gates.py
[R3]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/tools/policy_to_require_args.py
[R4]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/pulse_gate_policy_v0.yml
[R5]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/docs/recorded_release_evidence_verifier_v0.md
[R6]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/contracts/pulsemech_device_canonical_json_v0.json
[R7]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/schemas/release_decision_v0.schema.json
[R8]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/docs/PULSEMECH_TRANSITION_METER_WHOLE_SYSTEM_DISCOVERY_v0.md
[R9]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/PULSEMECH_TRANSITION_METER.md
[R10]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/README.md
[R11]: https://github.com/HKati/pulse-release-gates-0.1/blob/d44bf963cbac377366e95ae7ac9e3603fff894a4/examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json
[W1]: https://csrc.nist.gov/pubs/sp/800/207/final
[W2]: https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md
[W3]: https://gvisor.dev/docs/architecture_guide/security/
[W4]: https://docs.kernel.org/userspace-api/seccomp_filter.html
[W5]: https://www.rfc-editor.org/info/rfc8785/
[W6]: https://www.rfc-editor.org/info/rfc7515/
[W7]: https://learn.microsoft.com/en-us/windows/security/hardware-security/tpm/tpm-fundamentals
[W8]: https://www.rfc-editor.org/info/rfc9162/
[W9]: https://docs.kernel.org/usb/authorization.html
[W10]: https://usbguard.github.io/documentation/rule-language.html
[C1]: https://www.justice.gov/opa/pr/saudi-national-arrested-installing-surreptitious-audio-recording-device-openai
[C2]: https://www.justice.gov/usao-ndca/pr/saudi-national-arrested-installing-surreptitious-audio-recording-device-openai-san
[C3]: https://x.com/OpenAINewsroom/status/2110095403198849132
[C4]: https://www.theverge.com/ai-artificial-intelligence/1010642/openai-employee-arrested-recording-device
