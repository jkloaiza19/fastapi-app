from typing import Protocol
from enum import Enum


class PaymentMethod(Enum):
    CARD = 'CARD'
    PAYPAL = 'PAYPAL'


class Payment(Protocol):
    def pay(self, amount: int):
        pass


class CardPayment(Payment):
    def pay(self, amount: int):
        print(f"Paying amount ${amount} using Card.")


class PaypalPayment(Payment):
    def pay(self, amount: int):
        print(f"Paying amount ${amount} using Paypal.")


PAYMENT_METHODS: dict[PaymentMethod, type[Payment]] = {
    PaymentMethod.CARD: CardPayment,
    PaymentMethod.PAYPAL: PaypalPayment,
}


my_payment = PAYMENT_METHODS[PaymentMethod.PAYPAL]()

my_payment.pay(250)
