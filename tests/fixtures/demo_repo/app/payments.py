def create_payment(user_id, amount):
    payment = {
        "user_id": user_id,
        "amount": amount,
    }

    return save_payment(payment)


def refund_payment(payment_id):
    return mark_payment_refunded(payment_id)