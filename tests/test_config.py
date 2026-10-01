from aeropatch.config import load_config


def test_ollama_host_environment_variable_is_used(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.example:11434")

    assert load_config("baseline-qwen3.5-4b")["local_host"] == "http://ollama.example:11434"


def test_explicit_local_host_override_wins_over_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.example:11434")

    assert load_config("baseline-qwen3.5-4b", local_host="http://localhost:11434")["local_host"] == \
        "http://localhost:11434"
