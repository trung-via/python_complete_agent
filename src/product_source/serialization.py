from __future__ import annotations
import json
import os
from typing import Any
from .models import ProductSourcePack

def serialize_source_pack(pack: ProductSourcePack, output_dir: str) -> str:
    os.makedirs(os.path.join(output_dir, 'original'), exist_ok=True)
    out_path = os.path.join(output_dir, 'source_pack.json')
    data = {
        "schema_version": "1.0",
        **pack.to_dict()
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=2, ensure_ascii=False)
    return out_path

def deserialize_source_pack(path: str) -> dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
