from app.greetings import greet


def test_greet_returns_greeting():
    assert greet("Alice") == "Hello, Alice!"
