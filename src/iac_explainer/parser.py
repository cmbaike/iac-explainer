import hcl2
from pathlib import Path


class ParseError(Exception):
    pass


def _normalise(value: object) -> object:
    """Strip the extra layer of quotes python-hcl2 adds to string scalars.

    hcl2 wraps string literals as '"the value"' (a Python str containing
    surrounding double-quote characters).  Interpolations like
    "${resource.name.attr}" are left as-is — they're useful context for the LLM.
    Booleans, ints, floats, and None are returned unchanged.
    The special "__is_block__" metadata key is dropped from dicts.
    """
    if isinstance(value, str):
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            # Only strip if the outer quotes are not part of an interpolation
            inner = value[1:-1]
            if not inner.startswith("${"):
                return inner
        return value
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items() if k != "__is_block__"}
    if isinstance(value, list):
        return [_normalise(item) for item in value]
    return value


def parse(path: str | Path) -> tuple[str, list[dict]]:
    """Return (raw_hcl, parsed_resources) from a .tf file.

    parsed_resources is a flat list of {"type": str, "name": str, "config": dict}.
    The raw text is passed to the LLM alongside the structured list so it can
    see inline comments and variable references that the AST drops.
    """
    p = Path(path)
    if not p.exists():
        raise ParseError(f"File not found: {path}")
    if p.suffix != ".tf":
        raise ParseError(f"Expected a .tf file, got: {p.suffix}")

    raw_hcl = p.read_text(encoding="utf-8")
    if not raw_hcl.strip():
        raise ParseError(f"File is empty: {path}")

    try:
        parsed = hcl2.loads(raw_hcl)
    except Exception as exc:
        raise ParseError(f"HCL parse error in {path}: {exc}") from exc

    # python-hcl2 returns `resource` as a list of single-key dicts.
    # Keys are quoted strings (e.g. '"aws_s3_bucket"'); strip the extra quotes.
    resources = []
    for block in parsed.get("resource", []):
        for raw_type, name_map in block.items():
            resource_type = raw_type.strip('"')
            for raw_name, config in name_map.items():
                resource_name = raw_name.strip('"')
                resources.append(
                    {
                        "type": resource_type,
                        "name": resource_name,
                        "config": _normalise(config),
                    }
                )

    return raw_hcl, resources
