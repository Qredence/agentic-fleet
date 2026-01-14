# Python Backend Anti-Patterns

Common anti-patterns found in Python backend code, especially in AI-generated code.

## Code Duplication

### Duplicate Validation Logic

**Anti-pattern:**

```python
# file1.py
def create_user(email: str):
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    # ...

# file2.py
def update_user(email: str):
    if not email or "@" not in email:
        raise ValueError("Invalid email")
    # ...
```

**Solution:** Extract to shared utility

```python
# utils/validation.py
def validate_email(email: str) -> None:
    if not email or "@" not in email:
        raise ValueError("Invalid email")

# file1.py, file2.py
from utils.validation import validate_email

def create_user(email: str):
    validate_email(email)
    # ...
```

### Recreated Utility Functions

**Anti-pattern:** Reimplementing common operations instead of importing

```python
# Recreating JSON serialization
def to_json(obj):
    return json.dumps(obj, indent=2)

def from_json(text):
    return json.loads(text)

# Recreating retry logic
def retry_request(url, max_attempts=3):
    for i in range(max_attempts):
        try:
            return requests.get(url)
        except Exception:
            if i == max_attempts - 1:
                raise
            time.sleep(2 ** i)
```

**Solution:** Use existing libraries

```python
import orjson  # or json
from tenacity import retry, stop_after_attempt, wait_exponential

# Use library directly
data = orjson.loads(text)

# Use decorator
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
def fetch_data(url):
    return requests.get(url)
```

## Over-Engineering

### Premature Abstraction

**Anti-pattern:** Creating abstractions before they're needed

```python
class DataProcessor:
    def process(self, data): pass

class UserDataProcessor(DataProcessor):
    def process(self, data):
        return data.upper()

class ProductDataProcessor(DataProcessor):
    def process(self, data):
        return data.lower()
```

**Solution:** Start simple, abstract when pattern emerges

```python
# Just functions until abstraction is justified
def process_user_data(data: str) -> str:
    return data.upper()

def process_product_data(data: str) -> str:
    return data.lower()
```

### Configuration Over-Engineering

**Anti-pattern:** Excessive configuration for simple cases

```python
class EmailSender:
    def __init__(
        self,
        host: str,
        port: int,
        use_tls: bool,
        timeout: int,
        retry_count: int,
        retry_delay: int,
        max_message_size: int,
        compression: bool,
        # ... 20 more parameters
    ):
        # ...
```

**Solution:** Use sensible defaults, allow overrides when needed

```python
from dataclasses import dataclass

@dataclass
class EmailConfig:
    host: str = "localhost"
    port: int = 587
    use_tls: bool = True
    timeout: int = 30
    # Only expose what users actually configure

class EmailSender:
    def __init__(self, config: EmailConfig | None = None):
        self.config = config or EmailConfig()
```

## God Objects

### God Class

**Anti-pattern:** One class doing too many things

```python
class UserManager:
    def create_user(self, ...): ...
    def update_user(self, ...): ...
    def delete_user(self, ...): ...
    def send_welcome_email(self, ...): ...
    def log_user_activity(self, ...): ...
    def validate_password(self, ...): ...
    def hash_password(self, ...): ...
    def generate_token(self, ...): ...
    def verify_token(self, ...): ...
    def check_permissions(self, ...): ...
    # ... 20 more methods
```

**Solution:** Split by responsibility

```python
class UserRepository:
    def create(self, user: User): ...
    def update(self, user: User): ...
    def delete(self, user_id: str): ...

class UserNotifier:
    def send_welcome_email(self, user: User): ...

class PasswordService:
    def validate(self, password: str): ...
    def hash(self, password: str): ...

class AuthService:
    def generate_token(self, user: User): ...
    def verify_token(self, token: str): ...
```

### God Function

**Anti-pattern:** One function doing everything

```python
def process_order(order_data):
    # Validate input (50 lines)
    # Query database (30 lines)
    # Calculate prices (40 lines)
    # Apply discounts (35 lines)
    # Process payment (45 lines)
    # Send notifications (25 lines)
    # Update inventory (30 lines)
    # Log everything (20 lines)
    # Return response (10 lines)
    # Total: 285 lines
```

**Solution:** Extract logical steps

```python
def process_order(order_data: OrderData) -> OrderResult:
    validated_order = validate_order(order_data)
    pricing = calculate_order_pricing(validated_order)
    payment_result = process_payment(pricing)

    if payment_result.success:
        update_inventory(validated_order)
        send_order_confirmation(validated_order, payment_result)

    return OrderResult(payment=payment_result, order=validated_order)
```

## Complexity Issues

### Deep Nesting

**Anti-pattern:** Too many nested levels

```python
def process_data(items):
    if items:
        for item in items:
            if item.is_valid:
                if item.category == "A":
                    if item.price > 100:
                        if item.in_stock:
                            # Actually do something
                            pass
```

**Solution:** Early returns and guard clauses

```python
def process_data(items):
    if not items:
        return

    for item in items:
        if not item.is_valid:
            continue
        if item.category != "A":
            continue
        if item.price <= 100:
            continue
        if not item.in_stock:
            continue

        # Actually do something (at top level)
        process_item(item)
```

### Complex Boolean Logic

**Anti-pattern:** Unreadable boolean expressions

```python
if (user.is_active and not user.is_deleted and user.email_verified and
    (user.role == "admin" or user.role == "moderator") and
    user.created_at < datetime.now() - timedelta(days=30)):
    # ...
```

**Solution:** Extract to named functions

```python
def is_established_staff_member(user: User) -> bool:
    return (
        user.is_active
        and not user.is_deleted
        and user.email_verified
        and user.role in ("admin", "moderator")
        and user.created_at < datetime.now() - timedelta(days=30)
    )

if is_established_staff_member(user):
    # ...
```

## Import Issues

### Wildcard Imports

**Anti-pattern:**

```python
from utils import *
from models import *
```

**Solution:** Explicit imports

```python
from utils import validate_email, format_date
from models import User, Product
```

### Circular Dependencies

**Anti-pattern:**

```python
# models.py
from services import UserService

class User:
    def validate(self):
        return UserService.validate(self)

# services.py
from models import User

class UserService:
    @staticmethod
    def validate(user: User):
        return user.email is not None
```

**Solution:** Reorganize or use TYPE_CHECKING

```python
# models.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services import UserService

class User:
    def validate(self) -> bool:
        from services import UserService  # Import at runtime
        return UserService.validate(self)
```

## Error Handling

### Bare Except

**Anti-pattern:** Catching all exceptions

```python
try:
    process_data()
except:  # Catches everything, including KeyboardInterrupt
    pass
```

**Solution:** Specific exceptions

```python
try:
    process_data()
except (ValueError, KeyError) as e:
    logger.error(f"Data processing error: {e}")
    raise
```

### Silent Failures

**Anti-pattern:** Hiding errors

```python
try:
    result = critical_operation()
except Exception:
    pass  # Error is lost
```

**Solution:** Log and handle appropriately

```python
try:
    result = critical_operation()
except Exception as e:
    logger.exception("Critical operation failed")
    # Either raise, return default, or handle explicitly
    raise
```

## Performance

### N+1 Queries

**Anti-pattern:** Repeated database queries in loops

```python
def get_users_with_orders():
    users = User.query.all()
    for user in users:
        user.orders = Order.query.filter_by(user_id=user.id).all()  # N queries
    return users
```

**Solution:** Eager loading or batch queries

```python
def get_users_with_orders():
    return User.query.options(
        joinedload(User.orders)
    ).all()  # 1-2 queries total
```

### Unnecessary Copies

**Anti-pattern:** Creating unnecessary data copies

```python
def process_large_list(items):
    new_items = items.copy()  # Unnecessary copy
    filtered = [x for x in new_items if x.is_valid]  # Another copy
    return sorted(filtered)  # Yet another copy
```

**Solution:** Process in-place or use generators

```python
def process_large_list(items):
    return sorted(
        (x for x in items if x.is_valid),
        key=lambda x: x.priority
    )
```
