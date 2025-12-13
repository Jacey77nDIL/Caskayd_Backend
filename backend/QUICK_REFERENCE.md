# Payment Account Form - Quick Reference

## 🚀 Quick Start (30 seconds)

### Backend
```python
# 1. Add to main.py
from payment_account_form import router as payment_account_router
app.include_router(payment_account_router)

# 2. Run migrations
alembic upgrade head
```

### Frontend (Choose One)

**React:**
```jsx
import PaymentAccountForm from './PaymentAccountForm'

export default () => <PaymentAccountForm />
```

**Vue:**
```vue
<template>
  <PaymentAccountForm />
</template>

<script setup>
import PaymentAccountForm from './PaymentAccountForm.vue'
</script>
```

**HTML:**
```html
<!-- Open payment_account_form.html in browser -->
```

---

## 📋 API Reference

### Get Setup Status
```bash
GET /api/payment-account/setup-status
Authorization: Bearer {token}

Response: { is_setup_complete: boolean, account_details?: {...} }
```

### List Banks
```bash
GET /api/payment-account/banks

Response: [{ name: string, code: string, active: boolean }, ...]
```

### Validate Account
```bash
POST /api/payment-account/validate-account?account_number=1234567890&bank_code=011
Authorization: Bearer {token}

Response: { valid: boolean, account_name: string, ... }
```

### Setup Account
```bash
POST /api/payment-account/setup
Authorization: Bearer {token}
Content-Type: application/json

Body: {
  "account_number": "1234567890",
  "bank_code": "011"
}

Response: { id, account_number, account_name, bank_name, bank_code, currency }
```

### Get Account
```bash
GET /api/payment-account/account
Authorization: Bearer {token}

Response: { id, account_number, account_name, bank_name, bank_code, currency }
```

### Delete Account
```bash
DELETE /api/payment-account/account
Authorization: Bearer {token}

Response: { message: "Account deleted successfully" }
```

---

## 🎨 Styling Customization

### React Colors
```jsx
// Replace in PaymentAccountForm.tsx
#4CAF50 → Primary green (buttons)
#f44336 → Danger red (delete)
#757575 → Secondary gray
```

### Vue Colors
```vue
<style scoped>
:root {
  --primary: #4CAF50;
  --danger: #f44336;
  --secondary: #757575;
}
</style>
```

---

## ⚠️ Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **404 - Endpoints not found** | Routes not included in main.py | Add `app.include_router(payment_account_router)` |
| **401 - Unauthorized** | Missing/invalid JWT token | Login and include valid token in header |
| **Account validation fails** | Invalid bank details | Verify account number (10 digits) and bank code |
| **CORS error** | Frontend URL not allowed | Update CORS origins in main.py |
| **Banks list empty** | Paystack API unreachable | Check Paystack API credentials |

---

## 📁 File Locations

```
backend/
├── payment_account_form.py          ← Backend routes
├── PaymentAccountForm.tsx           ← React component
├── PaymentAccountForm.vue           ← Vue component
├── payment_account_form.html        ← Standalone HTML
├── PAYMENT_FORM_GUIDE.md           ← Full documentation
└── README_PAYMENT_FORM.md          ← Overview
```

---

## 🔐 Security Features

✅ JWT authentication required
✅ Creator-only access
✅ Paystack account validation
✅ Server-side input validation
✅ SQL injection protection
✅ CORS validation

---

## 📊 Form States

```
Empty State
    ↓
Selecting Bank + Account Number
    ↓
Validating Account
    ↓
Account Verified
    ↓
Account Saved
    ↓
Account Summary View (Edit/Delete options)
```

---

## 🧪 Test with cURL

```bash
# 1. Get available banks
curl http://localhost:8000/api/payment-account/banks

# 2. Validate account
curl -X POST \
  'http://localhost:8000/api/payment-account/validate-account?account_number=0690000031&bank_code=011' \
  -H 'Authorization: Bearer your_token_here'

# 3. Setup account
curl -X POST http://localhost:8000/api/payment-account/setup \
  -H 'Authorization: Bearer your_token_here' \
  -H 'Content-Type: application/json' \
  -d '{
    "account_number": "0690000031",
    "bank_code": "011"
  }'

# 4. Get current account
curl http://localhost:8000/api/payment-account/account \
  -H 'Authorization: Bearer your_token_here'

# 5. Delete account
curl -X DELETE http://localhost:8000/api/payment-account/account \
  -H 'Authorization: Bearer your_token_here'
```

---

## 🎯 Form Field Validation

| Field | Type | Validation |
|-------|------|-----------|
| Bank Code | Select | Required, must exist in bank list |
| Account Number | Text | Required, 10 digits, numeric |
| Account Name | Display | Auto-populated from Paystack |

---

## 📱 Responsive Breakpoints

- **Desktop**: Full layout (600px+)
- **Tablet**: Single column (600px - 1200px)
- **Mobile**: Optimized layout (<600px)

---

## 🔄 Database Integration

### Existing Models Used
- `UserCreator` - creator users
- `BankAccount` - payment accounts
- `Payout` - payout transactions

### Existing Schemas Used
- `BankAccountCreate`
- `BankAccountResponse`
- `BankListResponse`

---

## 🛠️ Troubleshooting Checklist

- [ ] Backend routes added to main.py?
- [ ] Database migrations run? (`alembic upgrade head`)
- [ ] JWT token valid and included in requests?
- [ ] User is logged in as creator (not business)?
- [ ] Paystack API credentials configured?
- [ ] CORS allows frontend origin?
- [ ] Account number is exactly 10 digits?
- [ ] Bank code is valid and in active banks list?

---

## 📚 Resources

| Resource | Link |
|----------|------|
| Paystack API Docs | https://paystack.com/docs |
| FastAPI Docs | https://fastapi.tiangolo.com |
| React Docs | https://react.dev |
| Vue Docs | https://vuejs.org |
| Full Guide | See PAYMENT_FORM_GUIDE.md |

---

## ✅ Pre-Deployment Checklist

- [ ] All endpoints return correct status codes
- [ ] Error messages are user-friendly
- [ ] Form validates before submission
- [ ] Mobile responsive on all devices
- [ ] Loading states work correctly
- [ ] Token refresh handled properly
- [ ] Paystack API credentials set
- [ ] Database backups configured
- [ ] CORS properly configured
- [ ] Rate limiting configured (if needed)

---

## 🚀 After Integration

1. Test all form flows end-to-end
2. Test with real Paystack accounts
3. Test on mobile devices
4. Test error scenarios
5. Monitor API logs
6. Set up payment notifications
7. Create admin dashboard to view accounts
8. Schedule payout processing

---

**Last Updated:** December 13, 2025
**Status:** Ready for Use
**Support:** See full guide for detailed help
