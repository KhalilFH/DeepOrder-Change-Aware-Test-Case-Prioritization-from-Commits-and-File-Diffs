# C1 analysis reproduction

Commands (repository root):

```
python -m c1_harness.cli annotate --stage measured
python -m c1_harness.cli analyze --out analysis
```

Analysis version `c1-matched/1`; Python 3.14.3.

| Input or code | SHA-256 (inputs raw; code LF-normalized) |
|---|---|
| `annotations.jsonl` | `ca0030b5b8e397d38c49742a9becd3206e03fcaaa729a9e233b2a1de7a8124df` |
| `etcd5509__L.jsonl` | `a8fbab6330a0973b6a2216dec7e7f22ad3bbe3b0a263c110075e9b1879ce125d` |
| `etcd5509__R.jsonl` | `a24d480724f93245f1146e24760cd00beaaafc80783a9e430be405fb05663050` |
| `etcd7492__L.jsonl` | `ac0fc51b532f611a684c355e336d3a20427ce7e53d12689f513a57502acc3006` |
| `etcd7492__R.jsonl` | `76800a7206403d9898126534d0d096b3ade3df5a3ea99c12c9a6aa6dd64b9f8e` |
| `grpc1859__L.jsonl` | `07e03ad229b04ad6c0e0db0b136cad82ded84ce3614e17fd82e46aecabd2386a` |
| `grpc1859__R.jsonl` | `e95859c19dae08a778ab05c34d2baf69e4a7bd1a3dc9a2af77897b5e36f8d1f2` |
| `grpc2391__L.jsonl` | `69d224d482540da73a1f93fbddd1828f31be0f575d9198f19729f3572134f109` |
| `grpc2391__R.jsonl` | `5691cc87240e41dde42b533bb37346fb02f1447509603fbbd1693c99eaa756a3` |
| `istio17860__L.jsonl` | `0a8963c7bfb25f227db72650407db4209c72f7a07cc63bbf2efcb41d3450edfa` |
| `istio17860__R.jsonl` | `91555e7f8e416d97c561077cf29b7c9f0c286457851a60ef41fe9869addb1b54` |
| `k8s26980__L.jsonl` | `5c9e54a0b699a690cab52c58e06749ce9a999300852abc58995f0c29c163eb52` |
| `k8s26980__R.jsonl` | `3cf32d07cc9f0676c0cd03f31bddc91f4c999acdd5d24486eaecfc1ece1b8259` |
| `c1_harness/cards.py` | `6cb638501f774ab1736c88547521c73fb66a4b66beed42b88f49aca9b1241075` |
| `c1_harness/matched.py` | `9b4caefd91a9cba85775f9a0b8687b6b1a7f0c5e09897fcc6c2aed5ad21874d0` |
| `e1_harness/analysis.py` | `bc27c7de7ebce6bd42c56749c134b76945f13c615bf0f0533336f5528ee1a841` |
| `e1_harness/ledger.py` | `9e51b801dba5f034cc1818192d86314e41f93343a4efe6eaa3053cbf8f8a34f3` |
| `e1_harness/oracle.py` | `20a494f00b87d52a035b8a1d31b40d31ca46d9037854a5b0caafcf04b20a89a0` |
| `e1_harness/policy.py` | `b5a2e4ba6638a7a6ae565b0962b47c0af9bf07466bfa0473773b240918ff7da4` |

| Output | SHA-256 (LF-normalized) |
|---|---|
| `attempt_index.csv` | `4557e498ad761be4282ac8ecfb2177a500e781162e1151b46d351d585ade4f57` |
| `policy_decisions.csv` | `6f3c0b448506f0774e82a82bcfbd129539a401f9d4c990a62e84403815b4fb07` |
| `subject_contrasts.csv` | `e60989d47d51e9d581818421f494ea9f4b259152454286d60d49b83ab4ca56fa` |
| `summary.json` | `1d768e0028b94cac8a377de61fa32cb6788a971d5783e9a177089bb88e9f2bdb` |
| `report.md` | `63e8ca7db9d6806147527ea0b40c22d9d516c9b5dafa473434502b0cf1c6ab41` |
