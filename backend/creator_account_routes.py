"""
Simple endpoint for creators to submit their account details for payment collection
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from auth import oauth2_scheme, decode_user_id_from_jwt, SECRET_KEY, ALGORITHM
from jose import jwt
from models import UserCreator, BankAccount
from schemas import BankAccountCreate, BankAccountResponse
from paystack_service import paystack_service

router = APIRouter(prefix="/api/creator", tags=["Creator"])


@router.post("/submit-account", response_model=BankAccountResponse)
async def submit_account_details(
    data: BankAccountCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Creator submits their bank account details to receive payments.
    
    Request:
    {
        "account_number": "1234567890",
        "bank_code": "011"
    }
    """
    try:
        # Decode JWT and get creator
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        # Only creators can submit accounts
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can submit payment accounts")

        # Validate account number format
        if not data.account_number or len(data.account_number) != 10:
            raise HTTPException(status_code=400, detail="Account number must be 10 digits")

        # Resolve account with Paystack to get account name
        account_details = await paystack_service.resolve_account_number(
            data.account_number, 
            data.bank_code
        )
        account_name = account_details.get("account_name")
        
        if not account_name:
            raise HTTPException(status_code=400, detail="Invalid account number or bank code")

        # Create transfer recipient on Paystack
        recipient_code = await paystack_service.create_transfer_recipient(
            name=account_name,
            account_number=data.account_number,
            bank_code=data.bank_code
        )

        # Get bank name from Paystack
        banks = await paystack_service.get_banks()
        bank_name = next((b["name"] for b in banks if b["code"] == data.bank_code), "Unknown Bank")

        # Check if creator already has account
        result = await db.execute(
            select(BankAccount).where(BankAccount.user_id == user.id)
        )
        existing_account = result.scalar_one_or_none()

        # Save or update account in database
        if existing_account:
            existing_account.account_number = data.account_number
            existing_account.account_name = account_name
            existing_account.bank_code = data.bank_code
            existing_account.bank_name = bank_name
            existing_account.recipient_code = recipient_code
            db.add(existing_account)
        else:
            new_account = BankAccount(
                user_id=user.id,
                account_number=data.account_number,
                account_name=account_name,
                bank_code=data.bank_code,
                bank_name=bank_name,
                recipient_code=recipient_code
            )
            db.add(new_account)

        await db.commit()
        
        # Fetch the saved account
        result = await db.execute(
            select(BankAccount).where(BankAccount.user_id == user.id)
        )
        saved_account = result.scalar_one()
        
        return saved_account

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to save account: {str(e)}")
