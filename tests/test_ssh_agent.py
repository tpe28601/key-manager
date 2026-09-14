from pathlib import Path

from key_manager.command import CommandResult
from key_manager.ssh.agent import add_key_to_agent, get_agent_status


def test_agent_status_parses_fingerprints_with_git_ssh_add(monkeypatch):
    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    monkeypatch.setattr("key_manager.ssh.agent.find_git_ssh_add", lambda: ssh_add)
    monkeypatch.setattr(
        "key_manager.ssh.agent.run_command",
        lambda args, timeout=30.0: CommandResult(0, "256 SHA256:abc comment (ED25519)\n", ""),
    )
    status = get_agent_status()
    assert status.available is True
    assert "SHA256:abc" in status.fingerprints


def test_add_key_to_agent_passes_only_path_to_git_ssh_add(monkeypatch, tmp_path: Path):
    seen = {}
    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    monkeypatch.setattr("key_manager.ssh.agent.find_git_ssh_add", lambda: ssh_add)

    def fake(args, timeout=30.0):
        seen["args"] = list(args)
        seen["timeout"] = timeout
        return CommandResult(0, "", "")

    monkeypatch.setattr("key_manager.ssh.agent.run_command", fake)
    path = tmp_path / "id_ed25519"
    add_key_to_agent(path)
    assert seen["args"] == [str(ssh_add), str(path)]
    assert seen["timeout"] == 120.0


def test_add_key_auto_starts_git_ssh_agent_and_reuses_its_environment(monkeypatch, tmp_path: Path):
    from key_manager.ssh import agent as agent_module

    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    ssh_agent = Path(r"C:\Program Files\Git\usr\bin\ssh-agent.exe")
    monkeypatch.setattr(agent_module, "find_git_ssh_add", lambda: ssh_add)
    monkeypatch.setattr(agent_module, "find_git_ssh_agent", lambda: ssh_agent)
    monkeypatch.setattr(agent_module, "_managed_agent_env", {})

    calls = []

    def fake(args, timeout=30.0, env=None, input_text=None):
        calls.append((list(args), dict(env or {})))
        if list(args) == [str(ssh_add), "-l"] and "SSH_AUTH_SOCK" not in (env or {}):
            return CommandResult(2, "", "Could not open a connection to your authentication agent.")
        if list(args) == [str(ssh_agent), "-s"]:
            return CommandResult(
                0,
                "SSH_AUTH_SOCK=/tmp/ssh-AbCd/agent.100; export SSH_AUTH_SOCK;\n"
                "SSH_AGENT_PID=101; export SSH_AGENT_PID;\n"
                "echo Agent pid 101;\n",
                "",
            )
        if list(args) == [str(ssh_add), "-l"]:
            return CommandResult(1, "The agent has no identities.\n", "")
        if list(args)[0] == str(ssh_add):
            return CommandResult(0, "", "")
        raise AssertionError(args)

    monkeypatch.setattr(agent_module, "run_command", fake)
    key_path = tmp_path / "id_ed25519"
    result = agent_module.add_key_to_agent(key_path)

    assert result.returncode == 0
    add_call = next(call for call in calls if call[0] == [str(ssh_add), str(key_path)])
    assert add_call[1]["SSH_AUTH_SOCK"] == "/tmp/ssh-AbCd/agent.100"
    assert add_call[1]["SSH_AGENT_PID"] == "101"
    assert agent_module.get_agent_status().available is True


def test_agent_parser_rejects_incomplete_ssh_agent_output():
    from key_manager.ssh.agent import parse_agent_environment

    assert parse_agent_environment("SSH_AUTH_SOCK=/tmp/a; export SSH_AUTH_SOCK;") == {}


def test_add_key_to_agent_uses_git_askpass_for_passphrase_prompt(monkeypatch, tmp_path: Path):
    from key_manager.ssh import agent as agent_module

    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    askpass = Path(r"C:\Program Files\Git\mingw64\libexec\git-core\git-gui--askpass.exe")
    monkeypatch.setattr(agent_module, "find_git_ssh_add", lambda: ssh_add)
    monkeypatch.setattr(agent_module, "find_git_ssh_askpass", lambda: askpass)
    monkeypatch.setattr(
        agent_module,
        "_managed_agent_env",
        {"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock", "SSH_AGENT_PID": "101"},
    )

    calls = []

    def fake(args, timeout=30.0, env=None, input_text=None):
        calls.append((list(args), dict(env or {})))
        if list(args) == [str(ssh_add), "-l"]:
            return CommandResult(1, "The agent has no identities.\n", "")
        if list(args)[0] == str(ssh_add):
            return CommandResult(0, "", "")
        raise AssertionError(args)

    monkeypatch.setattr(agent_module, "run_command", fake)
    key_path = tmp_path / "id_ed25519"
    result = agent_module.add_key_to_agent(key_path)

    assert result.returncode == 0
    add_env = next(env for args, env in calls if args == [str(ssh_add), str(key_path)])
    assert add_env["SSH_ASKPASS"] == str(askpass)
    assert add_env["GIT_ASKPASS"] == str(askpass)
    assert add_env["SSH_ASKPASS_REQUIRE"] == "force"
    assert add_env["DISPLAY"]
    add_args = next(args for args, _env in calls if args == [str(ssh_add), str(key_path)])
    assert "passphrase" not in " ".join(add_args).lower()


def test_add_key_to_agent_reports_missing_askpass_when_interactive_add_fails(monkeypatch, tmp_path: Path):
    from key_manager.ssh import agent as agent_module

    ssh_add = Path(r"C:\Program Files\Git\usr\bin\ssh-add.exe")
    monkeypatch.setattr(agent_module, "find_git_ssh_add", lambda: ssh_add)
    monkeypatch.setattr(agent_module, "find_git_ssh_askpass", lambda: None)
    monkeypatch.setattr(
        agent_module,
        "_managed_agent_env",
        {"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock", "SSH_AGENT_PID": "101"},
    )

    def fake(args, timeout=30.0, env=None, input_text=None):
        if list(args) == [str(ssh_add), "-l"]:
            return CommandResult(1, "The agent has no identities.\n", "")
        if list(args) == [str(ssh_add), str(tmp_path / "id_ed25519")]:
            return CommandResult(1, "", "Enter passphrase for key")
        raise AssertionError(args)

    monkeypatch.setattr(agent_module, "run_command", fake)
    result = agent_module.add_key_to_agent(tmp_path / "id_ed25519")

    assert result.returncode != 0
    assert "找不到 Git for Windows SSH AskPass" in result.stderr
