import pytest

pytestmark = pytest.mark.e2e


def test_empty_library_then_upload_then_export_and_delete(page, server_url, song_wav):
    page.goto(server_url)
    page.wait_for_selector("#empty:not([hidden])", timeout=15000)
    assert page.locator("#add-song").is_visible()

    page.set_input_files("#file-input", str(song_wav))
    page.wait_for_selector("#studio:not([hidden])", timeout=60000)
    assert page.inner_text("#song-title") == "Practice Tune"
    assert page.inner_text("#chip-key") == "C major"
    assert page.inner_text("#chip-bpm") == "120 BPM"
    assert page.locator("#chip-demo").is_hidden()
    page.wait_for_function("document.getElementById('chord-now').textContent === 'C'")
    assert page.locator("#song-select option").count() == 1

    page.click("#export-btn")
    hrefs = page.eval_on_selector_all("#export-menu a", "els => els.map(e => e.href)")
    assert len(hrefs) == 5
    page.keyboard.press("Escape")
    assert page.locator("#export-menu").is_hidden()
    page.click("#export-btn")
    for href in hrefs:
        assert page.request.get(href).ok, href
    with page.expect_download() as download:
        page.click("#export-menu a:has-text('Chord sheet (text)')")
    assert download.value.suggested_filename == "Practice Tune - chords.txt"

    page.click("#play")
    page.wait_for_function("document.getElementById('clock-time').textContent !== '0:00.0'", timeout=5000)

    page.once("dialog", lambda d: d.accept())
    page.click("#export-btn")
    page.click("#export-menu button")
    page.wait_for_selector("#empty:not([hidden])", timeout=10000)
    assert page.problems == []


def test_bad_upload_shows_the_reason(page, server_url, tmp_path):
    junk = tmp_path / "junk.mp3"
    junk.write_bytes(b"not audio at all" * 200)
    page.goto(server_url)
    page.wait_for_selector("#empty:not([hidden])")
    page.set_input_files("#file-input", str(junk))
    page.wait_for_selector("#toast.error", timeout=30000)
    assert "Could not process" in page.inner_text("#toast")
