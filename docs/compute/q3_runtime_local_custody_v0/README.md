# Q3 runtime input: owner-local custody and documentation v0

Date: 2026-11-02  
Status: owner storage decision recorded; local delivery prepared; owner-machine receipt not yet verified.  
Repository: `HKati/pulse-release-gates-0.1`  
Preparation base: `7bfd34dbd502f89bbf878ee37e9a1cfc5fb1e868`  
Authority effect: `none`

## 1. Owner decision and change boundary

The owner selected local preservation of the original runtime archive on their
own computer. Git LFS and paid remote storage are not authorized for this object.
Only this documentation and the two retained assessment records are intended
for the repository's `docs` tree.

This decision supersedes the earlier proposed Git LFS destination for the
selected archive. It does not authorize the upload of its payload to Git,
Git LFS, release assets or another storage service. It authorizes neither a
billing change nor a new spend.

Local preservation is not local installation or model execution. No self-hosted
runner, file server, tunnel, externally accessible folder or connection to the
owner's machine is established or authorized by this document.

This is an additive, documentation-only change. It does not modify the runtime,
workflow, profiles, checkers, capture handoff, CI manifests, release policy,
normative status, DOI or Software Heritage identities. The existing preservation
manifest and redistribution review remain unchanged as historical records.
The earlier destination is not an active instruction for this selected object.

## 2. Exact selected original archive

| Field | Identity |
| --- | --- |
| Filename | `q2-runtime-preparation-37148637546-1.zip` |
| Original repository | `HKati/pulse-release-gates-0.1` |
| Original run / attempt | `37148637546 / 1` |
| Original artifact ID | `11282419957` |
| Original source commit | `77fc5d51896568db50a2a87f650711a65db8fe8c` |
| Original archive size | `508460811` bytes |
| Original archive SHA-256 | `b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9` |

The archive was recovered from an existing owner Library copy, not by a new
successful download from the original GitHub artifact endpoint. The recovered
bytes retain the original object identity; they do not create a new provider
artifact ID or authenticate the original execution anew.

Keep the original filename and bytes. Do not rebuild, repack or rename another
archive into this identity. Preserve the ZIP without extracting it for storage.
Neither this directory nor either JSON record contains the runtime payload.

## 3. Retained records

- [RECOVERY_CHECK.json](RECOVERY_CHECK.json) is the unchanged recovery report.
  It records the original size and digest, 78 ZIP members, the verification of
  76 inventory entries and the two original reports, without executing archive
  code. Its recorded timestamp and claims are not rewritten by this decision.
- [PREPARATION_SCOPE_RESULT.json](PREPARATION_SCOPE_RESULT.json) is the unchanged
  earlier, single-object component and publication-scope assessment. Its
  `planned_destination.storage=git_lfs` and `publication_requirements` fields
  describe the earlier proposal, not the owner's current storage selection.
  It is retained as evidence of that assessment, not consumed as configuration.

Exact hashes of the retained report files:

| File | SHA-256 |
| --- | --- |
| `RECOVERY_CHECK.json` | `355b19b84fd3b19726515648be014a1cbdee02f2484df1f8b0ef64c46b469fd7` |
| `PREPARATION_SCOPE_RESULT.json` | `08bb9a6af69663681abfdc383c7d3e10374b3a5949b065e70cd1102567cce787` |

During preparation of this documentation delivery, the original outer size and
SHA-256, all 78 ZIP member CRCs, all 76 recorded member size/digest bindings and
the two original report hashes were checked again against the recovered copy.
No archive member was extracted to disk or executed for that check. This is not
a repetition of the earlier nested-wheel component review or a native Q3 run.

## 4. Owner-machine receipt and storage

Save the original ZIP to an ordinary local folder outside any repository
checkout. Select a folder that is not configured for cloud synchronization.
An example folder name is `PULSE_Q3_RUNTIME`; no drive letter, username, private
absolute path or successful transfer is asserted here.

After the download has completed, verify the saved copy's byte count and
SHA-256. On Windows, open PowerShell in the folder containing the ZIP and use:

```powershell
$p = Join-Path (Get-Location) 'q2-runtime-preparation-37148637546-1.zip'
$f = Get-Item -LiteralPath $p -ErrorAction Stop
if ($f.PSIsContainer -or $f.Length -ne 508460811) {
    throw 'Q3 runtime archive size mismatch.'
}
$h = (Get-FileHash -LiteralPath $p -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
if ($h -ne 'b3a2b4db54816dd6f40171c221947d942ca63f3e9883f76de8455ad66037f4b9') {
    throw 'Q3 runtime archive SHA-256 mismatch.'
}
'LOCAL COPY MATCHES THE SELECTED ORIGINAL BYTES'
```

This read-only check does not install dependencies, extract or execute the
archive, publish data or grant execution permission. The PowerShell snippet was
not executed on the owner's machine during preparation. Owner-local receipt
remains unverified until the saved copy is checked there. A separately verified
copy on another owner-controlled local medium may be retained for backup; no
backup copy is claimed to exist already.

## 5. Preservation is not hosted retrieval

A local archive plus public documentation is an owner-held preservation
arrangement. It is not repository payload custody, a public download endpoint
or automatic access for the existing GitHub-hosted Q3 workflow.

The carried-forward acquisition blocker is unchanged: the original Actions
artifact endpoint was unavailable in the preceding inspection, and the native
acquisition path still selects that original provider artifact. This docs-only
change does not implement an alternative delivery path and does not claim a new
successful provider download.

Local storage does not imply a decision to run the model on the owner's
computer. A future execution path requires a separately specified, reviewed and
owner-authorized way to supply the exact bytes to its actual runner, within the
owner's no-LFS/no-paid-storage boundary. No such path is activated here, and no
ready-to-dispatch preflight or capture request is included.

## 6. Unchanged evidence and review boundaries

The earlier public-payload review is retained, not declared complete or legally
cleared. The rejected LFS publication path and its account-budget check are no
longer prerequisites for this selected storage/documentation task. That scope
change does not settle previously open notice or source questions for any
future distribution.

The historical runner-image contradictions and capture restrictions remain
unchanged. Hash equality proves byte agreement with the selected identity; it
is not execution evidence, source authentication or release authority.

Current decision and completion distinctions:

| Item | Status in this delivery |
| --- | --- |
| Storage choice | Owner-local archive; documentation in `docs` |
| Git LFS / paid remote storage | Not authorized for the selected object |
| Original bytes available for owner download | Prepared and rechecked |
| Saved owner-machine copy verified | Not yet observed |
| Documentation package | Prepared; not pushed or merged by this delivery |
| Runtime payload included in repository package | No |
| Hosted runtime transport restored | No |
| Tokenizer/model execution or workflow dispatch | None performed or authorized |
| Capture handoff / Q3 measurement complete | No |
| Release-authority effect | `none` |

Keep #2879 open.

## 7. Repository delivery inventory

Add only the following three files:

```text
docs/compute/q3_runtime_local_custody_v0/README.md
docs/compute/q3_runtime_local_custody_v0/RECOVERY_CHECK.json
docs/compute/q3_runtime_local_custody_v0/PREPARATION_SCOPE_RESULT.json
```

No existing file is overwritten. No executable or CI registration is added.
The records bind the documented original object, not a fictional owner-local
path. Stop rather than overwrite any unexpected existing file at these paths.
The owner opens the pull request and controls the merge.
