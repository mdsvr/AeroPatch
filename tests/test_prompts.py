import pytest

from aeropatch.agent.prompts import SecretInPrompt, check_no_secrets


@pytest.mark.parametrize(
    "text",
    [
        "key = sk-ant-1234567890abcdefghijklmnopqrst",
        "GOOGLE_API_KEY=AIza" + "A" * 35,
        "github_pat_" + "a" * 30,
        'password = "s3cret-value-123"',
        "api_token = AbCd0123EfGh4567IjKl8901MnOp2345",
        "auth payload contains aB3dE7fG9hJ2kL4mN6pQ8rS1tV5wX0yZ",
    ],
)
def test_known_and_assignment_secrets_are_blocked(text):
    with pytest.raises(SecretInPrompt):
        check_no_secrets(text)


def test_placeholder_configuration_is_not_blocked():
    check_no_secrets('api_key = "your_api_key"')
