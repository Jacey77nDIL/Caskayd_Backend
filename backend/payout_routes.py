from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from database import get_db
from auth import oauth2_scheme, decode_user_id_from_jwt, SECRET_KEY, ALGORITHM
from jose import jwt
from models import UserCreator, BankAccount, Payout
from schemas import (
    BankListResponse, 
    BankAccountCreate, 
    BankAccountResponse, 
    PayoutRequest, 
    PayoutResponse
)
from paystack_service import paystack_service

router = APIRouter(prefix="/api/payouts", tags=["Payouts"])

@router.get("/banks", response_model=List[BankListResponse])
async def get_supported_banks():
    """Get list of banks supported by Paystack"""
    try:
        banks = await paystack_service.get_banks()
        return [
            BankListResponse(name=b["name"], code=b["code"], active=b["active"]) 
            for b in banks
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bank-account", response_model=BankAccountResponse)
async def add_bank_account(
    data: BankAccountCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Add or update creator's bank account"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can add bank accounts")

        # 1. Resolve Account Number
        account_details = await paystack_service.resolve_account_number(
            data.account_number, 
            data.bank_code
        )
        account_name = account_details["account_name"]
        
        # 2. Create Transfer Recipient
        recipient_code = await paystack_service.create_transfer_recipient(
            name=account_name,
            account_number=data.account_number,
            bank_code=data.bank_code
        )
        
        # 3. Get Bank Name (optional, but good for storage)
        banks = await paystack_service.get_banks()
        bank_name = next((b["name"] for b in banks if b["code"] == data.bank_code), "Unknown Bank")

        # 4. Save to Database
        result = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            existing_account.account_number = data.account_number
            existing_account.account_name = account_name
            existing_account.bank_code = data.bank_code
            existing_account.bank_name = bank_name
            existing_account.recipient_code = recipient_code
            db.add(existing_account)
            await db.commit()
            await db.refresh(existing_account)
            return existing_account
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
            await db.refresh(new_account)
            return new_account

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/bank-account", response_model=BankAccountResponse)
async def get_bank_account(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get creator's current bank account"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators have bank accounts")
            
        result = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(status_code=404, detail="No bank account found")
            
        return account
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/withdraw", response_model=PayoutResponse)
async def initiate_withdrawal(
    data: PayoutRequest,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Initiate a withdrawal to the connected bank account"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can withdraw funds")
            
        # 1. Check Bank Account
        result = await db.execute(select(BankAccount).where(BankAccount.user_id == user.id))
        account = result.scalar_one_or_none()
        
        if not account or not account.recipient_code:
            raise HTTPException(status_code=400, detail="Please add a valid bank account first")
            
        # 2. Generate Reference
        reference = f"payout_{uuid.uuid4().hex[:12]}"
        
        # 3. Initiate Transfer on Paystack
        # Note: Amount in Paystack transfer is in kobo
        amount_kobo = int(data.amount * 100)
        
        transfer_data = await paystack_service.initiate_transfer(
            amount=amount_kobo,
            recipient_code=account.recipient_code,
            reference=reference,
            reason=data.description
        )
        
        # 4. Record Payout
        payout = Payout(
            user_id=user.id,
            amount=data.amount,
            reference=reference,
            status="pending", # Paystack returns 'otp' or 'pending' usually
            recipient_code=account.recipient_code,
            transfer_code=transfer_data.get("transfer_code"),
            description=data.description
        )
        db.add(payout)
        await db.commit()
        await db.refresh(payout)
        
        return payout

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history", response_model=List[PayoutResponse])
async def get_payout_history(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get history of payouts"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        result = await db.execute(
            select(Payout)
            .where(Payout.user_id == user.id)
            .order_by(Payout.created_at.desc())
        )
        payouts = result.scalars().all()
        return payouts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
