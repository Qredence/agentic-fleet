# Refactoring Patterns

Practical refactoring strategies for improving Python backend code.

## Extract Function

When a code block is complex or reused, extract it into a named function.

**Before:**

```python
def generate_report(users):
    result = []
    for user in users:
        # Complex calculation (10 lines)
        score = 0
        for activity in user.activities:
            if activity.type == "login":
                score += 1
            elif activity.type == "purchase":
                score += 5
            elif activity.type == "review":
                score += 3
        user_data = {"name": user.name, "score": score}
        result.append(user_data)
    return result
```

**After:**

```python
def calculate_user_score(user: User) -> int:
    score = 0
    for activity in user.activities:
        if activity.type == "login":
            score += 1
        elif activity.type == "purchase":
            score += 5
        elif activity.type == "review":
            score += 3
    return score

def generate_report(users):
    return [
        {"name": user.name, "score": calculate_user_score(user)}
        for user in users
    ]
```

## Extract Variable

Replace complex expressions with well-named variables.

**Before:**

```python
if (user.created_at < datetime.now() - timedelta(days=30) and
    user.is_active and not user.is_deleted):
    # ...
```

**After:**

```python
is_established_user = user.created_at < datetime.now() - timedelta(days=30)
is_eligible = user.is_active and not user.is_deleted

if is_established_user and is_eligible:
    # ...
```

## Consolidate Duplicate Code

### Pattern: Extract Common Function

**Before:**

```python
# api/users.py
def create_user(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    # ...

# api/auth.py
def register(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    # ...

# api/profile.py
def update_email(data):
    if not data.get("email") or "@" not in data["email"]:
        raise ValueError("Invalid email")
    # ...
```

**After:**

```python
# utils/validation.py
def validate_email(email: str | None) -> None:
    if not email or "@" not in email:
        raise ValueError("Invalid email")

# api/users.py, api/auth.py, api/profile.py
from utils.validation import validate_email

def create_user(data):
    validate_email(data.get("email"))
    # ...
```

### Pattern: Use Inheritance or Composition

**Before:** Duplicate data processing logic

```python
class UserProcessor:
    def process(self, user):
        # Sanitize (10 lines)
        # Validate (15 lines)
        # Transform (20 lines)
        pass

class ProductProcessor:
    def process(self, product):
        # Sanitize (10 lines) - same as above
        # Validate (15 lines) - same as above
        # Transform (20 lines) - different
        pass
```

**After:** Extract common logic

```python
class BaseProcessor:
    def sanitize(self, data): ...
    def validate(self, data): ...

class UserProcessor(BaseProcessor):
    def process(self, user):
        self.sanitize(user)
        self.validate(user)
        self.transform_user(user)

    def transform_user(self, user): ...

class ProductProcessor(BaseProcessor):
    def process(self, product):
        self.sanitize(product)
        self.validate(product)
        self.transform_product(product)

    def transform_product(self, product): ...
```

## Simplify Conditional Logic

### Pattern: Guard Clauses

**Before:**

```python
def process_order(order):
    if order is not None:
        if order.is_valid():
            if order.total > 0:
                if order.customer.is_active:
                    # Process order (20 lines)
                    pass
                else:
                    return None
            else:
                return None
        else:
            return None
    else:
        return None
```

**After:**

```python
def process_order(order):
    if order is None:
        return None
    if not order.is_valid():
        return None
    if order.total <= 0:
        return None
    if not order.customer.is_active:
        return None

    # Process order (20 lines) - now at top level
    return process_valid_order(order)
```

### Pattern: Replace Conditional with Polymorphism

**Before:**

```python
def calculate_price(item_type, quantity, base_price):
    if item_type == "book":
        if quantity > 10:
            return base_price * quantity * 0.9
        return base_price * quantity
    elif item_type == "electronics":
        if quantity > 5:
            return base_price * quantity * 0.85
        return base_price * quantity * 0.95
    elif item_type == "clothing":
        return base_price * quantity * 0.8
```

**After:**

```python
from abc import ABC, abstractmethod

class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, quantity: int, base_price: float) -> float:
        pass

class BookPricing(PricingStrategy):
    def calculate(self, quantity: int, base_price: float) -> float:
        discount = 0.9 if quantity > 10 else 1.0
        return base_price * quantity * discount

class ElectronicsPricing(PricingStrategy):
    def calculate(self, quantity: int, base_price: float) -> float:
        discount = 0.85 if quantity > 5 else 0.95
        return base_price * quantity * discount

class ClothingPricing(PricingStrategy):
    def calculate(self, quantity: int, base_price: float) -> float:
        return base_price * quantity * 0.8

PRICING_STRATEGIES = {
    "book": BookPricing(),
    "electronics": ElectronicsPricing(),
    "clothing": ClothingPricing(),
}

def calculate_price(item_type: str, quantity: int, base_price: float) -> float:
    strategy = PRICING_STRATEGIES.get(item_type)
    if not strategy:
        raise ValueError(f"Unknown item type: {item_type}")
    return strategy.calculate(quantity, base_price)
```

## Break Up God Classes

### Pattern: Extract Related Methods

**Before:**

```python
class UserManager:
    def create_user(self, ...): ...
    def update_user(self, ...): ...
    def delete_user(self, ...): ...
    def hash_password(self, ...): ...
    def verify_password(self, ...): ...
    def send_email(self, ...): ...
    def log_activity(self, ...): ...
    # 20 more methods
```

**After:**

```python
class UserRepository:
    """Data access for users."""
    def create(self, user: User): ...
    def update(self, user: User): ...
    def delete(self, user_id: str): ...
    def find_by_id(self, user_id: str): ...

class PasswordService:
    """Password hashing and verification."""
    def hash(self, password: str): ...
    def verify(self, password: str, hashed: str): ...

class UserNotifier:
    """User notifications."""
    def send_welcome_email(self, user: User): ...
    def send_reset_email(self, user: User): ...

class ActivityLogger:
    """User activity logging."""
    def log_login(self, user: User): ...
    def log_action(self, user: User, action: str): ...
```

## Reduce Complexity

### Pattern: Extract Nested Logic

**Before:**

```python
async def process_users(user_ids):
    results = []
    for user_id in user_ids:
        user = await db.get_user(user_id)
        if user:
            if user.is_active:
                orders = await db.get_orders(user_id)
                if orders:
                    total = sum(o.amount for o in orders)
                    if total > 1000:
                        results.append({
                            "user_id": user_id,
                            "total": total,
                            "status": "vip"
                        })
    return results
```

**After:**

```python
async def is_vip_user(user_id: str) -> tuple[bool, float]:
    user = await db.get_user(user_id)
    if not user or not user.is_active:
        return False, 0

    orders = await db.get_orders(user_id)
    if not orders:
        return False, 0

    total = sum(o.amount for o in orders)
    return total > 1000, total

async def process_users(user_ids):
    results = []
    for user_id in user_ids:
        is_vip, total = await is_vip_user(user_id)
        if is_vip:
            results.append({
                "user_id": user_id,
                "total": total,
                "status": "vip"
            })
    return results
```

### Pattern: Replace Loop with Comprehension

**Before:**

```python
def get_active_user_emails(users):
    result = []
    for user in users:
        if user.is_active:
            if user.email:
                result.append(user.email)
    return result
```

**After:**

```python
def get_active_user_emails(users):
    return [
        user.email
        for user in users
        if user.is_active and user.email
    ]
```

## Improve Import Organization

### Pattern: Group and Sort Imports

**Before:**

```python
from myapp.utils import helper
import sys
from typing import List
import os
from myapp.models import User
import json
```

**After:**

```python
# Standard library
import json
import os
import sys
from typing import List

# Local imports
from myapp.models import User
from myapp.utils import helper
```

### Pattern: Replace Wildcard Imports

**Before:**

```python
from utils import *
from models import *

# Which module does User come from?
user = User()
```

**After:**

```python
from utils import validate_email, format_date
from models import User, Product

user = User()  # Clear origin
```

## Refactoring Workflow

1. **Ensure tests exist** - Before refactoring, write tests if they don't exist
2. **Make small changes** - Refactor incrementally, not all at once
3. **Run tests frequently** - After each small change, verify nothing broke
4. **Commit often** - Commit after each successful refactoring step
5. **Use tools** - Leverage IDE refactoring tools when available

## When to Refactor

✅ **DO refactor when:**

- Adding a new feature that reveals code smells
- Fixing a bug caused by unclear code
- Code review identifies issues
- You find yourself copy-pasting code

❌ **DON'T refactor when:**

- You're close to a deadline
- Tests don't exist and are hard to add
- The code works and won't be modified again
- Refactoring would break public APIs

## Refactoring Checklist

- [ ] Tests pass before refactoring
- [ ] Make one small change at a time
- [ ] Tests still pass after refactoring
- [ ] Code is more readable than before
- [ ] No functionality changed
- [ ] Performance is the same or better
- [ ] All imports still resolve correctly
- [ ] Type hints are accurate
