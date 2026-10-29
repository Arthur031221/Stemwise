import re

import pytest

pytestmark = pytest.mark.e2e


def open_demo(page, url):
    page.goto(url)
    page.wait_for_selector("#studio:not([hidden])", timeout=30000)


def seconds(page) -> float:
    minutes, rest = page.inner_text("#clock-time").split(":")
    return int(minutes) * 60 + float(rest)


def drag_on_ruler(page, duration, start, end):
    box = page.locator("#timeline").bounding_box()
    y = box["y"] + 10
    page.mouse.move(box["x"] + box["width"] * start / duration, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * end / duration, y, steps=6)
    page.mouse.up()


def test_demo_loads_with_analysis_and_no_errors(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    assert page.inner_text("#song-title") == demo_meta["title"]
    assert page.inner_text("#chip-key") == "E major"
    assert page.inner_text("#chip-bpm") == f"{round(demo_meta['bpm'])} BPM"
    assert page.locator(".strip").count() == 6
    assert "Kevin MacLeod" in page.inner_text("#credit")
    assert page.locator("#export-btn").is_hidden()
    assert page.inner_text("#chord-now") == "E"
    assert page.locator("#guitar-diagram svg circle").count() > 3
    assert page.problems == []


def test_play_button_swaps_between_play_and_pause_icons(page, demo_url):
    open_demo(page, demo_url)
    assert page.locator("#icon-play").is_visible()
    assert page.locator("#icon-pause").is_hidden()
    page.click("#play")
    page.wait_for_selector("#icon-pause", state="visible", timeout=5000)
    assert page.locator("#icon-play").is_hidden()
    page.click("#play")
    page.wait_for_selector("#icon-play", state="visible", timeout=5000)


def test_play_pause_and_seek(page, demo_url):
    open_demo(page, demo_url)
    page.click("#play")
    page.wait_for_function("document.getElementById('clock-time').textContent !== '0:00.0'", timeout=5000)
    page.wait_for_timeout(1200)
    page.click("#play")
    paused_at = seconds(page)
    assert paused_at > 0.8
    page.wait_for_timeout(500)
    assert seconds(page) == pytest.approx(paused_at, abs=0.15)
    box = page.locator("#timeline").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + 150)
    page.wait_for_timeout(200)
    assert seconds(page) == pytest.approx(18.0, abs=1.0)


def test_loop_selected_on_the_ruler_stays_inside_the_bars(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    bars = demo_meta["downbeats"]
    drag_on_ruler(page, demo_meta["duration"], bars[4] + 0.2, bars[5] + 0.2)
    assert page.inner_text("#loop-info") == "Bars 5 to 6"
    assert page.get_attribute("#loop-toggle", "aria-pressed") == "true"
    page.fill("#tempo", "150")
    page.dispatch_event("#tempo", "input")
    page.click("#play")
    seen = []
    for _ in range(24):
        page.wait_for_timeout(150)
        seen.append(seconds(page))
    start, end = bars[4], bars[6]
    assert min(seen) >= start - 0.2, seen
    assert max(seen) <= end + 0.2, seen
    assert max(seen) - min(seen) > 1.0, "playhead should travel through the loop"
    assert any(b < a - 1.0 for a, b in zip(seen, seen[1:], strict=False)), "loop should wrap at least once"
    page.keyboard.press("Escape")
    assert page.inner_text("#loop-info").startswith("Drag")


def test_speed_and_pitch_controls(page, demo_url):
    open_demo(page, demo_url)
    page.click("#tempo-presets button:text('70%')")
    assert page.inner_text("#tempo-out") == "70%"
    page.keyboard.press("]")
    assert page.inner_text("#tempo-out") == "75%"
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowUp")
    assert page.inner_text("#pitch-out") == "+2"
    assert page.inner_text("#chord-now") == "F#"
    assert page.inner_text("#chip-key") == "F# major"
    page.check("#flats")
    assert page.inner_text("#chord-now") == "Gb"
    assert page.inner_text("#chip-key") == "Gb major"


def test_mute_and_solo(page, demo_url):
    open_demo(page, demo_url)
    drums = page.locator(".strip[data-stem=drums]")
    drums.locator("button.m").click()
    assert drums.locator("button.m").get_attribute("aria-pressed") == "true"
    assert "dim" in drums.get_attribute("class")
    page.locator(".strip[data-stem=bass] button.s").click()
    assert "dim" in page.locator(".strip[data-stem=guitar]").get_attribute("class")
    assert "dim" not in page.locator(".strip[data-stem=bass]").get_attribute("class")
    page.keyboard.press("2")
    assert drums.locator("button.m").get_attribute("aria-pressed") == "false"


def test_speed_trainer_raises_the_tempo_after_clean_loops(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    page.click("#trainer-toggle")
    assert page.locator("#toast.error").is_visible()
    bars = demo_meta["downbeats"]
    drag_on_ruler(page, demo_meta["duration"], bars[2] + 0.2, bars[3] + 0.2)
    for field, value in (("#tr-start", "140"), ("#tr-step", "5"), ("#tr-goal", "150"), ("#tr-loops", "1")):
        page.fill(field, value)
        page.dispatch_event(field, "change")
    page.click("#trainer-toggle")
    assert page.inner_text("#tempo-out") == "140%"
    page.click("#play")
    page.wait_for_function("document.getElementById('tempo-out').textContent === '145%'", timeout=15000)
    page.click("#tr-miss")
    page.click("#play")


def test_language_switch_and_persistence(page, demo_url):
    open_demo(page, demo_url)
    page.select_option("#lang-select", "zh-TW")
    page.wait_for_function("document.querySelector('label[for=tempo]').textContent === '速度'")
    assert page.get_attribute("html", "lang") == "zh-TW"
    assert page.inner_text(".strip[data-stem=drums] .name") == "鼓"
    page.reload()
    page.wait_for_selector("#studio:not([hidden])")
    assert page.text_content("label[for=tempo]") == "速度"
    page.select_option("#lang-select", "en")
    assert page.text_content("label[for=tempo]") == "Speed"


def test_theme_toggle(page, demo_url):
    open_demo(page, demo_url)
    assert page.get_attribute("html", "data-theme") == "dark"
    page.click("#theme-toggle")
    assert page.get_attribute("html", "data-theme") == "light"
    page.reload()
    assert page.get_attribute("html", "data-theme") == "light"


def test_phone_layout_has_no_sideways_scroll(page, demo_url):
    page.set_viewport_size({"width": 390, "height": 800})
    open_demo(page, demo_url)
    width = page.evaluate("document.documentElement.scrollWidth")
    assert width <= 391, width


def test_phone_layout_shows_whole_stem_names(page, demo_url):
    page.set_viewport_size({"width": 390, "height": 800})
    open_demo(page, demo_url)
    clipped = page.evaluate(
        "[...document.querySelectorAll('.strip .name')]"
        ".filter(e => e.scrollWidth > e.clientWidth).map(e => e.textContent)"
    )
    assert clipped == []


def test_stems_are_aligned_with_the_beat_grid(page, demo_url, demo_meta):
    """Decoded AAC stems must be as long as the analysis says, or the bars would drift."""
    open_demo(page, demo_url)
    lengths = page.evaluate(
        """async () => {
            const out = [];
            for (const s of ['drums', 'guitar']) {
                const buf = await (await fetch(`demo/surf-shimmy/${s}.m4a`)).arrayBuffer();
                const ctx = new OfflineAudioContext(2, 44100, 44100);
                out.push((await ctx.decodeAudioData(buf)).duration);
            }
            return out;
        }"""
    )
    for length in lengths:
        assert length == pytest.approx(demo_meta["duration"], abs=0.06)


def test_numbers_in_the_clock_look_right(page, demo_url):
    open_demo(page, demo_url)
    assert re.fullmatch(r"\d:\d\d\.\d", page.inner_text("#clock-time"))


def test_l_loops_the_current_bar_and_toggles_it(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    bars = demo_meta["downbeats"]
    page.keyboard.press("l")
    assert page.inner_text("#loop-info") == "Bars 1 to 1"
    assert page.get_attribute("#loop-toggle", "aria-pressed") == "true"
    page.keyboard.press("l")
    assert page.get_attribute("#loop-toggle", "aria-pressed") == "false"
    page.keyboard.press("l")
    assert page.get_attribute("#loop-toggle", "aria-pressed") == "true"
    page.keyboard.press("Escape")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(200)
    assert seconds(page) == pytest.approx(bars[1], abs=0.1)
    page.keyboard.press("l")
    assert page.inner_text("#loop-info") == "Bars 2 to 2"
    page.keyboard.press("Escape")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(200)
    assert seconds(page) == pytest.approx(bars[2], abs=0.1)
    page.keyboard.press("ArrowLeft")
    page.wait_for_timeout(200)
    assert seconds(page) == pytest.approx(bars[1], abs=0.1)


def test_practice_setup_comes_back_after_a_reload(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    page.click("#tempo-presets button:text('70%')")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("2")
    page.locator("#click-toggle").click()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("l")
    info = page.inner_text("#loop-info")
    assert info == "Bars 2 to 2"
    open_demo(page, demo_url)
    assert page.inner_text("#tempo-out") == "70%"
    assert page.input_value("#tempo") == "70"
    assert page.inner_text("#pitch-out") == "-1"
    assert page.input_value("#pitch") == "-1"
    assert page.inner_text("#chip-key") == "D# major"
    assert page.locator(".strip[data-stem=drums] button.m").get_attribute("aria-pressed") == "true"
    assert page.get_attribute("#click-toggle", "aria-pressed") == "true"
    assert page.inner_text("#loop-info") == info
    assert page.get_attribute("#loop-toggle", "aria-pressed") == "true"
    assert page.locator("#clock-time").inner_text() != ""
    assert page.problems == []


def test_a_corrupt_saved_setup_is_ignored(page, demo_url):
    page.goto(demo_url)
    page.evaluate("localStorage.setItem('stemwise.song.surf-shimmy', '{broken')")
    page.evaluate("localStorage.setItem('stemwise.prefs', '7')")
    open_demo(page, demo_url)
    assert page.inner_text("#tempo-out") == "100%"
    assert page.problems == []


def test_shift_arrows_resize_the_loop_by_bars(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    page.keyboard.press("Shift+ArrowRight")
    assert page.inner_text("#loop-info") == "Bars 1 to 1"
    page.keyboard.press("Shift+ArrowRight")
    page.keyboard.press("Shift+ArrowRight")
    assert page.inner_text("#loop-info") == "Bars 1 to 3"
    page.keyboard.press("Shift+ArrowLeft")
    assert page.inner_text("#loop-info") == "Bars 1 to 2"
    page.keyboard.press("Shift+ArrowLeft")
    page.keyboard.press("Shift+ArrowLeft")
    assert page.inner_text("#loop-info") == "Bars 1 to 1"
    assert page.get_attribute("#timeline", "aria-label").startswith("Timeline")
    assert page.problems == []


def test_play_after_the_song_ended_starts_again_from_the_top(page, demo_url, demo_meta):
    open_demo(page, demo_url)
    box = page.locator("#timeline").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.985, box["y"] + 150)
    page.click("#play")
    page.wait_for_selector("#icon-play", state="visible", timeout=8000)
    assert seconds(page) > demo_meta["duration"] - 1.5
    page.click("#play")
    page.wait_for_timeout(1200)
    assert page.locator("#icon-pause").is_visible()
    assert 0.3 < seconds(page) < 3


def test_arrow_keys_move_a_focused_slider_and_not_the_song(page, demo_url):
    open_demo(page, demo_url)
    page.focus("#tempo")
    page.keyboard.press("ArrowRight")
    assert page.inner_text("#tempo-out") == "101%"
    page.keyboard.press("ArrowUp")
    assert page.inner_text("#pitch-out") == "0"
    assert seconds(page) == 0


def test_count_in_waits_a_bar_even_with_the_click_off(page, demo_url):
    open_demo(page, demo_url)
    page.click("#count-in")
    assert page.get_attribute("#click-toggle", "aria-pressed") == "false"
    page.click("#play")
    page.wait_for_timeout(500)
    assert seconds(page) == 0
    page.wait_for_function("document.getElementById('clock-time').textContent !== '0:00.0'", timeout=5000)
