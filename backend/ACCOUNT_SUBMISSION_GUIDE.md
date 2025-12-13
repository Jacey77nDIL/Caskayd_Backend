# Creator Account Submission Endpoint

## Quick Setup

The endpoint has been added to your `main.py`. No additional configuration needed!

## Endpoint Details

**URL:** `POST /creator/submit-account`

**Authentication:** Required (Bearer token)

**Purpose:** Creators submit their bank account details to receive payments

## How to Use

### 1. Get List of Banks (Optional)

```bash
curl -X GET http://localhost:8000/api/payouts/banks
```

### 2. Submit Account Details

```bash
curl -X POST http://localhost:8000/creator/submit-account \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_number": "1234567890",
    "bank_code": "011"
  }'
```

## Request Body

```json
{
  "account_number": "1234567890",
  "bank_code": "011"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `account_number` | string | Yes | 10-digit bank account number |
| `bank_code` | string | Yes | Bank code (e.g., "011" for First Bank) |

## Response (Success)

**Status Code:** `200`

```json
{
  "id": 1,
  "account_number": "1234567890",
  "account_name": "John Doe",
  "bank_name": "First Bank",
  "bank_code": "011",
  "currency": "NGN"
}
```

## Response (Errors)

### Invalid Account Number
**Status Code:** `400`
```json
{
  "detail": "Account number must be 10 digits"
}
```

### Invalid Account
**Status Code:** `400`
```json
{
  "detail": "Invalid account number or bank code"
}
```

### Not a Creator
**Status Code:** `403`
```json
{
  "detail": "Only creators can submit payment accounts"
}
```

### Unauthorized
**Status Code:** `401`
```json
{
  "detail": "Not authenticated"
}
```

## Features

✅ **Automatic Validation** - Validates account with Paystack API
✅ **Account Name Lookup** - Gets account name from bank
✅ **Transfer Recipient Creation** - Sets up Paystack recipient automatically
✅ **Database Saving** - Stores account in database
✅ **Update Support** - Updates if account already exists
✅ **Error Handling** - Clear error messages

## What It Does

1. Validates the JWT token (ensures creator is logged in)
2. Checks user is a creator (not business)
3. Validates account number is 10 digits
4. Calls Paystack API to validate account and get account name
5. Creates a transfer recipient on Paystack
6. Saves account details to database
7. Returns the saved account details

## Database Storage

The account details are saved in the `bank_accounts` table with columns:
- `user_id` - Creator's ID
- `account_number` - Bank account number
- `account_name` - Account holder name
- `bank_code` - Bank code
- `bank_name` - Bank name
- `recipient_code` - Paystack recipient code
- `currency` - Currency (default: NGN)

## Testing with Postman

1. **Get Token:**
   - Method: POST
   - URL: `http://localhost:8000/login`
   - Body: `{ "email": "creator@example.com", "password": "password" }`

2. **Submit Account:**
   - Method: POST
   - URL: `http://localhost:8000/creator/submit-account`
   - Header: `Authorization: Bearer <token>`
   - Body: `{ "account_number": "1234567890", "bank_code": "011" }`

## JavaScript/Fetch Example

```javascript
const token = localStorage.getItem('token');

const response = await fetch('http://localhost:8000/creator/submit-account', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    account_number: '1234567890',
    bank_code: '011'
  })
});

const data = await response.json();
if (response.ok) {
  console.log('Account saved:', data);
} else {
  console.error('Error:', data.detail);
}
```

## Frontend Form Example (React)

```jsx
import { useState } from 'react';

export function SubmitAccountForm() {
  const [accountNumber, setAccountNumber] = useState('');
  const [bankCode, setBankCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('/creator/submit-account', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          account_number: accountNumber,
          bank_code: bankCode
        })
      });

      const data = await response.json();
      
      if (response.ok) {
        setMessage('Account saved successfully!');
        console.log('Saved account:', data);
      } else {
        setMessage(`Error: ${data.detail}`);
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Account Number (10 digits)"
        value={accountNumber}
        onChange={(e) => setAccountNumber(e.target.value)}
        maxLength="10"
        required
      />
      <input
        type="text"
        placeholder="Bank Code"
        value={bankCode}
        onChange={(e) => setBankCode(e.target.value)}
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Submitting...' : 'Submit Account'}
      </button>
      {message && <p>{message}</p>}
    </form>
  );
}
```

## Bank Codes (Nigeria)

Common bank codes:
- `011` - First Bank
- `033` - Guaranty Trust Bank
- `050` - Ecobank
- `044` - Access Bank
- `076` - Zenith Bank
- `058` - Guaranty Trust Bank (GTCO)
- `102` - Keystone Bank
- `064` - United Bank for Africa

Get full list:
```bash
curl http://localhost:8000/api/payouts/banks
```

## Notes

- Account number must be exactly 10 digits
- Bank code must be valid and active on Paystack
- Each creator can have only one bank account (updates if exists)
- Paystack API must be configured with valid credentials
- Token must be valid JWT from creator login

## What Happens Next?

After account submission, the creator can:
1. Receive payments from businesses
2. Request payouts using the saved account
3. Update account details by submitting again
4. View payment history and payout status

---

Created: December 13, 2025
