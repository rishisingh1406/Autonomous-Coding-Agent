class UserNotFoundError(Exception):
    pass


def get_user(user_id):
    user = database_find_user(user_id)

    if user is None:
        raise UserNotFoundError(
            f"User {user_id} not found"
        )

    return user


def create_user(name, email):
    return database_create_user(
        name=name,
        email=email,
    )


def delete_user(user_id):
    return database_delete_user(user_id)