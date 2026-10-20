# Assets & Media License

Code in this repository is licensed under **Apache-2.0** (see `LICENSE`).

Unless noted otherwise below, documentation and visual/media assets are:
- Copyright (c) 2025 EPLabsAI
- Licensed under **Creative Commons Attribution 4.0 International (CC BY 4.0)**

CI-generated badges under `/badges/*.svg` are released as **CC0** to enable frictionless embedding.

> Trademarks: nothing in Apache-2.0 or CC licenses grants trademark rights.  
> See `TRADEMARKS.md`.

## Inventory

| Path                          | Owner    | License  | Notes                               |
|------------------------------ |----------|----------|-------------------------------------|
| `README.md`, `docs/`         | EPLabsAI | CC BY 4.0| documentation & examples            |
| `PULSE_one_pager.pdf/.png`   | EPLabsAI | CC BY 4.0| executive one‑pager                 |
| `pulse_landing_snippet.html` | EPLabsAI | CC BY 4.0| landing/website excerpt             |
| `hero_dark_4k.png`           | EPLabsAI | CC BY 4.0| dark hero                           |
| `hero_light_4k.png`          | EPLabsAI | CC BY 4.0| light hero                          |
| `badges/*.svg`               | Generated| CC0      | status/RDSI/ledger badges (generated)|

### Third‑party assets (if any)
If you add any third‑party asset, list its exact **source URL** and **original license** here.
If an asset is proprietary or non‑redistributable, do **not** check it into the public repository.


## Q2 metadata-only stage — publication boundary

The Q2 entries below are a **review inventory for a planned payload set**.
This ten-file stage adds the project records, component review and supplemental
license texts only. No model weights, native binary, Python archive, generated
response, token array, LFS pointer or LFS attribute is included. Archive paths
are future destinations, not a claim that those assets are already present.
The earlier inventory and later static continuation retain their dated scopes;
bootstrap unavailability statements in the earlier subsection are superseded
only by the explicitly recorded later access/inspection event.

The [stage contract](preservation/q2_reference_closure_v0/PRESERVATION_CONTRACT_v0.md) and
[component review](preservation/q2_reference_closure_v0/redistribution_review_v0.json)
define the exact boundary. P2 and the full-payload publication requirements
remain open. Metadata review does not grant permanent public-payload rights.

### Q2 preservation candidate: third-party source and license inventory

Status: **prepared_not_published; subject to owner review**. This appendix applies only to the five exact original objects in `preservation/q2_reference_closure_v0/repository_preservation_manifest_v0.json`. It does not grant public-payload authorization or replace any original grant. P2 remains **REVIEW_COMPLETED_WITH_OPEN_REQUIREMENTS**; publication is blocked by unresolved component/source coverage.

The [component review](preservation/q2_reference_closure_v0/redistribution_review_v0.json) records exact archive/wheel/member hashes, license sources, obligations, material offsets and gaps. The [supplemental notices](preservation/q2_reference_closure_v0/THIRD_PARTY_NOTICES_v0.txt) retain original legal text outside the unchanged archives. Source URLs below identify the exact distributed wheel, pinned upstream legal source or qualified source catalog; a wheel URL is not a corresponding-source offer. Unknown revisions and binary inclusion remain unknown.

| Exact component / frozen scope | Exact source URL(s) | Original license / scope |
|---|---|---|
| attrs 26.1.0 | <https://files.pythonhosted.org/packages/64/b4/17d4b0b2a2dc85a6df63d1157e028ed19f90d4cd97c36717afef2bc2f395/attrs-26.1.0-py3-none-any.whl> | MIT |
| certifi 2026.7.22 | <https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/certifi-2026.7.22-py3-none-any.whl> | MPL-2.0 |
| charset-normalizer 3.5.2 | <https://files.pythonhosted.org/packages/e4/ed/cf505d3011ffceb12c2067a7a5d3cfe92b875d4d44bb0ff0d69375e2c184/charset_normalizer-3.5.2-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl> | MIT |
| filelock 4.0.9 | <https://files.pythonhosted.org/packages/01/4f/83454fafd628e1e7e1726d74e44fb2332be5969d04c6182ca1fecb6c580e/filelock-4.0.9-py3-none-any.whl> | MIT |
| fsspec 2026.9.0 | <https://files.pythonhosted.org/packages/6c/c0/a98505f18594f1bce828bb159cec0fcf9860562f1a2c85913409fc8f3d9e/fsspec-2026.9.0-py3-none-any.whl> | BSD-3-Clause |
| hf-xet 1.6.0 | <https://files.pythonhosted.org/packages/67/4e/a28359bf1c1ecf11eba22123168c138698f7cb576ac678f5a2e16cd5da08/hf_xet-1.6.0-cp38-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl> | Apache-2.0 |
| huggingface_hub 0.36.2 | <https://files.pythonhosted.org/packages/a8/af/48ac8483240de756d2438c380746e7130d1c6f75802ef22f3c6d49982787/huggingface_hub-0.36.2-py3-none-any.whl> | Apache-2.0 |
| idna 3.20 | <https://files.pythonhosted.org/packages/58/a2/bb081bab032533a855d44de1d56f8e8426114ff1ba5d1f07a438a0a654f8/idna-3.20-py3-none-any.whl> | BSD-3-Clause |
| Jinja2 3.1.6 | <https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl> | BSD-3-Clause |
| jsonschema 4.25.1 | <https://files.pythonhosted.org/packages/bf/9c/8c95d856233c1f82500c2450b8c68576b4cf1c871db3afac5c34ff84e6fd/jsonschema-4.25.1-py3-none-any.whl> | MIT |
| jsonschema-specifications 2025.9.1 | <https://files.pythonhosted.org/packages/41/45/1a4ed80516f02155c51f51e8cedb3c1902296743db0bbc66608a0db2814f/jsonschema_specifications-2025.9.1-py3-none-any.whl> | MIT |
| MarkupSafe 3.0.4 | <https://files.pythonhosted.org/packages/81/a5/a513b76c139a3915b43404324e55c0b7979ae4f0d39eb6f075b0282e90a8/markupsafe-3.0.4-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| mpmath 1.3.0 | <https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl> | BSD-3-Clause |
| networkx 3.6.1 | <https://files.pythonhosted.org/packages/9e/c9/b2622292ea83fbb4ec318f5b9ab867d0a28ab43c5717bb85b0a5f6b3b0a4/networkx-3.6.1-py3-none-any.whl> | BSD-3-Clause |
| numpy 2.4.6 | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; additional native-library terms separately recorded |
| packaging 26.3 | <https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl> | Apache-2.0 OR BSD-2-Clause |
| PyYAML 6.0.3 | <https://files.pythonhosted.org/packages/71/60/917329f640924b18ff085ab889a11c763e0b573da888e8404ff486657602/pyyaml-6.0.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl> | MIT |
| referencing 0.37.0 | <https://files.pythonhosted.org/packages/2c/58/ca301544e1fa93ed4f80d724bf5b194f6e4b945841c5bfd555878eea9fcb/referencing-0.37.0-py3-none-any.whl> | MIT |
| regex 2026.9.29 | <https://files.pythonhosted.org/packages/8a/70/aa08d1d2b294894b365e5f8ba5380fe3f8546acdb81f10639dfd74209c37/regex-2026.9.29-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl> | Apache-2.0 AND CNRI-Python |
| requests 2.34.2 | <https://files.pythonhosted.org/packages/a0/f4/c67b0b3f1b9245e8d266f0f112c500d50e5b4e83cb6f3b71b6528104182a/requests-2.34.2-py3-none-any.whl> | Apache-2.0 |
| rfc8785 0.1.4 | <https://files.pythonhosted.org/packages/4d/78/119878110660b2ad709888c8a1614fce7e2fab39080ab960656dc8605bf6/rfc8785-0.1.4-py3-none-any.whl> | Apache-2.0 |
| rpds-py 2026.6.3 | <https://files.pythonhosted.org/packages/5e/19/7e98f468bd50346faff5b10e5297374b443bfdddacc8e9fbc65984539597/rpds_py-2026.6.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl> | MIT |
| safetensors 0.8.0 | <https://files.pythonhosted.org/packages/28/50/f203ff3a3ddfe19308efc83c5a3a29ed02bf786732ec35e68bf9162f3365/safetensors-0.8.0-cp310-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl> | Apache-2.0 |
| sympy 1.14.0 | <https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl> | BSD-3-Clause; bundled MIT/BSD material separately recorded |
| tokenizers 0.22.2 | <https://files.pythonhosted.org/packages/2e/76/932be4b50ef6ccedf9d3c6639b056a967a86258c6d9200643f01269211ca/tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl> | Apache-2.0 |
| torch 2.8.0+cpu | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause; composite third-party LICENSE/NOTICE separately recorded |
| tqdm 4.70.1 | <https://files.pythonhosted.org/packages/a7/03/921a3d3c75785aca9ebfbfcabfbc3a1be12e2ab5265deb026d55a5a3f83e/tqdm-4.70.1-py3-none-any.whl> | MPL-2.0 AND MIT |
| transformers 4.57.6 | <https://files.pythonhosted.org/packages/03/b8/e484ef633af3887baeeb4b6ad12743363af7cce68ae51e938e00aaa0529d/transformers-4.57.6-py3-none-any.whl> | Apache-2.0 |
| typing_extensions 4.16.0 | <https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl> | PSF-2.0 |
| urllib3 2.8.0 | <https://files.pythonhosted.org/packages/92/9d/c4e665119135114480843e7ab388fa94d8480650450e6f8e26b70d323a4c/urllib3-2.8.0-py3-none-any.whl> | MIT |
| pip 24.0 | <https://github.com/pypa/pip/tree/ef78c129b1a966dbbbdb8ebfffc43723e89110d1> | MIT |
| HuggingFaceTB/SmolLM2-135M-Instruct | <https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/12fd25f77366fa6b3b4b768ec3050bf629380bac> | Apache-2.0 (pinned card and original upstream model record) |
| CacheControl 0.13.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/cachecontrol/LICENSE.txt> | Apache-2.0 |
| colorama 0.4.6 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/colorama/LICENSE.txt> | BSD-3-Clause |
| distlib 0.3.8 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/distlib/LICENSE.txt> | PSF/Python historical license chain |
| distro 1.8.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/distro/LICENSE> | Apache-2.0 |
| msgpack 1.0.5 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/msgpack/COPYING> | Apache-2.0 |
| packaging 21.3 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/packaging/LICENSE><br><https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/packaging/LICENSE.APACHE><br><https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/packaging/LICENSE.BSD> | Apache-2.0 OR BSD-2-Clause |
| platformdirs 3.8.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/platformdirs/LICENSE> | MIT |
| pyparsing 3.1.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/pyparsing/LICENSE> | MIT |
| pyproject-hooks 1.0.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/pyproject_hooks/LICENSE> | MIT |
| requests 2.31.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/requests/LICENSE> | Apache-2.0 |
| certifi 2023.7.22 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/certifi/LICENSE> | MPL-2.0 |
| chardet 5.1.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/chardet/LICENSE> | LGPL-2.1-or-later |
| idna 3.4 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/idna/LICENSE.md> | BSD-3-Clause |
| urllib3 1.26.17 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/urllib3/LICENSE.txt> | MIT |
| rich 13.4.2 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/rich/LICENSE> | MIT |
| pygments 2.15.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/pygments/LICENSE> | BSD-2-Clause |
| typing_extensions 4.7.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/typing_extensions.LICENSE> | PSF/Python historical license chain |
| resolvelib 1.0.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/resolvelib/LICENSE> | ISC |
| setuptools 68.0.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/pkg_resources/LICENSE> | MIT |
| six 1.16.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/six.LICENSE> | MIT |
| tenacity 8.2.2 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/tenacity/LICENSE> | Apache-2.0 |
| tomli 2.0.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/tomli/LICENSE> | MIT |
| truststore 0.8.0 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/truststore/LICENSE> | MIT |
| webencodings 0.5.1 | <https://raw.githubusercontent.com/pypa/pip/ef78c129b1a966dbbbdb8ebfffc43723e89110d1/src/pip/_vendor/webencodings/LICENSE> | BSD-3-Clause |
| DCGM [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| FP16 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| FXdiv [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| NNPACK [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| NVTX [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 with exception |
| VulkanMemoryAllocator [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| XNNPACK [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| benchmark [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| boost-vcpkg-helpers [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| cJSON [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| catch2 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSL-1.0 |
| clog [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| colorama [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| composable_kernel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| cpp-httplib [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| cpplint [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| cpr [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| cpuinfo [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| cudnn_frontend [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| cutlass [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| dart [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| docs [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 with exception |
| doctest [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| duktape-1.5.2 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| duktape-1.8.0 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| dynolog [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| etw [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| expected [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| fbgemm [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| ffnvcodec [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT with exception |
| flash-attention [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| flatbuffers [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| fmt [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT with exception |
| gemmlowp [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| generator [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| gettimeofday [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| gloo [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| googlemock [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| googletest [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| gtest [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| hipify_torch [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| hungarian [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Permissive (free to use) |
| ideep [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| irrlicht [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| kineto [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| libnop [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| libstemmer [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| libuv [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| mimalloc [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| miniz-3.0.2 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| mkl-dnn [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| ms-gsl [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| mx [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| onnx [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| opentelemetry-cpp [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| opentelemetry-proto [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| opentracing-cpp [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| pdcurses [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Public Domain for core |
| pfs [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| physac [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| pqp [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| prometheus-cpp [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| protobuf [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| psimd [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| pthreadpool [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| pybind11 [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| python [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 with exception |
| python [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| python [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| python [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| python-peachpy [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| sigslot [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Public Domain |
| sleef [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSL-1.0 |
| swift [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| tb_plugin [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| tensorflow-common [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| tensorpipe [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| test [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT with exception |
| variant [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| vcpkg [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | MIT |
| vulkan [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 with exception |
| OpenBLAS [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| LAPACK [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause-Open-MPI |
| GCC runtime library [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | GPL-3.0-or-later WITH GCC-exception-3.1 |
| libquadmath [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | LGPL-2.1-or-later |
| numpy/_core/include/numpy/random/LICENSE.txt frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | MIT |
| numpy/ma/LICENSE frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| numpy/random/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | Composite BSD-3-Clause/MIT/CC0-1.0; retain exact text |
| numpy-2.4.6.dist-info/licenses/numpy/_core/src/common/pythoncapi-compat/COPYING frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | 0BSD |
| numpy-2.4.6.dist-info/licenses/numpy/_core/src/highway/LICENSE frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | (Apache-2.0 OR BSD-3-Clause) AND CC0-1.0 for random-inl.h |
| numpy-2.4.6.dist-info/licenses/numpy/_core/src/npysort/x86-simd-sort/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| numpy-2.4.6.dist-info/licenses/numpy/_core/src/umath/svml/LICENSE frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause (as supplied by NumPy) |
| numpy-2.4.6.dist-info/licenses/numpy/fft/pocketfft/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| numpy-2.4.6.dist-info/licenses/numpy/linalg/lapack_lite/LICENSE.txt frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause-Open-MPI |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/distributions/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | Composite BSD-3-Clause/MIT; retain complete exact text |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/mt19937/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/pcg64/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | MIT |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/philox/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/sfc64/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | MIT |
| numpy-2.4.6.dist-info/licenses/numpy/random/src/splitmix64/LICENSE.md frozen within numpy==2.4.6 selected wheel [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/02/03/74fe2a4cb3817d94d86402f2506554130a2f01414e299b5a843e5a8a957f/numpy-2.4.6-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl> | CC0-1.0 |
| Diofant exact frozen subset in sympy==1.14.0; independent upstream revision not recorded [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl> | BSD-3-Clause |
| multipledispatch exact frozen subset in sympy==1.14.0; independent upstream revision not recorded [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl> | BSD-3-Clause |
| PyDy examples exact frozen subset in sympy==1.14.0; independent upstream revision not recorded [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl> | BSD-3-Clause |
| latex2sympy exact frozen subset in sympy==1.14.0; independent upstream revision not recorded [parent-frozen legal scope; independent revision/inclusion qualified] | <https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl> | MIT |
| Earlier BSD License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| Caffe's BSD License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-2-Clause |
| Caffe2's Apache License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | Apache-2.0 |
| Cephes's 3-Clause BSD License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| SciPy's 3-Clause BSD License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSD-3-Clause |
| Boost's 1.0 Software License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | BSL-1.0 |
| PILLOW-SIMD Software License frozen attribution scope in torch==2.8.0+cpu NOTICE [parent-frozen legal scope; independent revision/inclusion qualified] | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | LicenseRef-PILLOW-SIMD-as-shipped; see complete original grant |
| libgomp.so.1 | <https://download-r2.pytorch.org/whl/cpu/torch-2.8.0%2Bcpu-cp311-cp311-manylinux_2_28_x86_64.whl> | UNKNOWN exact GNU/other runtime origin; GNU basename is insufficient |
| LibYAML-related _yaml extension | <https://files.pythonhosted.org/packages/71/60/917329f640924b18ff085ab889a11c763e0b573da888e8404ff486657602/pyyaml-6.0.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl> | MIT parent PyYAML; exact embedded LibYAML license/build scope UNKNOWN |
| CPython 3.11.16 | <https://raw.githubusercontent.com/python/cpython/41388c9cb160d0886d5ca00d2e6c8782608a4549/LICENSE><br><https://github.com/actions/python-versions/releases/download/3.11.16-31661435402/python-3.11.16-linux-24.04-x64.tar.gz> | PSF-2.0 and historical Python license chain; external library grants separately applicable |
| autocommand 2.2.2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/autocommand-2.2.2.dist-info/LICENSE> | LGPL-3.0 |
| backports.tarfile 1.2.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/backports.tarfile-1.2.0.dist-info/LICENSE> | MIT |
| importlib_metadata 8.0.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/importlib_metadata-8.0.0.dist-info/LICENSE> | Apache-2.0 |
| inflect 7.3.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/inflect-7.3.1.dist-info/LICENSE> | MIT |
| jaraco.collections 5.1.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/jaraco.collections-5.1.0.dist-info/LICENSE> | MIT |
| jaraco.context 5.3.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/jaraco.context-5.3.0.dist-info/LICENSE> | MIT |
| jaraco.functools 4.0.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/jaraco.functools-4.0.1.dist-info/LICENSE> | MIT |
| jaraco.text 3.12.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/jaraco.text-3.12.1.dist-info/LICENSE> | MIT |
| more_itertools 10.3.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/more_itertools-10.3.0.dist-info/LICENSE> | MIT |
| packaging 24.2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/packaging-24.2.dist-info/LICENSE><br><https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/packaging-24.2.dist-info/LICENSE.APACHE><br><https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/packaging-24.2.dist-info/LICENSE.BSD> | Apache-2.0 OR BSD-2-Clause |
| platformdirs 4.2.2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/platformdirs-4.2.2.dist-info/licenses/LICENSE> | MIT |
| tomli 2.0.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/tomli-2.0.1.dist-info/LICENSE> | MIT |
| typeguard 4.3.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/typeguard-4.3.0.dist-info/LICENSE> | MIT |
| typing_extensions 4.12.2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/typing_extensions-4.12.2.dist-info/LICENSE> | PSF/Python historical license chain |
| wheel 0.45.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/wheel-0.45.1.dist-info/LICENSE.txt> | MIT |
| zipp 3.19.2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/zipp-3.19.2.dist-info/LICENSE> | MIT |
| packaging vendored by wheel 24.0 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/wheel/vendored/packaging/LICENSE><br><https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/wheel/vendored/packaging/LICENSE.APACHE><br><https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/wheel/vendored/packaging/LICENSE.BSD><br><https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/setuptools/_vendor/wheel/vendored/vendor.txt> | Apache-2.0 OR BSD-2-Clause |
| setuptools 79.0.1 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/pypa/setuptools/607f6be776db97d83c9cc54e0eaa578567dcc44c/LICENSE> | MIT; vendor and config NOTICE scopes separately applicable |
| actions/python-versions packaging/installer 113fda1c80e6067111133a853b435dfdf0c65bf2 [prior/source catalog; current bootstrap uninspected] | <https://raw.githubusercontent.com/actions/python-versions/113fda1c80e6067111133a853b435dfdf0c65bf2/LICENSE> | MIT for builder source only |

The primary model/tokenizer is `HuggingFaceTB/SmolLM2-135M-Instruct@12fd25f77366fa6b3b4b768ec3050bf629380bac`. Eight core-bundle dependency wheel copies are explicitly bound in the component review, as well as all 30 preparation wheels, the installed pip 24.0 distribution, 24 pip-vendored projects and 47 native objects. The source-wide Torch/NumPy catalogs are not proof that every named project is linked into this CPU wheel.

Known open requirements: unavailable selected bootstrap prevents a complete dependency/notice inventory; exact GNU runtime build/source and conveyance coverage are unresolved; opaque Rust/static dependencies need exact inclusion/notice evidence; owner must review original project/script/record rights and eventual source/notice delivery. The root license and a LICENSE filename do not establish clearance. No archive is repacked to add notices. P1, P3, P4 and P5 are unchanged.


## Q2 direct static-review continuation — 2026-10-20

This supplements the earlier proposed Q2 inventory; the earlier unavailability
record remains historical, not the current bootstrap access observation.
The exact bootstrap has now been inspected as data, with no installation or
archive-code execution: 10,545 TAR entries, 9,970 regular files, nine internal
symlinks, 81 ELF objects, 26 direct legal files, two ensurepip distribution wheels
and two standard-library wheel fixtures. Eighteen installed/vendor METADATA
records distinguish pip 24.0, setuptools 79.0.1 and sixteen setuptools vendors.
The fixtures are not treated as installed runtime dependencies.

All 26 direct bootstrap legal texts match previously retained pinned material.
The 366 retained pip vendor files in each of its installed and ensurepip copies
match the same pinned pip Git blobs. The previous 26 vendor notice texts apply
to these copies too. The two installer RECORD files differ between wheel and
installed layout; those differences are retained, not normalized away.

| Observed component/scope | Pinned-source notice supplied outside original archives | Limit |
| --- | --- | --- |
| Bootstrap Expat 2.8.3 identifier | CPython `41388c9cb160d0886d5ca00d2e6c8782608a4549`, `Modules/expat/COPYING` | Source macros, build flags and binary marker agree; no binary rebuild/source-equivalence claim. |
| Bootstrap libmpdec 2.5.1 identifier | Same CPython commit, full license header in `Modules/_decimal/libmpdec/constants.h` | Excerpt is labeled; not a hash of the whole header file. |
| PyYAML native LibYAML 0.2.5 marker | libyaml `2c891fc7a770e8ba2fec34fc6b545c672beb37e6`, `License` | Static source/version markers support this scope; wheel-specific build/patch attribution remains open. |

Nineteen distinct externally required SONAMEs are not present as named members
or SONAME-matched objects in the bootstrap. A dynamic dependency reference is
not an included-file inventory. Nor does absence of a separate library prove
absence of static code or settle combined-work licensing for wrappers.

The follow-up reads seven original preparation wheels and binds selected native
objects to their earlier capsule hashes. Four Rust objects contain 124 recorded
source-path markers (39 tokenizers, 72 hf-xet, seven safetensors, six rpds-py);
these are qualified build-path observations, not a complete dependency SBOM.
GNU runtime source/conveyance obligations and native transitive coverage remain
itemized and open. No arbitrary optional source dependency is declared shipped.

See the existing Q2 `redistribution_review_v0.json` and
`THIRD_PARTY_NOTICES_v0.txt` for exact paths, hashes and source references.
P2 remains incomplete. P1/P3/P4/P5, original archives, earlier reports and all
release/retention claims are unchanged. This inventory grants no publication
permission and does not substitute metadata for actual repository byte storage.
