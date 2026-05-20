"""Run the v7 Ukraine ingestion canvas over a topic list.

For each topic:
  - Snapshot baseline (chunk count for that topic, seen-urls.jsonl rows)
  - Invoke canvas /completions with the topic; stream SSE; capture tool calls + node outputs
  - Snapshot post-run + delta
  - Aggregate per-outlet / per-language stats

The canvas itself does the per-topic discover/crawl/translate/ingest cycle and
the seen-urls dedupe. This driver just iterates topics and reports.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import time
import urllib.request

CANVAS_ID = "6f4f5c74467b4804bfd61c01ebcef818"
RAGFLOW = "https://ragflow1.cloud-dog.net"
RFK = "ragflow-lezX2hIWxC8E_2YjO6KPOsMBXmO3sC6_PHSBeJrPatw"

FILEMCP = "https://filemcpserver0.cloud-dog.net/mcp"
FILEMCP_TOKEN = "FileMCP-local-5678"

INDEX_RETRIEVER = "https://indexretriever0.cloud-dog.net/mcp"
IR_TOKEN = "cd_admin_99821a7ef9ebe7646e13797a2f22515640d2fdabbf1ff3b2"
PROFILE = "default"
COLLECTION = "ukraine-ingest"

DEFAULT_TOPICS = [
    "Russia Ukraine drone strikes energy infrastructure 2026 winter",
    "Ukraine counteroffensive Donetsk Pokrovsk May 2026",
    "Russia Ukraine peace negotiations diplomatic positions May 2026",
]


def _ctx():
    c = ssl.create_default_context(); c.check_hostname=False; c.verify_mode=ssl.CERT_NONE; return c


def mcp_call(url, tool, args, token=None, timeout=30):
    body = {"jsonrpc":"2.0","id":int(time.time()*1000)%100000,"method":"tools/call","params":{"name":tool,"arguments":args}}
    hdrs = {"Content-Type":"application/json","Accept":"application/json, text/event-stream"}
    if token: hdrs["Authorization"]=f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdrs, method="POST")
    with urllib.request.urlopen(req, context=_ctx(), timeout=timeout) as r:
        raw = r.read().decode()
    m = re.search(r"^data: (.+)$", raw, re.M)
    obj = json.loads(m.group(1)) if m else json.loads(raw)
    return (obj.get("result") or {}).get("structuredContent") or {}


def read_seen_urls():
    sc = mcp_call(FILEMCP, "read_file", {"path": "ukraine-corpus/seen-urls.jsonl"}, FILEMCP_TOKEN, 20)
    content = sc.get("value") or sc.get("content") or sc.get("text") or ""
    if not content:
        return []
    rows = []
    # Try JSONL first
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    # Fallback: maybe it was written as a single JSON array (v7c bug)
    if not rows:
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                rows = parsed
        except Exception:
            pass
    return rows


def search_chunks(query: str) -> list[dict]:
    sc = mcp_call(INDEX_RETRIEVER, "search",
        {"profile": PROFILE, "collection": COLLECTION, "query": query, "top_k": 50},
        IR_TOKEN, 30)
    return sc.get("hits") or sc.get("results") or []


def run_canvas(topic) -> dict:
    """POST to /completions; stream SSE; capture node outputs + final."""
    # Create session
    sess_req = urllib.request.Request(
        f"{RAGFLOW}/api/v1/agents/{CANVAS_ID}/sessions",
        data=b"{}",
        headers={"Authorization":f"Bearer {RFK}","Content-Type":"application/json"},
        method="POST",
    )
    with urllib.request.urlopen(sess_req, context=_ctx(), timeout=30) as r:
        sess_obj = json.loads(r.read().decode())
    session_id = sess_obj.get("data",{}).get("id")

    # Stream completion
    # v7c: pass topics via inputs.topics (Array<string>); question is just a kick.
    body = {
        "question": "run-cycle",
        "stream": True,
        "session_id": session_id,
        "inputs": {"topics": {"type": "Array<string>", "value": [topic] if isinstance(topic, str) else list(topic)}},
    }
    req = urllib.request.Request(
        f"{RAGFLOW}/api/v1/agents/{CANVAS_ID}/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization":f"Bearer {RFK}","Content-Type":"application/json","Accept":"text/event-stream"},
        method="POST",
    )
    events = []
    cycle_output = None
    final_output = None
    t0 = time.time()
    with urllib.request.urlopen(req, context=_ctx(), timeout=3600) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data:"): continue
            payload = line[5:].strip()
            if not payload: continue
            try:
                obj = json.loads(payload)
            except Exception:
                continue
            events.append(obj)
            ev = obj.get("event")
            data = obj.get("data") or {}
            cname = data.get("component_name") or data.get("component_id") or ""
            # Print EVERY event for debugging
            if ev in ("workflow_started","workflow_finished","node_started","node_finished","tool_invocation_started","tool_invocation_finished","error","message_finished"):
                summary = ""
                if ev == "node_finished":
                    outs = data.get("outputs") or {}
                    content = outs.get("content") or outs.get("text") or ""
                    summary = f"elapsed={data.get('elapsed_time')}s output[:200]={str(content)[:200]!r}"
                elif ev in ("tool_invocation_started","tool_invocation_finished"):
                    summary = f"tool={data.get('tool_name')} args={json.dumps(data.get('arguments') or {})[:200]}"
                elif ev == "error":
                    summary = json.dumps(data)[:400]
                elif ev == "node_started":
                    summary = f"component={cname}"
                print(f"  [{ev}] {cname}  {summary}")
                if ev == "node_finished":
                    outs = data.get("outputs") or {}
                    content = outs.get("content") or outs.get("text") or ""
                    if "CycleNode" in cname or cname == "Agent":
                        cycle_output = content
                    elif "FinalNode" in cname or cname == "Message":
                        final_output = content
    wall = time.time() - t0
    return {
        "session_id": session_id,
        "wall_clock_s": wall,
        "events": len(events),
        "cycle_output": cycle_output,
        "final_output": final_output,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", nargs="*", default=None, help="Topics to run; defaults to a built-in 3-topic list")
    ap.add_argument("--out", default="working/w28a-262/cycle-report.json")
    args = ap.parse_args()
    topics = args.topics or DEFAULT_TOPICS

    print(f"=== Ukraine v7 ingest cycle — {len(topics)} topic(s) ===\n")

    # Baseline
    seen_before = read_seen_urls()
    print(f"baseline seen-urls register rows: {len(seen_before)}")

    report = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "topics": [], "summary": {}}

    for i, topic in enumerate(topics):
        print(f"\n========== TOPIC [{i+1}/{len(topics)}]: {topic!r} ==========")
        chunks_before = search_chunks(topic)
        per_topic_seen_before = len(read_seen_urls())
        result = run_canvas(topic)
        print(f"\nWall-clock: {result['wall_clock_s']:.1f}s   events: {result['events']}")

        # Parse the cycle JSON summary if present
        manifest = None
        if result["cycle_output"]:
            txt = result["cycle_output"]
            js = txt.find("{"); je = txt.rfind("}")
            if js >= 0 and je > js:
                try:
                    manifest = json.loads(txt[js:je+1])
                except Exception as e:
                    print(f"  (manifest parse failed: {e})")

        # Post-run snapshot
        time.sleep(5)
        chunks_after = search_chunks(topic)
        per_topic_seen_after = len(read_seen_urls())
        delta_chunks = len(chunks_after) - len(chunks_before)
        delta_seen = per_topic_seen_after - per_topic_seen_before

        topic_report = {
            "topic": topic,
            "wall_clock_s": round(result["wall_clock_s"], 1),
            "chunks_matching_before": len(chunks_before),
            "chunks_matching_after": len(chunks_after),
            "delta_chunks": delta_chunks,
            "seen_urls_before": per_topic_seen_before,
            "seen_urls_after": per_topic_seen_after,
            "delta_seen_urls": delta_seen,
            "manifest": manifest,
        }
        print(f"\n  delta chunks (topic-matching): +{delta_chunks}")
        print(f"  delta seen-urls register: +{delta_seen}")
        if manifest:
            print(f"  manifest.new_ingested = {manifest.get('new_ingested')}")
            print(f"  manifest.per_outlet = {manifest.get('per_outlet')}")
            for u in (manifest.get("new_urls") or [])[:5]:
                print(f"    + {u}")
        report["topics"].append(topic_report)

    # Final aggregate snapshot
    seen_after_all = read_seen_urls()
    report["summary"] = {
        "seen_urls_before": len(seen_before),
        "seen_urls_after": len(seen_after_all),
        "new_urls_added": len(seen_after_all) - len(seen_before),
        "topics_run": len(topics),
    }

    # Per-outlet breakdown
    outlet_counts = {}
    lang_counts = {}
    for r in seen_after_all:
        o = r.get("outlet_id") or r.get("outlet") or "?"
        outlet_counts[o] = outlet_counts.get(o, 0) + 1
        l = r.get("lang") or "?"
        lang_counts[l] = lang_counts.get(l, 0) + 1
    report["summary"]["per_outlet_total"] = outlet_counts
    report["summary"]["per_language_total"] = lang_counts

    print(f"\n\n========== CYCLE COMPLETE ==========")
    print(f"  seen-urls register: {len(seen_before)} → {len(seen_after_all)}  (+{len(seen_after_all)-len(seen_before)})")
    print(f"  per outlet: {outlet_counts}")
    print(f"  per language: {lang_counts}")

    with open(args.out, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
