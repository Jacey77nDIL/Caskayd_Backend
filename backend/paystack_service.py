# backend/paystack_service.py
import os
import logging
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")
PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackService:
    def __init__(self):
        self.secret_key = PAYSTACK_SECRET
        self.base_url = PAYSTACK_BASE_URL
        
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for Paystack API"""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    
    async def initialize_transaction(
        self,
        email: str,
        amount: int,  # Amount in kobo (smallest currency unit)
        currency: str = "NGN",
        reference: Optional[str] = None,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Initialize a payment transaction
        
        Args:
            email: Customer email
            amount: Amount in kobo (e.g., 20000 = ₦200.00)
            currency: Currency code (default: NGN)
            reference: Unique transaction reference
            callback_url: URL to redirect after payment
            metadata: Additional data to attach to transaction
        """
        try:
            payload = {
                "email": email,
                "amount": amount,
                "currency": currency
            }
            
            if reference:
                payload["reference"] = reference
            if callback_url:
                payload["callback_url"] = callback_url
            if metadata:
                payload["metadata"] = metadata
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transaction/initialize",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                data = response.json()
                
                if response.status_code != 200 or not data.get("status"):
                    logger.error(f"Paystack initialization failed: {data}")
                    raise Exception(f"Payment initialization failed: {data.get('message', 'Unknown error')}")
                
                return {
                    "status": True,
                    "authorization_url": data["data"]["authorization_url"],
                    "access_code": data["data"]["access_code"],
                    "reference": data["data"]["reference"]
                }
                
        except httpx.TimeoutException:
            logger.error("Paystack API timeout")
            raise Exception("Payment service timeout. Please try again.")
        except Exception as e:
            logger.error(f"Paystack initialization error: {str(e)}")
            raise
    
    async def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction using its reference
        
        Args:
            reference: Transaction reference to verify
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/transaction/verify/{reference}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                data = response.json()
                
                if response.status_code != 200:
                    logger.error(f"Paystack verification failed: {data}")
                    raise Exception(f"Payment verification failed: {data.get('message', 'Unknown error')}")
                
                transaction_data = data["data"]
                
                return {
                    "status": data.get("status"),
                    "transaction_status": transaction_data.get("status"),
                    "reference": transaction_data.get("reference"),
                    "amount": transaction_data.get("amount"),
                    "currency": transaction_data.get("currency"),
                    "paid_at": transaction_data.get("paid_at"),
                    "customer": transaction_data.get("customer"),
                    "metadata": transaction_data.get("metadata")
                }
                
        except httpx.TimeoutException:
            logger.error("Paystack API timeout during verification")
            raise Exception("Payment verification timeout. Please try again.")
        except Exception as e:
            logger.error(f"Paystack verification error: {str(e)}")
            raise


    async def get_banks(self) -> List[Dict[str, Any]]:
        """Fetch list of supported banks"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/bank",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                data = response.json()
                if response.status_code != 200:
                    raise Exception(f"Failed to fetch banks: {data.get('message')}")
                return data["data"]
        except Exception as e:
            logger.error(f"Paystack get_banks error: {str(e)}")
            raise

    async def resolve_account_number(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        """Verify account number and get account name"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/bank/resolve",
                    params={"account_number": account_number, "bank_code": bank_code},
                    headers=self._get_headers(),
                    timeout=30.0
                )
                data = response.json()
                if response.status_code != 200:
                    raise Exception(f"Account resolution failed: {data.get('message')}")
                return data["data"]
        except Exception as e:
            logger.error(f"Paystack resolve_account error: {str(e)}")
            raise

    async def create_transfer_recipient(
        self, 
        name: str, 
        account_number: str, 
        bank_code: str, 
        currency: str = "NGN"
    ) -> str:
        """Create a transfer recipient (beneficiary)"""
        try:
            payload = {
                "type": "nuban",
                "name": name,
                "account_number": account_number,
                "bank_code": bank_code,
                "currency": currency
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transferrecipient",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                data = response.json()
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to create recipient: {data.get('message')}")
                return data["data"]["recipient_code"]
        except Exception as e:
            logger.error(f"Paystack create_recipient error: {str(e)}")
            raise

    async def initiate_transfer(
        self, 
        amount: int, 
        recipient_code: str, 
        reference: str, 
        reason: str = "Payout"
    ) -> Dict[str, Any]:
        """Initiate a transfer (payout)"""
        try:
            payload = {
                "source": "balance",
                "amount": amount,
                "recipient": recipient_code,
                "reference": reference,
                "reason": reason
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transfer",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                data = response.json()
                if response.status_code != 200:
                    raise Exception(f"Transfer failed: {data.get('message')}")
                return data["data"]
        except Exception as e:
            logger.error(f"Paystack initiate_transfer error: {str(e)}")
            raise

# Global instance
paystack_service = PaystackService()
