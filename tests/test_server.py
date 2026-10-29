import io
import zipfile

import pytest
import soundfile as sf
from starlette.testclient import TestClient

from stemwise import server
from stemwise.separate import STEMS

from .conftest import StubSeparator, wait_ready


def test_health_reports_version_and_stems(client):
    body = client.get("/api/health").json()
    assert body["stems"] == list(STEMS)
    assert body["device"] == "cpu"


def test_static_player_is_served(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Stemwise" in page.text
    assert client.get("/js/engine.js").status_code == 200
    assert client.get("/locales/zh-TW.json").status_code == 200


def test_upload_processes_and_lists(client, ready_song):
    song_id, meta = ready_song
    assert meta["title"] == "Practice Tune"
    assert meta["duration"] == pytest.approx(8.0, abs=0.05)
    assert meta["bpm"] == pytest.approx(120.0, abs=0.5)
    assert [c["label"] for c in meta["chords"]] == ["C", "Am", "F", "G"]
    assert meta["key"] == "C major"
    listing = client.get("/api/songs").json()
    assert [s["id"] for s in listing] == [song_id]
    assert "beats" not in listing[0]


def test_uploading_the_same_file_twice_reuses_the_song(client, song_wav, ready_song):
    res = client.post("/api/songs", params={"name": "again.wav"}, content=song_wav.read_bytes())
    assert res.status_code == 200
    assert res.json() == {"id": ready_song[0], "existing": True}


def test_stems_download_as_flac(client, ready_song):
    song_id, _ = ready_song
    for stem in STEMS:
        res = client.get(f"/api/songs/{song_id}/stems/{stem}.flac")
        assert res.status_code == 200
        audio, rate = sf.read(io.BytesIO(res.content))
        assert rate == 44100 and audio.shape[1] == 2


def test_unknown_stem_and_song(client, ready_song):
    song_id, _ = ready_song
    assert client.get(f"/api/songs/{song_id}/stems/kazoo.flac").status_code == 404
    assert client.get("/api/songs/000000000000").status_code == 404
    assert client.get("/api/songs/..%2F..%2Fetc").status_code == 404


def test_export_backing_track_leaves_out_stems(client, ready_song):
    song_id, _ = ready_song
    full = client.get(f"/api/songs/{song_id}/export/backing")
    without = client.get(f"/api/songs/{song_id}/export/backing", params={"without": "guitar"})
    assert full.headers["content-type"] == "audio/wav"
    a, _ = sf.read(io.BytesIO(full.content))
    b, _ = sf.read(io.BytesIO(without.content))
    assert abs(b).max() < abs(a).max() * 0.7


def test_export_everything_muted_is_a_clear_error(client, ready_song):
    song_id, _ = ready_song
    res = client.get(f"/api/songs/{song_id}/export/backing", params={"without": ",".join(STEMS)})
    assert res.status_code == 422


def test_export_formats(client, ready_song):
    song_id, _ = ready_song
    zipped = client.get(f"/api/songs/{song_id}/export/stems")
    names = zipfile.ZipFile(io.BytesIO(zipped.content)).namelist()
    assert sorted(names) == sorted(f"Practice Tune - {s}.flac" for s in STEMS)
    text = client.get(f"/api/songs/{song_id}/export/chords.txt").text
    assert "Am" in text and "Practice Tune" in text
    html = client.get(f"/api/songs/{song_id}/export/chords.html").text
    assert html.startswith("<!doctype html") and "Practice Tune" in html
    midi = client.get(f"/api/songs/{song_id}/export/beats.mid").content
    assert midi[:4] == b"MThd"
    assert client.get(f"/api/songs/{song_id}/export/nope").status_code == 404
    disposition = client.get(f"/api/songs/{song_id}/export/chords.txt").headers["content-disposition"]
    assert "chords.txt" in disposition


def test_rename_and_delete(client, ready_song):
    song_id, _ = ready_song
    res = client.patch(f"/api/songs/{song_id}", json={"title": "  My <b>riff</b>/..  "})
    assert res.json()["title"] == "My briffb.."
    assert client.patch(f"/api/songs/{song_id}", json={"title": "Mr. Brightside"}).json()["title"] == "Mr. Brightside"
    assert client.delete(f"/api/songs/{song_id}").status_code == 204
    assert client.get(f"/api/songs/{song_id}").status_code == 404


def test_empty_and_oversize_uploads_are_refused(client, monkeypatch):
    assert client.post("/api/songs", content=b"").status_code == 400
    monkeypatch.setattr(server, "MAX_UPLOAD", 1000)
    res = client.post("/api/songs", content=b"x" * 5000)
    assert res.status_code == 413
    leftovers = [p.name for p in client.app.state.library.root.iterdir() if p.name.startswith(".upload")]
    assert leftovers == []


def test_garbage_upload_ends_in_a_readable_error(client):
    res = client.post("/api/songs", params={"name": "notes.mp3"}, content=b"this is not audio" * 100)
    meta = wait_ready(client, res.json()["id"])
    assert meta["status"] == "error"
    assert meta["error"]
    # the worker survives and takes the next job
    assert client.get("/api/health").status_code == 200


def test_export_waits_for_processing(client, lib):
    lib.create("abcdef123456", "Pending", "p.mp3")
    assert client.get("/api/songs/abcdef123456/export/chords.txt").status_code == 409


def test_hosts_other_than_this_machine_are_refused(client):
    assert client.get("/api/songs", headers={"host": "evil.example"}).status_code == 403
    assert client.get("/api/songs", headers={"host": "localhost:8765"}).status_code == 200
    assert client.get("/api/songs", headers={"host": "[::1]:8765"}).status_code == 200


def test_cross_site_writes_are_refused(client, song_wav):
    body = song_wav.read_bytes()
    res = client.post("/api/songs", content=body, headers={"origin": "https://evil.example"})
    assert res.status_code == 403
    assert client.get("/api/songs").json() == []
    same = client.post("/api/songs", content=body, headers={"origin": "http://localhost", "host": "localhost"})
    assert same.status_code == 202


def test_extra_hosts_can_be_allowed(lib):
    app = server.create_app(lib, separator=StubSeparator(), extra_hosts={"studio.lan"})
    with TestClient(app, base_url="http://studio.lan") as c:
        assert c.get("/api/health").status_code == 200
    app.state.jobs.close()


def test_interrupted_jobs_are_marked_on_restart(lib):
    lib.create("abcdef123456", "Half done", "h.mp3")
    app = server.create_app(lib, separator=StubSeparator(), start_worker=False)
    assert lib.read("abcdef123456")["status"] == "error"
    assert app.state.jobs is None


def test_clean_title():
    assert server.clean_title("../../etc/My Song (live).mp3") == "My Song (live)"
    assert server.clean_title("???.wav") == "Untitled"
    assert server.clean_title("Mr. Brightside.mp3") == "Mr. Brightside"


def test_deleting_a_queued_song_does_not_stop_the_worker(client, song_wav, lib):
    from stemwise.pipeline import run_job

    lib.create("abcdef123456", "Gone", "g.wav")
    run_job(lib, "abcdef123456", song_wav, StubSeparator())  # finishes, then the song is removed under it
    lib.delete("abcdef123456")
    app_jobs = client.app.state.jobs
    app_jobs.submit("abcdef123456", song_wav.with_name("missing.wav"))
    res = client.post("/api/songs", params={"name": song_wav.name}, content=song_wav.read_bytes())
    assert wait_ready(client, res.json()["id"])["status"] == "ready"
    assert not lib.exists("abcdef123456")


def test_a_rename_during_processing_is_kept(lib, song_wav):
    from stemwise.pipeline import run_job

    lib.create("abcdef123456", "Before", "b.wav")

    class Renaming(StubSeparator):
        def split(self, *args, **kwargs):
            meta = lib.read("abcdef123456")
            meta["title"] = "After"
            lib.write("abcdef123456", meta)
            return super().split(*args, **kwargs)

    run_job(lib, "abcdef123456", song_wav, Renaming())
    assert lib.read("abcdef123456")["title"] == "After"


def test_non_ascii_titles_keep_their_name_in_downloads(client, song_wav):
    res = client.post("/api/songs", params={"name": "夜に駆ける.wav"}, content=song_wav.read_bytes())
    song_id = res.json()["id"]
    wait_ready(client, song_id)
    head = client.get(f"/api/songs/{song_id}/export/chords.txt").headers["content-disposition"]
    assert "filename*=UTF-8''%E5%A4%9C" in head


def test_interrupted_uploads_are_removed_on_restart(lib):
    lib.create("abcdef123456", "Half done", "h.mp3")
    (lib.folder("abcdef123456") / "source.mp3").write_bytes(b"x" * 10)
    server.create_app(lib, separator=StubSeparator(), start_worker=False)
    assert not list(lib.folder("abcdef123456").glob("source.*"))
