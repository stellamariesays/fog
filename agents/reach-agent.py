#!/usr/bin/env python3
"""
Reach Agent — task-executable wrapper around the numinous reach library.

Commands:
    reach-scan        → Full reach scan (implied regions, convergence)
    reach-pressure    → Pressure readings for strongest implied regions
    reach-regions     → Top N candidate regions by strength

Input: JSON args on argv[2] (optional)
Output: JSON on stdout
"""

import sys
import json
sys.path.insert(0, "/home/sophia/numinous")
sys.path.insert(0, "/home/sophia/fog")


def _load_atlas():
    """Try loading the mesh atlas from Manifold."""
    import urllib.request
    try:
        req = urllib.request.Request("http://localhost:8777/mesh")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _build_vocab_from_mesh(mesh_data: dict) -> set:
    """Extract capability vocabulary from mesh data."""
    vocab = set()
    if not mesh_data:
        return vocab
    agents = mesh_data if isinstance(mesh_data, list) else mesh_data.get("agents", [])
    for agent in agents:
        for cap in agent.get("capabilities", []):
            vocab.add(cap)
    return vocab


def reach_scan(args: dict) -> dict:
    from numinous.reach import _tokenize, _all_tokens, ReachRegion, ReachReading

    mesh_data = _load_atlas()
    vocab = _build_vocab_from_mesh(mesh_data)

    if not vocab:
        return {
            "status": "no_vocabulary",
            "readable": "No mesh vocabulary available. Run with live Manifold hub.",
            "regions": [],
        }

    # Token analysis
    token_counts = _all_tokens(vocab)

    # Find implied compounds — tokens that co-occur in different terms
    # but haven't been combined into a single term
    token_to_terms = {}
    for term in vocab:
        for tok in _tokenize(term):
            token_to_terms.setdefault(tok, set()).add(term)

    candidates = []
    seen_tokens = set()
    for tok1 in sorted(token_counts.keys()):
        for tok2 in sorted(token_counts.keys()):
            if tok1 >= tok2:
                continue
            combo = f"{tok1}-{tok2}"
            if combo in vocab or f"{tok2}-{tok1}" in vocab:
                continue
            implied_by = token_to_terms.get(tok1, set()) | token_to_terms.get(tok2, set())
            if len(implied_by) >= 2:
                strength = min(token_counts[tok1], token_counts[tok2]) / max(token_counts[tok1], token_counts[tok2])
                candidates.append({
                    "term": combo,
                    "strength": round(strength, 4),
                    "implied_by": sorted(implied_by)[:5],
                })

    candidates.sort(key=lambda c: c["strength"], reverse=True)
    top = candidates[:args.get("limit", 10)]

    return {
        "vocabulary_size": len(vocab),
        "token_count": len(token_counts),
        "candidate_regions": len(candidates),
        "top_regions": top,
        "readable": f"Reach scan: {len(vocab)} terms, {len(candidates)} implied regions. Top: {top[0]['term'] if top else 'none'}.",
    }


def reach_pressure(args: dict) -> dict:
    scan = reach_scan(args)
    top = scan.get("top_regions", [])
    return {
        "pressure_regions": top[:5],
        "readable": f"Reach pressure: {len(top)} regions. Strongest: {top[0]['term'] if top else 'none'}.",
    }


def reach_regions(args: dict) -> dict:
    scan = reach_scan(args)
    limit = args.get("limit", 5)
    return {
        "regions": scan.get("top_regions", [])[:limit],
        "readable": scan.get("readable", "No regions found."),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No command. Usage: reach-agent.py <command> [args_json]"}))
        sys.exit(1)

    command = sys.argv[1]
    args = {}
    if len(sys.argv) > 2:
        try:
            args = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            args = {}

    dispatch = {
        "reach-scan": reach_scan,
        "reach-pressure": reach_pressure,
        "reach-regions": reach_regions,
    }

    handler = dispatch.get(command)
    if not handler:
        print(json.dumps({"error": f"Unknown command: {command}", "available": list(dispatch.keys())}))
        sys.exit(1)

    result = handler(args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
