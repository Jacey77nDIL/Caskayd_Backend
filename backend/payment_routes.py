from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid
import hmac
import hashlib
import os
import logging

from database import get_db
from auth import oauth2_scheme, decode_user_id_from_jwt, SECRET_KEY, ALGORITHM
from jose import jwt
from models import Transaction, TransactionStatus, UserBusiness, UserCreator
from paystack_service import paystack_service
from schemas import PaymentInitializeResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Payments"])

class PayCreatorRequest(BaseModel):
    creator_id: int
    amount: float
    campaign_id: Optional[int] = None
    description: Optional[str] = None

@router.post("/pay-creator", response_model=PaymentInitializeResponse)
async def pay_creator(
    data: PayCreatorRequest,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Business initiates a payment to a creator.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can pay creators")
            
        # Verify Creator exists
        creator_res = await db.execute(select(UserCreator).where(UserCreator.id == data.creator_id))
        creator = creator_res.scalar_one_or_none()
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
            
        # Initialize Paystack Transaction
        amount_kobo = int(data.amount * 100)
        reference = f"pay_{uuid.uuid4().hex[:12]}"
        
        metadata = {
            "payment_type": "creator_payment",
            "creator_id": data.creator_id,
            "business_id": user.id,
            "campaign_id": data.campaign_id,
            "description": data.description
        }
        
        result = await paystack_service.initialize_transaction(
            email=user.email,
            amount=amount_kobo,
            reference=reference,
            metadata=metadata,
            callback_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/payment/callback"
        )
        
        # Record Transaction
        transaction = Transaction(
            reference=reference,
            amount=data.amount,
            currency="NGN",
            email=user.email,
            status=TransactionStatus.pending,
            user_id=user.id,
            user_type="business",
            recipient_id=data.creator_id,
            authorization_url=result["authorization_url"],
            access_code=result["access_code"],
            purpose="creator_payment",
            transaction_metadata=metadata
        )
        db.add(transaction)
        await db.commit()
        
        return PaymentInitializeResponse(
            status=True,
            authorization_url=result["authorization_url"],
            access_code=result["access_code"],
            reference=reference
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Paystack Webhooks
    """
    try:
        body = await request.body()
        secret = os.getenv("PAYSTACK_SECRET")
        
        # Verify Signature
        hash_object = hmac.new(secret.encode('utf-8'), body, hashlib.sha512)
        expected_signature = hash_object.hexdigest()
        
        if x_paystack_signature != expected_signature:
            raise HTTPException(status_code=400, detail="Invalid signature")
            
        event = await request.json()
        event_type = event.get("event")
        data = event.get("data", {})
        
        if event_type == "charge.success":
            reference = data.get("reference")
            
            # Update Transaction
            result = await db.execute(select(Transaction).where(Transaction.reference == reference))
            transaction = result.scalar_one_or_none()
            
            if transaction:
                transaction.status = TransactionStatus.success
                transaction.paid_at = data.get("paid_at")
                await db.commit()
                logger.info(f"Payment successful for reference: {reference}")
                
                # TODO: If we had a Wallet system, we would credit the creator here.
                # For now, the transaction record serves as proof of payment.
                
        elif event_type == "transfer.success":
            # Handle Payout Success
            reference = data.get("reference")
            from models import Payout, PayoutStatus
            
            result = await db.execute(select(Payout).where(Payout.reference == reference))
            payout = result.scalar_one_or_none()
            
            if payout:
                payout.status = PayoutStatus.SUCCESS
                await db.commit()
                logger.info(f"Payout successful for reference: {reference}")
                
        elif event_type == "transfer.failed":
             # Handle Payout Failure
            reference = data.get("reference")
            from models import Payout, PayoutStatus
            
            result = await db.execute(select(Payout).where(Payout.reference == reference))
            payout = result.scalar_one_or_none()
            
            if payout:
                payout.status = PayoutStatus.FAILED
                await db.commit()
                logger.warning(f"Payout failed for reference: {reference}")

        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
