"""Public game pages must not show internal codes or player IDs (the embedded data payload may keep them)."""

from nflcast.predict.verify_claims import public_raw_labels


def _page(tmp_path, gid, body):
    d = tmp_path / "game" / gid
    d.mkdir(parents=True)
    (d / "index.html").write_text(f"<html><head></head><body>{body}</body></html>", encoding="utf-8")


def test_raw_codes_in_visible_text_are_found(tmp_path):
    _page(tmp_path, "2026_03_CAR_CLE", "<p>chain_qb_unavailable_roster:00-0040704</p><td>roster:RES</td>")
    _page(tmp_path, "2026_03_ATL_GB", "<p>home QB: report_not_available</p>")
    _page(tmp_path, "2026_11_BAL_PIT", "<td>Lamar Jackson</td><td>R48</td>")          # a raw reserve-list code
    hits = public_raw_labels(tmp_path)
    assert set(hits) == {"2026_03_CAR_CLE", "2026_03_ATL_GB", "2026_11_BAL_PIT"}
    assert hits["2026_11_BAL_PIT"] == ["R48"]
    assert "00-0040704" in hits["2026_03_CAR_CLE"]


def test_plain_english_page_and_data_payload_pass(tmp_path):
    _page(tmp_path, "2026_03_HOU_IND",
          "<p>Joe Flacco is on the reserve list and cannot start.</p><td>Injured reserve, designated to return</td>"
          "<p>RESULTS by week; R2 and 2R are not codes.</p>"
          '<script>self.__next_f.push(["chain_qb_unavailable_roster:00-0040704"])</script>')
    assert public_raw_labels(tmp_path) == {}
