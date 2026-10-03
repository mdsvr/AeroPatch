import pytest

from aeropatch.agent.prompts import SecretInPrompt, check_no_secrets, redact


@pytest.mark.parametrize(
    "text",
    [
        "key = sk-ant-1234567890abcdefghijklmnopqrst",
        "GOOGLE_API_KEY=AIza" + "A" * 35,
        "github_pat_" + "a" * 30,
        'password = "s3cret-value-123"',
        'DB_PASSWORD = "s3cret-value-123"',
        "api_token = AbCd0123EfGh4567IjKl8901MnOp2345",
        "auth payload contains aB3dE7fG9hJ2kL4mN6pQ8rS1tV5wX0yZ",
    ],
)
def test_known_and_assignment_secrets_are_blocked(text):
    with pytest.raises(SecretInPrompt):
        check_no_secrets(text)


def test_placeholder_configuration_is_not_blocked():
    check_no_secrets('api_key = "your_api_key"')


def test_redacted_sandbox_feedback_passes_the_filter_without_the_value():
    trace = ("password = 's3cret!'\n\n    def hash_password(password):\nE   AssertionError\n"
             "E   FileNotFoundError: '/tmp/pytest-of-sandbox/pytest-0/test_other_ticket0/ticket-1/secret.txt'")
    with pytest.raises(SecretInPrompt):
        check_no_secrets(trace.split("\n")[-1])  # the temp path alone trips the entropy rule
    clean = redact(trace)
    assert "s3cret!" not in clean and "AssertionError" in clean and "FileNotFoundError" in clean
    check_no_secrets(clean)
    assert "sk-ant" not in redact("key = sk-ant-1234567890abcdefghijklmnopqrst")
    with pytest.raises(SecretInPrompt):  # whatever redaction leaves behind still meets the filter
        check_no_secrets(redact("see sk-ant-1234567890abcdefghijklmnopqrst"))
