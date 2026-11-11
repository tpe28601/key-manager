"""Unit tests for the ~/.ssh/config parser (SPEC-1.2 section 4.5 scope)."""

from __future__ import annotations

from pathlib import Path

from key_manager.ssh import sshconfig


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_host_aliases_hostname_and_identity(tmp_path: Path):
    config = _write(tmp_path / "config", """# top comment
Host dev web
    HostName dev.example.com
    User bob   # inline comment must not leak into the value
    IdentityFile ~/.ssh/id_dev

Host *
    IdentityFile ~/.ssh/id_default
""")
    data = sshconfig.parse_ssh_config(config)
    by_pattern = {block.pattern: block for block in data.hosts}
    assert {"dev", "web", "*"} <= set(by_pattern)
    dev = by_pattern["dev"]
    assert dev.hostname == "dev.example.com"
    assert dev.identity_files == ("~/.ssh/id_dev",)
    assert dev.patterns == ("dev", "web")
    assert by_pattern["*"].identity_files == ("~/.ssh/id_default",)
    assert by_pattern["web"].source == str(config)
    assert data.match_blocks == 0
    assert data.unresolved_includes == []


def test_multiple_identity_files_and_equals_syntax(tmp_path: Path):
    config = _write(tmp_path / "config", """Host multi
HostName=multi.example.com
IdentityFile "C:/keys/id_one"
identityfile /home/alice/.ssh/id_two
""")
    block = sshconfig.parse_ssh_config(config).hosts[0]
    assert block.hostname == "multi.example.com"
    assert block.identity_files == ("C:/keys/id_one", "/home/alice/.ssh/id_two")


def test_include_one_level_and_match_skipped(tmp_path: Path):
    _write(tmp_path / "extra.d" / "10-team.conf", """Host inner
    HostName inner.example.com
    IdentityFile ~/keys/id_inner
""")
    config = _write(tmp_path / "config", """Host base
    IdentityFile ~/.ssh/id_base

Include extra.d/*.conf

Match host 10.0.0.*
    IdentityFile ~/.ssh/id_match
""")
    data = sshconfig.parse_ssh_config(config)
    patterns = [block.pattern for block in data.hosts]
    assert patterns == ["base", "inner"]
    inner = next(block for block in data.hosts if block.pattern == "inner")
    assert inner.identity_files == ("~/keys/id_inner",)
    all_identities = " ".join(item for block in data.hosts for item in block.identity_files)
    assert "id_match" not in all_identities
    assert data.match_blocks == 1


def test_include_glob_without_match_is_reported(tmp_path: Path):
    config = _write(tmp_path / "config", "Include nothing/*.conf\nHost a\n    HostName a.example.com\n")
    data = sshconfig.parse_ssh_config(config)
    assert data.unresolved_includes == ["nothing/*.conf"]
    assert [block.pattern for block in data.hosts] == ["a"]


def test_include_inside_include_is_not_followed(tmp_path: Path):
    _write(tmp_path / "d" / "one.conf", """Host one
    IdentityFile ~/.ssh/id_one
Include two.conf
""")
    _write(tmp_path / "d" / "two.conf", "Host two\n    IdentityFile ~/.ssh/id_two\n")
    config = _write(tmp_path / "config", "Include d/one.conf\n")
    data = sshconfig.parse_ssh_config(config)
    assert [block.pattern for block in data.hosts] == ["one"]
    assert data.unresolved_includes == ["有 Include 未解析"]


def test_keywords_before_first_host_are_ignored(tmp_path: Path):
    config = _write(tmp_path / "config", "IdentityFile ~/.ssh/id_global\nHost a\n    HostName a.example.com\n")
    data = sshconfig.parse_ssh_config(config)
    assert [block.pattern for block in data.hosts] == ["a"]
    assert data.hosts[0].identity_files == ()


def test_missing_file_returns_empty(tmp_path: Path):
    data = sshconfig.parse_ssh_config(tmp_path / "absent")
    assert data.hosts == []


def test_expand_identity_path():
    ssh_dir = Path("C:/Users/alice/.ssh")
    assert sshconfig.expand_identity_path("%d/id_ed", ssh_dir).replace("\\", "/") == (ssh_dir / "id_ed").as_posix()
    assert sshconfig.expand_identity_path("~/.ssh/id_rsa", ssh_dir).replace("\\", "/").endswith("/.ssh/id_rsa")
    assert sshconfig.expand_identity_path('"C:/k/id quoted"', ssh_dir) == "C:/k/id quoted"
