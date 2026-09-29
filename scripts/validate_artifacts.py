import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import jsonschema

BASE = Path("schemas/artifacts")
PAIRS = [
    ("projects/nha-su-va-bat-rong/artifacts/proposal_packet.json", "proposal_packet.schema.json"),
    ("projects/nha-su-va-bat-rong/artifacts/decision_log.json", "decision_log.schema.json"),
]

ok = True
for artifact, schema_name in PAIRS:
    data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    schema = json.loads((BASE / schema_name).read_text(encoding="utf-8"))
    errors = sorted(
        jsonschema.Draft202012Validator(schema).iter_errors(data),
        key=lambda e: list(e.path),
    )
    if not errors:
        print(f"VALID   {artifact}")
    else:
        ok = False
        print(f"INVALID {artifact}  ({len(errors)} errors)")
        for err in errors[:20]:
            print("   path:", "/".join(str(p) for p in err.path), "->", err.message[:260])

print("\nALL VALID" if ok else "\nFIX NEEDED")
