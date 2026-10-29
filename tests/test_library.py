import pytest

from stemwise.library import hash_file, valid_id


def test_create_read_list_delete(lib):
    lib.create("abc123def456", "Song", "song.mp3")
    assert lib.exists("abc123def456")
    assert lib.read("abc123def456")["status"] == "queued"
    assert [s["id"] for s in lib.listing()] == ["abc123def456"]
    lib.delete("abc123def456")
    assert not lib.exists("abc123def456")
    assert lib.listing() == []


@pytest.mark.parametrize("bad", ["", "..", "../etc", "abc/def", "ABCDEF123456", "abc", "a" * 40, "abc123def45g"])
def test_ids_that_could_escape_the_library_are_rejected(bad):
    assert not valid_id(bad)


def test_hash_is_stable_and_content_based(tmp_path):
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"same bytes")
    b.write_bytes(b"same bytes")
    assert hash_file(a) == hash_file(b)
    assert valid_id(hash_file(a))
    b.write_bytes(b"other bytes")
    assert hash_file(a) != hash_file(b)


def test_listing_is_newest_first(lib):
    lib.create("aaaaaaaaaaaa", "Old", "old.mp3")
    meta = lib.read("aaaaaaaaaaaa")
    meta["created"] = "2020-01-01T00:00:00+0000"
    lib.write("aaaaaaaaaaaa", meta)
    lib.create("bbbbbbbbbbbb", "New", "new.mp3")
    assert [s["title"] for s in lib.listing()] == ["New", "Old"]
