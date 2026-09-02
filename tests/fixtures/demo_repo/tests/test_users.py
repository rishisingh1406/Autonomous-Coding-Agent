def test_get_user_missing_user():

    user = get_user("missing-id")

    assert user is None


def test_create_user():

    user = create_user(
        "Alice",
        "alice@example.com",
    )

    assert user["name"] == "Alice"