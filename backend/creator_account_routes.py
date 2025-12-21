"""
Simple endpoint for creators to submit their account details for payment collection
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from auth import oauth2_scheme, decode_user_id_from_jwt, SECRET_KEY, ALGORITHM
from jose import jwt
from models import UserCreator, BankAccount, Niche
from schemas import BankAccountCreate, BankAccountResponse, CreatorCurrentUserResponse, CreatorProfileUpdate
from paystack_service import paystack_service

router = APIRouter(prefix="/api/creator", tags=["Creator"])


@router.get("/me", response_model=CreatorCurrentUserResponse)
async def get_current_creator(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current logged-in creator's full profile with id, email, name, profile image, niches, and socials.
    This is useful for getting the creator_id to fetch creator-specific images.
    """
    try:
        # Decode JWT and get creator
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        # Only creators can access this endpoint
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can access this endpoint")
        
        # Fetch creator with relationships loaded
        result = await db.execute(
            select(UserCreator)
            .options(selectinload(UserCreator.niches))
            .options(selectinload(UserCreator.socials))
            .where(UserCreator.id == user.id)
        )
        creator = result.scalar_one_or_none()
        
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        
        return creator
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch creator: {str(e)}")


@router.put("/profile", response_model=CreatorCurrentUserResponse)
async def update_creator_profile(
    data: CreatorProfileUpdate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Update creator profile details like bio, location, profile image, followers count, engagement rate, and niches.
    This allows creators to update their profile information after initial sign-up.
    """
    try:
        # Decode JWT and get creator
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user, role = await decode_user_id_from_jwt(payload, db)
        
        # Only creators can access this endpoint
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can access this endpoint")
        
        # Fetch creator
        result = await db.execute(
            select(UserCreator)
            .options(selectinload(UserCreator.niches))
            .options(selectinload(UserCreator.socials))
            .where(UserCreator.id == user.id)
        )
        creator = result.scalar_one_or_none()
        
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        
        # Update fields if provided
        if data.name is not None:
            creator.name = data.name
        if data.bio is not None:
            creator.bio = data.bio
        if data.location is not None:
            creator.location = data.location
        if data.profile_image is not None:
            creator.profile_image = data.profile_image
        if data.followers_count is not None:
            creator.followers_count = data.followers_count
        if data.engagement_rate is not None:
            creator.engagement_rate = data.engagement_rate
        
        # Update niches if provided
        if data.niche_ids is not None:
            # Clear existing niches
            creator.niches.clear()
            # Add new niches
            if data.niche_ids:
                niches_result = await db.execute(
                    select(Niche).where(Niche.id.in_(data.niche_ids))
                )
                niches = niches_result.scalars().all()
                for niche in niches:
                    creator.niches.append(niche)
        
        await db.commit()
        await db.refresh(creator, ["niches", "socials"])
        
        return creator
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update profile: {str(e)}")


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
