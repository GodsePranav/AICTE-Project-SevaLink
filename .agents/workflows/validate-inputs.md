---
description: Validate all input fields and labels after every prompt
---

## Post-Prompt Validation Checklist

After completing any code change, run through this checklist:

### 1. Label Standards
- All field labels should use industry-standard naming (e.g., "Username" not "Unique Username")
- Labels should be concise, professional, and match what users expect
- Required fields should have a red asterisk `*`

### 2. Input Validation Rules
For every input field, ensure:

**Text Fields:**
- Min/max length constraints
- No leading/trailing whitespace accepted
- Appropriate placeholder text

**Email:**
- Accept all valid email formats/domains (not just @gmail.com)
- Validate format with regex
- Check uniqueness

**Phone Number:**
- Exactly 10 digits
- Only numeric input
- Pattern validation on frontend + backend

**Aadhaar Number:**
- Exactly 12 digits
- Only numeric input
- Luhn check if applicable

**Full Name:**
- Minimum 2 words (first + last name)
- Only letters and spaces
- No special characters or numbers

**Date Fields:**
- Post Job scheduled date: must be current or future only
- Date of Birth: must be in the past, user must be 14+ years old

**Password:**
- Minimum 8 characters
- Django's built-in validators apply

**Budget/Price:**
- Non-negative numbers only
- Reasonable max limit

**Dropdowns/Selects:**
- Must have a valid selection (not the placeholder)

### 3. Frontend Validation
- HTML5 attributes: `required`, `pattern`, `min`, `max`, `minlength`, `maxlength`
- `type` attributes: `email`, `tel`, `number`, `date`, `datetime-local`
- JavaScript real-time validation with error messages

### 4. Backend Validation
- Django form `clean_*` methods for each field
- Proper error messages returned to template
- Sanitize all inputs
