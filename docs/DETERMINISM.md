# Determinizmus & flakiness (lokál‑first, offline)

**Kiindulás:** nincs külső futtató, nincs konténer, nincs felhős detektor.  
A PULSE determinisztikusan **értékel**, ha a lokális/CI környezet rögzített; a „fail‑closed” elv szerint **bármely bizonytalanság → FAIL**.

## Lokális reprodukálhatóság (runner nélkül)
- **Python környezet**: használj `venv`‑et és rögzített csomagverziókat.
~~~bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install pyyaml jsonschema
pip freeze > requirements.lock.txt
~~~
- **Seed**: egyetlen egységes `seed` mindenhol (logold a `status.json`‑ban).
- **CPU‑first**: GPU nem szükséges; ha mégis GPU, kapcsold be a determinisztikát (lásd lejjebb).
- **Külső hálózat tiltása**: ne hívj külső API‑kat/modellvégpontokat. A detektorok legyenek **offline/heurisztikusak** (regex, szabály, statikus modell).  
  **Policy:** ha egy detektor hálózati erőforrást igényel → **FAIL‑closed**.

## RNG & környezet – ajánlott beállítások
Állítsd be az alábbiakat, hogy a futások megismételhetők legyenek (reproducibility).

**Shell (Linux/macOS)**
~~~bash
export PYTHONHASHSEED=0
~~~

**Windows (PowerShell)**
~~~powershell
$env:PYTHONHASHSEED = "0"
~~~

**Python / NumPy / (opcionális) PyTorch**
~~~python
import random, numpy as np
random.seed(12345)
np.random.seed(12345)

try:
    import torch
    torch.manual_seed(12345)
    torch.use_deterministic_algorithms(True)
    if torch.backends.cudnn:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
except Exception:
    # PyTorch nem kötelező; CPU-only környezetben elhagyható
    pass
~~~

**Megjegyzés:** GPU hiányában a fenti seedelés elegendő; CPU‑n determinisztikus a futás.

## Timeout / Retry / Cache
- **Per‑rule timeout**, legfeljebb **1 retry**; ha kimerül → **FAIL‑closed**.
- Detektoroknál **cache TTL**; minden bemenet/kimenet legyen **hash‑elve** (diagnosztika).
- Hálózati erőforrás/hiba (ha mégis előfordulna) → **FAIL** (nincs „soft pass”).

## EPF (shadow‑only) és RDSI — lokálisan is futtatható
Az **EPF** kis amplitúdójú, **auditálható** perturbációt vizsgál **csak** a \[threshold − ε, threshold] sávban, **külön** lépésként.  
**Soha** nem írja felül a baseline CI döntést; célja kizárólag diagnosztika.

**RDSI** (stabilitási mutató): `RDSI = 1 − p(change)`; 95% Wilson CI‑vel publikáljuk:
- **RDSI ≥ 0.95** → stabil  
- **0.85–0.95** → figyelendő  
- **< 0.85** → billeg (küszöb/kalibráció szükséges)

## Offline detektorok (példák)
- **PII/format invariáns**: reguláris kifejezések (e‑mail, tel., IBAN, JSON‑parse).  
- **Toxicitás/helytelen nyelv**: tiltólista + szabályok (determinista).  
- **Groundedness (egyszerű)**: hivatkozások/idézetek száma, kulcsszó‑fedezet.  
- **Fairness (lightweight)**: csoportcímkés mintahalmaz + min‑over‑groups arányok.

## Flakiness runbook (lokál)
1. **Ismételhetőség**: futtasd 3× ugyanazzal a seed‑del → azonos döntés?  
2. **Környezet**: egyező Python és csomagverziók (`requirements.lock.txt`)?  
3. **Detektor**: biztosan offline? (nincs hálózati hívás)  
4. **Küszöb közelében**? → nézd az EPF/Audit naplót; kell‑e margin/újrakalibráció.  
5. **Cache** ürítés, újrafuttatás: kizárja a „stale” állapotot.

## Összefoglaló táblázat (lokál‑first)

| Terület | Kötelező | Ajánlott |
|---|---|---|
| Python környezet | ✅ `venv` + verziózár | `requirements.lock.txt` commit |
| Seed | ✅ rögzített | – |
| CPU/GPU | ✅ CPU | GPU: determinisztika flag |
| Detektor | ✅ offline/proxy | hálózat → FAIL‑closed |
| Timeout/Retry | ✅ per‑rule | max 1 retry |
| EPF | ✅ shadow‑only | RDSI jelentés (lokálban is) |
