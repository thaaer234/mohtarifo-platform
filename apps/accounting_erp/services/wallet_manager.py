from decimal import Decimal
from django.db import transaction
from ..models.wallets import Wallet, WalletTransaction
from django.core.exceptions import ObjectDoesNotExist

class WalletManager:
    @staticmethod
    @transaction.atomic
    def credit(wallet, amount, source_event, reference_id=None, description=""):
        """
        Safely credits a wallet and records the transaction.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        balance_before = wallet.balance
        wallet.balance += amount
        wallet.save()

        return WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='credit',
            source_event=source_event,
            reference_id=reference_id,
            description=description,
            balance_before=balance_before,
            balance_after=wallet.balance
        )

    @staticmethod
    @transaction.atomic
    def debit(wallet, amount, source_event, reference_id=None, description="", allow_negative=False):
        """
        Safely debits a wallet and records the transaction.
        """
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        if not allow_negative and wallet.withdrawable_balance < amount:
            raise ValueError("Insufficient balance")

        balance_before = wallet.balance
        wallet.balance -= amount
        wallet.save()

        return WalletTransaction.objects.create(
            wallet=wallet,
            amount=amount,
            transaction_type='debit',
            source_event=source_event,
            reference_id=reference_id,
            description=description,
            balance_before=balance_before,
            balance_after=wallet.balance
        )

    @staticmethod
    def get_or_create_wallet(owner, owner_type):
        """
        Retrieves or creates a wallet for a specific owner.
        """
        params = {'owner_type': owner_type}
        if owner_type == 'STUDENT': params['student'] = owner
        elif owner_type == 'TEACHER': params['instructor'] = owner
        elif owner_type == 'CENTER': params['sales_center'] = owner
        
        wallet, created = Wallet.objects.get_or_create(**params)
        return wallet
