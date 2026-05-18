# 🔧 Quick Modification Examples

This file shows practical examples of how to modify the 3 Pydantic models.

---

## Example 1: Add a New Field to Activities

**Scenario:** You discover a new field in the JSON: `deviceSerialNumber`

### Step 1: Add the field definition
```python
# In app/models/activities.py, in the SummarizedActivityModel class, add:

from typing import Optional

class SummarizedActivityModel(BaseModel):
    # ... existing fields ...
    
    deviceSerialNumber: Optional[str] = Field(
        default=None,
        description="Serial number of the device that recorded the activity",
        example="123ABC456"
    )
```

### Step 2: Add validation (if needed)
```python
@field_validator('deviceSerialNumber')
@classmethod
def validate_device_serial(cls, v):
    if v is not None and len(v) < 3:
        raise ValueError('deviceSerialNumber must be at least 3 characters')
    return v
```

### Step 3: Test it
```python
from app.models.activities import SummarizedActivityModel

test_data = {
    "activityId": 123,
    "activityType": {"typeId": 1, "typeKey": "cycling"},
    "startTimeInSeconds": 1715904000000,
    "distance": 5000,
    "duration": 3600,
    "deviceSerialNumber": "GarminWatch789"
}

activity = SummarizedActivityModel(**test_data)
print(activity.deviceSerialNumber)  # Output: GarminWatch789
```

---

## Example 2: Make a Field Optional in Sleep

**Scenario:** The field `averageRespiration` is sometimes missing in Garmin data

### Step 1: Find the field
```python
# In app/models/sleep.py, find:
averageRespiration: float = Field(...)
```

### Step 2: Make it optional
```python
# Change to:
averageRespiration: Optional[float] = Field(
    default=None,
    description="Average respiration rate during sleep (breaths per minute)",
    ge=0,
    le=100
)
```

### Step 3: Update the validator (if exists)
```python
# Before:
@field_validator('averageRespiration')
@classmethod
def validate_respiration(cls, v):
    if v < 0 or v > 100:
        raise ValueError('averageRespiration must be between 0 and 100')
    return v

# After:
@field_validator('averageRespiration')
@classmethod
def validate_respiration(cls, v):
    if v is not None and (v < 0 or v > 100):
        raise ValueError('averageRespiration must be between 0 and 100')
    return v
```

---

## Example 3: Add Validation to Records

**Scenario:** You want to validate that `value` is never 0 (since 0 isn't a real PR)

### Current code:
```python
value: float = Field(
    description="The personal record value",
    example=100.5
)
```

### Step 1: Add GT (greater than) constraint
```python
value: float = Field(
    description="The personal record value (must be > 0)",
    example=100.5,
    gt=0  # This is the constraint!
)
```

### OR Step 2: Use validator for complex logic
```python
@field_validator('value')
@classmethod
def validate_value(cls, v):
    if v <= 0:
        raise ValueError('PR value must be positive')
    if v > 999999:
        raise ValueError('PR value seems unrealistic')
    return v
```

---

## Example 4: Change Field Type in Activities

**Scenario:** You realize `calories` should be `Optional[float]` instead of `float` because some activities don't track it

### Before:
```python
calories: float = Field(
    description="Calories burned during activity",
    example=250.5
)
```

### After:
```python
calories: Optional[float] = Field(
    default=None,
    description="Calories burned during activity (if available)",
    example=250.5,
    ge=0  # Still >= 0 when present
)
```

### Update validator:
```python
@field_validator('calories')
@classmethod
def validate_calories(cls, v):
    if v is not None and v < 0:
        raise ValueError('calories cannot be negative')
    return v
```

---

## Example 5: Add a Computed Property

**Scenario:** You want a property that calculates total sleep in hours

### In app/models/sleep.py:
```python
class SleepDataModel(BaseModel):
    # ... existing fields ...
    deepSleepSeconds: int
    lightSleepSeconds: int
    remSleepSeconds: int
    awakeSleepSeconds: int
    
    # Add this property:
    @property
    def total_sleep_hours(self) -> float:
        """Calculate total sleep in hours"""
        total_seconds = (
            self.deepSleepSeconds + 
            self.lightSleepSeconds + 
            self.remSleepSeconds + 
            self.awakeSleepSeconds
        )
        return total_seconds / 3600

    @property
    def deep_sleep_percentage(self) -> float:
        """Calculate percentage of deep sleep"""
        total = self.total_sleep_hours
        if total == 0:
            return 0
        return (self.deepSleepSeconds / 3600) / total * 100
```

### Usage:
```python
sleep = SleepDataModel(**data)
print(f"Total sleep: {sleep.total_sleep_hours} hours")
print(f"Deep sleep: {sleep.deep_sleep_percentage:.1f}%")
```

---

## Example 6: Add Complex Validation

**Scenario:** In Activities, `distance` and `duration` should be reasonable

### Current:
```python
distance: float = Field(description="Distance in meters", example=5000, ge=0)
duration: int = Field(description="Duration in seconds", example=3600)
```

### Add comprehensive validator:
```python
@field_validator('distance', 'duration')
@classmethod
def validate_distance_duration(cls, v, info):
    # Get the field name
    field_name = info.field_name
    
    if field_name == 'distance':
        if v < 0:
            raise ValueError('distance cannot be negative')
        if v > 1000000:  # More than 1000 km
            raise ValueError('distance seems unrealistic')
    
    if field_name == 'duration':
        if v < 0:
            raise ValueError('duration cannot be negative')
        if v > 86400:  # More than 24 hours
            raise ValueError('duration seems unrealistic for single activity')
    
    return v
```

---

## Example 7: Add Alias for Field Name Variation

**Scenario:** Garmin sometimes uses `activityId` and sometimes `activity_id`

### Solution - use alias:
```python
activityId: int = Field(
    alias='activity_id',  # Accept both names in JSON
    description="Unique activity identifier",
    example=12345
)

# Tell Pydantic to populate by name AND alias
model_config = ConfigDict(
    populate_by_name=True,  # Accept both 'activityId' and 'activity_id'
    validate_default=True
)
```

### Usage:
```python
# Both work now:
activity1 = SummarizedActivityModel(activityId=123, ...)
activity2 = SummarizedActivityModel(activity_id=123, ...)  # Also works!
```

---

## Example 8: Add Field with Custom Validation

**Scenario:** `activityType` should only be certain values

### Find the field:
```python
activityType: Dict = Field(description="Activity type info")
```

### Add validation:
```python
VALID_ACTIVITY_TYPES = {
    'cycling', 'running', 'walking', 'swimming', 
    'hiking', 'skiing', 'golfing', 'tennis'
}

@field_validator('activityType')
@classmethod
def validate_activity_type(cls, v):
    if isinstance(v, dict) and 'typeKey' in v:
        if v['typeKey'] not in VALID_ACTIVITY_TYPES:
            raise ValueError(f"Invalid activity type: {v['typeKey']}")
    return v
```

---

## Workflow: How to Modify a Model

### 1. **Identify what to change**
   - New field? → Add to class
   - Change type? → Modify annotation
   - Add validation? → Add @field_validator
   - Make optional? → Use Optional[Type]

### 2. **Make the change** in the model file

### 3. **Add/update validator** if needed

### 4. **Test it:**
   ```python
   from app.models.activities import SummarizedActivityModel
   
   test_data = {...}
   model = SummarizedActivityModel(**test_data)
   print(model)
   ```

### 5. **Run tests:**
   ```bash
   cd /Users/sophieliu/Desktop/sophie/garmin\ insight\ RAG/garmin-rag-project
   pytest tests/ -v
   ```

---

## Common Patterns

### Pattern: Make Required Field Optional
```python
# Before
required_field: str = Field(description="...")

# After
optional_field: Optional[str] = Field(
    default=None,
    description="..."
)
```

### Pattern: Add Range Validation
```python
# Using Pydantic constraints
heart_rate: int = Field(ge=40, le=200, description="HR in bpm")

# OR using validator
@field_validator('heart_rate')
@classmethod
def validate_hr(cls, v):
    if not (40 <= v <= 200):
        raise ValueError('HR must be 40-200 bpm')
    return v
```

### Pattern: Add Multiple Fields
```python
# Don't do this one by one
# Do this all at once:

class MyModel(BaseModel):
    field1: int = Field(...)
    field2: str = Field(...)
    field3: Optional[float] = Field(...)
    
    @field_validator('field1', 'field2')
    @classmethod
    def validate_all(cls, v):
        # Shared validation
        return v
```

---

## 🚨 Common Mistakes to Avoid

### ❌ Mistake 1: Forgetting to import Optional
```python
# WRONG
optional_field: Optional[str]  # NameError!

# RIGHT
from typing import Optional
optional_field: Optional[str]
```

### ❌ Mistake 2: Forgetting to import Field
```python
# WRONG
field: str = Field(description="...")  # NameError!

# RIGHT
from pydantic import Field
field: str = Field(description="...")
```

### ❌ Mistake 3: Validator doesn't handle None
```python
# WRONG
@field_validator('optional_field')
@classmethod
def validate(cls, v):
    return v.upper()  # Crashes if v is None!

# RIGHT
@field_validator('optional_field')
@classmethod
def validate(cls, v):
    if v is None:
        return None
    return v.upper()
```

### ❌ Mistake 4: Modifying field without updating validator
```python
# Changed field to Optional but validator still expects non-None
@field_validator('status')
@classmethod
def validate_status(cls, v):
    if v not in ['active', 'inactive']:  # Crashes if v is None!
        raise ValueError(...)
    return v

# Fix: Check for None first
@field_validator('status')
@classmethod
def validate_status(cls, v):
    if v is None:
        return None
    if v not in ['active', 'inactive']:
        raise ValueError(...)
    return v
```

---

## 📚 Complete Modification Reference

For COMPLETE details on every field and validator in all 3 models, see:

```
app/models/MODIFICATION_GUIDE.md
```

This quick reference shows common patterns. The full guide has complete field lists.

---

✅ **Ready to modify your models!**
