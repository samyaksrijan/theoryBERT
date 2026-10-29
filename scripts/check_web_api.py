"""Exercise the actual HTTP boundary, verification gates and video export."""

import argparse
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from theorybert.data.generators import pattern_dfa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8501")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    def get(path):
        with urlopen(base + path, timeout=15) as response:
            return json.load(response)

    def task(payload, failure=False):
        request = Request(
            base + "/api/jobs",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=15) as response:
            job = json.load(response)["job_id"]
        deadline = time.monotonic() + 190
        while time.monotonic() < deadline:
            status = get("/api/jobs/" + job)
            if status["status"] != "running":
                if failure:
                    assert status["status"] == "error", status
                    return status
                assert status["status"] == "complete", status
                return status["result"]
            time.sleep(0.1)
        raise AssertionError("HTTP task did not finish within its budget.")

    assert get("/api/health")["status"] == "ready"
    catalog = get("/api/catalog")
    assert len(catalog["dfa"]) == len(catalog["cfg"]) == 3
    fixture = {
        "kind": "dfa",
        "description": "Binary strings that end in 01.",
        "input": "1101",
        "example_id": "manual-suffix-01",
        "source": "demo",
    }
    accepted = task(fixture)
    assert accepted["verified"] and accepted["trace"]["accepted"] and accepted["graph"]
    rejected = task({**fixture, "input": "00"})
    assert (
        rejected["verified"]
        and not rejected["trace"]["accepted"]
        and rejected["renderable"]
    )
    wrong = task({**fixture, "source": "incorrect"})
    assert (
        wrong["status"] == "EQUIVALENCE_FAILED"
        and wrong["reports"][0]["counterexample"] == []
    )
    assert not wrong["renderable"] and wrong["trace"] is None
    unverified = task({**fixture, "source": "manual", "candidate_json": json.dumps(pattern_dfa("01").to_dict()), "example_id": None})
    assert (
        unverified["status"] == "REFERENCE_UNAVAILABLE" and unverified["trace"] is not None
        and unverified["graph"] and not unverified["verified"] and not unverified["renderable"]
    )
    gate = task({"kind": "render", "result_id": unverified["id"]}, failure=True)
    assert "VerifiedDFA" in gate["error"]
    task(
        {**fixture, "source": "learned", "checkpoint": "artifacts/does-not-exist"},
        failure=True,
    )
    malformed = task(
        {**fixture, "reference_json": '{"states":[],"states":[]}'}, failure=True
    )
    assert "Duplicate" in malformed["error"]
    large = pattern_dfa("01010101")
    larger = task(
        {
            **fixture,
            "description": "Binary strings that end in 01010101.",
            "input": "01010101",
            "source": "manual",
            "candidate_json": json.dumps(large.to_dict()),
            "reference_json": json.dumps(large.to_dict()),
        }
    )
    assert larger["verified"] and not larger["renderable"] and larger["visual_error"]
    cfg = task(
        {"kind": "cfg", "grammar": "E -> E '+' E | 'id'", "input": "id + id + id"}
    )
    assert cfg["verified"] and len(cfg["trees"]) == 2 and len(cfg["steps"]) == 2
    empty = task({"kind": "cfg", "grammar": "S -> 'a' S 'b' |", "input": ""})
    assert empty["spec"]["input_tokens"] == [] and empty["verified"]
    task({"kind": "cfg", "grammar": "invalid grammar", "input": "a"}, failure=True)
    task({"kind": "render", "result_id": "forged"}, failure=True)
    video = task({"kind": "render", "result_id": accepted["id"], "quality": "preview"})
    with urlopen(
        Request(base + video["url"], headers={"Range": "bytes=0-31"}), timeout=15
    ) as response:
        assert response.status == 206 and len(response.read()) == 32
    tree_video = task(
        {
            "kind": "render",
            "result_id": cfg["id"],
            "tree_index": 1,
            "quality": "preview",
        }
    )
    assert tree_video["tree_index"] == 1
    for path in ("/", "/dfa", "/grammar", "/examples", "/research"):
        with urlopen(base + path, timeout=15) as response:
            assert response.status == 200 and b'id="root"' in response.read()
    try:
        get("/api/videos/not-a-video.mp4")
    except HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("An invalid video path was accepted.")
    print(
        "React API checks passed: DFA acceptance/rejection, failed gates, references, checkpoints, CFG ambiguity/epsilon, actual videos, byte ranges and page refreshes."
    )


if __name__ == "__main__":
    main()
