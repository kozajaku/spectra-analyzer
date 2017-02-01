import pytest
from spectra_analyzer import server


@pytest.mark.parametrize("input, expected", [(0, "0 B"), (500, "500 B"),
                                             (999, "999 B"), (1000, "1.00 kB"), (8797, "8.80 kB"),
                                             (549848951, "549.85 MB"), (456545999992, "456.55 GB")])
def test_format_size(input, expected):
    """Test format_size function - should return file size in human readable string format."""
    assert server.format_size(input) == expected


def test_format_mtime():
    """Test format_mtime function - should return time from epoch converted to
    human readable format."""
    mtime = 1485975119
    assert server.format_mtime(mtime) == "19:51:59 01. 02. 2017"


def test_serialize_path1(tmpdir):
    """Test path serialization. """
    # create file hierarchy
    tmpdir.mkdir("dir1")
    tmpdir.mkdir("dir2")
    tmpdir.mkdir("dir3")
    tmpdir.join("file1").open("a").close()
    tmpdir.join("file2").open("a").close()
    res = server.serialize_path(str(tmpdir))
    listing = res["directory"]
    dirs = 0
    files = 0
    back = False
    for item in listing:
        if item["is_file"]:
            files += 1
        else:
            dirs += 1
            if item["name"] == "..":
                back = True
    assert dirs == 4
    assert files == 2
    assert back


def test_serialize_path2(tmpdir):
    """Test path serialization. In this case path points to a file - test
    that the file is selected."""
    # create file hierarchy
    tmpdir.mkdir("dir1")
    tmpdir.mkdir("dir2")
    tmpdir.join("file1").open("a").close()
    tmpdir.join("file2").open("a").close()
    file = tmpdir.join("file3")
    file.open("a").close()
    res = server.serialize_path(str(file))
    listing = res["directory"]
    dirs = 0
    files = 0
    back = False
    selected = False
    for item in listing:
        if item["is_file"]:
            files += 1
            if item["selected"]:
                if selected:
                    assert False
                else:
                    selected = True
        else:
            dirs += 1
            if item["name"] == "..":
                back = True
    assert dirs == 3
    assert files == 3
    assert back
    assert selected
