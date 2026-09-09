# buff/fam-guard branch tests: action tracker + telemetry (fast, no network).
import os

from simurg.agent_loop import ActionTracker
from simurg import telemetry


def test_action_loop_fires_on_repeated_clicks():
    t = ActionTracker(loop_threshold=3)
    assert t.note("click", "@ref-7 buy now").state == "clean"
    assert t.note("click", "@ref-7 buy now").state == "clean"
    v = t.note("click", "@ref-7 buy now")
    assert v.state == "corrupt" and any("x3" in r for r in v.reasons)


def test_varied_actions_stay_clean():
    t = ActionTracker()
    assert t.note("open", "https://a.example", output="loaded homepage with nav").state == "clean"
    assert t.note("snapshot", "", output="12 refs found on page").state == "clean"
    assert t.note("click", "@ref-3", output="cart opened, 2 items").state == "clean"


def test_stall_progresses_suspect_then_corrupt():
    t = ActionTracker(stall_suspect=3, stall_corrupt=5)
    assert t.note("click", "@a", output="  ").state == "clean"
    assert t.note("click", "@b", output="").state == "clean"
    assert t.note("click", "@c", output=" ").state == "suspect"
    assert t.note("click", "@d", output="").state == "suspect"
    assert t.note("click", "@e", output="").state == "corrupt"


def test_progress_resets_stall():
    t = ActionTracker()
    t.note("click", "@a", output="")
    t.note("click", "@b", output="")
    v = t.note("snapshot", "", output="page has 40 refs, cart total $24")
    assert v.state == "clean"


def test_consecutive_sentences_fire():
    from simurg.agent_loop import TextLoopTracker
    t = TextLoopTracker()
    t.note("The Margherita pizza costs ten whole dollars today. " * 3)
    assert t.verdict().state == "corrupt"


def test_varied_sentences_stay_clean():
    from simurg.agent_loop import TextLoopTracker
    t = TextLoopTracker()
    t.note("The Margherita costs ten dollars today. The Pepperoni costs twelve dollars today. "
           "The cart total updates after each click on the checkout button.")
    assert t.verdict().state == "clean"


def test_telemetry_roundtrip_and_summary(tmp_path):
    p = os.path.join(str(tmp_path), "guard.jsonl")
    telemetry.log_attempt(p, {"model": "flash", "verdict": "clean", "latency_s": 1.0})
    telemetry.log_attempt(p, {"model": "flash", "verdict": "corrupt", "latency_s": 3.0})
    telemetry.log_attempt(p, {"model": "glm", "verdict": "clean", "latency_s": 2.0})
    s = telemetry.summarize(p)
    assert s["attempts"] == 3
    assert s["by_verdict"] == {"clean": 2, "corrupt": 1}
    assert s["by_model"]["flash"] == 2
