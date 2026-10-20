# QRH003 knowledge continuity — M1 preservation

This companion preserves the **2026-10-20 M1 / KNOWLEDGE_LINK_INVENTORY**
for the selected `qrh003_zeta` claim. The five inventory outputs are prepared;
**M1 acceptance remains `INCOMPLETE`** because required source bytes are not
fully acquired. The next work item is `Q-SOURCE-1`.

The preserved historical family decision remains **`BLOCK`**, its archived
decision replay remains **`MATCH`**, and no production QRH certificate was
emitted. This companion has `authority_effect: none`.

## Preserved artifact

| Item | Value |
| --- | --- |
| Archive | [PULSEMECH_QRH003_M1_v0_1_INCOMPLETE.zip](PULSEMECH_QRH003_M1_v0_1_INCOMPLETE.zip) |
| Bytes | `1781765` |
| SHA-256 | `1d6a7ae6c060361190eba45471233d5f7e56504e24833fde185d9904304b53a5` |
| Machine-readable identity | [ARCHIVE_MANIFEST.json](ARCHIVE_MANIFEST.json) |
| Source notices | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| M1 acceptance | `INCOMPLETE` |
| Handoff ready | `false` |

The ZIP is the exact previously prepared M1 artifact. Its bytes, member names
and internal cross-file digests are retained. Repository preservation is a
subsequent packaging step; the M1 audit correctly records that the original
static inventory work performed no repository writes.

## Reading the inventory

Extract a copy of the ZIP into a separate working directory. Start with
`M1/M1_AUDIT_TRAIL.md`, the Hungarian audit narrative. The JSON field names and
most structured explanations are English; verbatim source excerpts and
historical records retain their original languages.

| ZIP member | Purpose |
| --- | --- |
| `M1/INPUTS_LOCK.json` | Pinned inputs, acquisition anchors, raw-byte identities, embedded additional source bytes and the exact selected-source coverage inventory. |
| `M1/CLAIM_CARD_QRH003_ZETA.json` | One claim, manuscript/formal anchors, the pole convention, exclusions and 21 source excerpts. |
| `M1/EVIDENCE_RELATIONS.json` | E1–E7, separate relation/review states, six status axes and preserved historical decision/replay bindings. |
| `M1/OPEN_QUESTIONS.json` | Eight open questions with required evidence and closure conditions; all owners remain `not_assigned`. |
| `M1/M1_AUDIT_TRAIL.md` | Static operations, byte comparisons, internal review scope and M1 acceptance findings. |

Paths beginning with `M1/` in these records refer to the extracted archive.
Historical local paths and owner-controlled object IDs are provenance labels;
they are not repository paths, credentials or public download locations.

## Claim and source boundary

The selected classical claim is zeta nonvanishing for `Re(s) > 7/8`, with
the classical pole at `s = 1` excluded. Its manuscript anchor is Theorem 1.1,
PDF page 4. The formal target is:

`OAI.riemannZeta_ne_zero_of_seven_eighths_lt_re`

The pinned formal source uses Mathlib's totalized `riemannZeta`, including its
specified value at `s = 1`. The claim card retains this distinction and the
supporting definition, series, pole-residue and totalization excerpts.
Independent semantic/domain review remains `NOT_REVIEWED`; source-signature
agreement does not establish elaborated-type, kernel or axiom verification.

| Source role | Pinned revision |
| --- | --- |
| OpenAI Math subject | `adc7f1241b42e322a6451854ab7e4b4c146bf78a` |
| Subject tree | `a8e3481a92772ee311cdc9dd6409cd7b927a3fc1` |
| Mathlib definition context | `d13f23b723b8a846827a245b89c10fc7d3f11612` |
| Current QRH003 source used by M1 | `c0895b920399cafbc14aa9fd3b6d3b68671f0220` |
| Merged M1 planning contract | `2ca84e3e0c9709758adc48eb959f1b5e0c965c19` |

The historical `qrh003-pilot-002-20261007` decision covers **four claims and
five exports**, including this selected zeta claim. It is preserved with that
scope. The M1 card does not create a historical zeta-only decision.

## Why M1 remains incomplete

The two selected roots of the preserved static import graph inventory
**13,688 modules / 150,238,780 source bytes**. Of these, **16 modules / 149,395
bytes** are acquired and match; **13,672 modules / 150,089,385 bytes** are
`NOT_ACQUIRED`. No actual byte conflict was found in the comparison.

`NOT_ACQUIRED` records current possession. It does not claim that retrieval
was attempted and denied. The historical graph is a restricted static
baseline with a partial provider universe, not a complete compiler/runtime
closure. Full module/provider/revision/path/size/hash records remain in the
input lock. Preserved patch bytes are not counted as acquired effective
post-patch source trees.

All seven E1–E7 relations are accounted for with evidence or explicit missing
references. This does not mean that all seven relations are verified.
`Q-SOURCE-1` names the exact next acquisition/reconciliation task. Native
proof capture remains `NOT_IMPLEMENTED`; native proof, fresh replay and
K01–K20 experiments remain `NOT_RUN`; independent handoff is `NOT_TESTED`.

## What is physically present

The M1 input lock embeds **51 additional source, plan and license payloads**
totalling **884,742 decoded bytes**, each with size and SHA-256. The 21 claim
excerpts are also present. The full historical source/evidence archive is a
separate owner-controlled input:

- Filename: `PULSEMECH_QRH003_IMPLEMENTATION_v0_1_1.zip`
- Bytes: `23453781`
- SHA-256: `ce5737b01ae3b400bac96c092afb982a0af74a812692714e4c7cd094b61afbdc`

That 23.45 MB archive, the complete upstream PDFs, unacquired dependency
source trees and a full proof/runtime environment are not included here.
Access to the original archive must be obtained separately and its exact
digest checked. Publishing this inventory does not make owner-controlled
source objects publicly retrievable or establish two independent durable
copies of all required bytes.

## Archive identity check

From this directory, Python's standard library can check the archive and
every member without executing any archived code:

```python
import hashlib
import json
import zipfile
from pathlib import Path

manifest = json.loads(Path("ARCHIVE_MANIFEST.json").read_text(encoding="utf-8"))
archive = Path(manifest["archive"]["path"])
raw = archive.read_bytes()
assert len(raw) == manifest["archive"]["size_bytes"]
assert hashlib.sha256(raw).hexdigest() == manifest["archive"]["sha256"]
with zipfile.ZipFile(archive) as bundle:
    records = manifest["archive"]["members"]
    assert len(bundle.namelist()) == len(records)
    assert set(bundle.namelist()) == {r["path"] for r in records}
    for record in records:
        data = bundle.read(record["path"])
        assert len(data) == record["size_bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
print("Archive and member bytes match; M1 acceptance remains INCOMPLETE.")
```

This check establishes byte identity only. It does not run the historical
verifier, replay, Lean, policy checker, tests or a signature verifier.

## Related material

- [Knowledge-continuity overview](../../docs/PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_OVERVIEW_v0.md)
- [Technical contract](../../docs/PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_TECHNICAL_PLAN_v0.md)
- [Implementation plan and M1 acceptance rules](../../docs/PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_IMPLEMENTATION_PLAN_v0.md)
- [Experiment plan: K01–K20](../../docs/PULSEMECH_QRH003_KNOWLEDGE_CONTINUITY_EXPERIMENT_PLAN_v0.md)
- [Existing QRH003 audit demonstrator](../openai_math_003_qrh_v0/README.md)
- [Documentation index](../../docs/INDEX.md)
