from wholagged.checks import parse_sdr_pops, pick_cm_targets, short_error

from fakes import CM_LIST, SDR


def test_pick_cm_targets_prefers_websockets():
    targets = pick_cm_targets(CM_LIST["response"]["serverlist"], limit=10)
    assert len(targets) == 4
    assert targets[0] == ("ext1-fra1.steamserver.net", 27019, "fra1")
    assert all(not host[0].isdigit() for host, _, _ in targets)


def test_pick_cm_targets_skips_bad_endpoints():
    servers = [{"endpoint": "nohost"}, {"endpoint": ":80"}, {"endpoint": "a.b:x"}, {"endpoint": "ok.host:443"}]
    assert pick_cm_targets(servers) == [("ok.host", 443, "?")]


def test_parse_sdr_pops():
    pops = parse_sdr_pops(SDR)
    assert {p.code for p in pops} == {"sto", "vie", "fra", "dxb", "sgp"}
    assert parse_sdr_pops({}) == []
    assert parse_sdr_pops("garbage") == []


def test_short_error_clips():
    assert short_error("x" * 200).endswith("…")
    assert short_error(TimeoutError()) == "timeout"
