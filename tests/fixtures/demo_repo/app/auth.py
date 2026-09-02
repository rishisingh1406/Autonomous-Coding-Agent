def authenticate(username, password):
    user = find_user_by_username(username)

    if user is None:
        return False

    return check_password(
        password,
        user.password_hash,
    )


def create_token(user):
    return generate_jwt(user.id)