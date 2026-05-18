"""
═══════════════════════════════════════════════════════════════════════════════
  GARMIN PYDANTIC MODELS - MODIFICATION & EXTENSION GUIDE
  
  Task 2: 3 Pydantic Models for Garmin Data
  Created: 2026-04-18
  Location: app/models/
    - activities.py (SummarizedActivityModel)
    - sleep.py (SleepDataModel)  
    - records.py (PersonalRecordModel)
═══════════════════════════════════════════════════════════════════════════════
"""

# ─────────────────────────────────────────────────────────────────────────────
# 📋 TABLE OF CONTENTS
# ─────────────────────────────────────────────────────────────────────────────
# 1. QUICK REFERENCE
# 2. HOW TO ADD A NEW FIELD
# 3. HOW TO ADD A VALIDATOR
# 4. HOW TO ADD A HELPER METHOD
# 5. HOW TO CHANGE FIELD TYPES
# 6. PYDANTIC V2 PATTERNS USED
# 7. COMMON MODIFICATION SCENARIOS
# 8. TESTING YOUR MODIFICATIONS


# ═════════════════════════════════════════════════════════════════════════════
# 1. QUICK REFERENCE
# ═════════════════════════════════════════════════════════════════════════════

"""
MODEL STRUCTURE (all 3 models follow same pattern):

    class ModelName(BaseModel):
        '''Docstring'''
        
        # ===== CORE FIELDS =====
        field1: type = Field(..., description="...")
        
        # ===== VALIDATORS =====
        @field_validator('field1')
        @classmethod
        def validate_field1(cls, v):
            # Validation logic
            return v
        
        # ===== HELPER METHODS =====
        def helper_method(self):
            # Logic
            return result
        
        model_config = ConfigDict(...)


KEY IMPORTS USED:
    from typing import Optional, List, Dict, Any
    from pydantic import BaseModel, Field, field_validator, ConfigDict
    from datetime import datetime


FIELD() PARAMETERS:
    Field(
        ...,                              # Required (use ...) or default value
        description="Human description",  # For documentation
        example="sample value",           # UI/API docs example
        gt=0,                             # Greater than (validation)
        ge=0,                             # Greater than or equal
        lt=100,                           # Less than
        le=100,                           # Less than or equal
        min_length=1,                     # String/list minimum length
        max_length=255,                   # String/list maximum length
        pattern=r'regex',                 # Regex validation
    )


COMMON VALIDATORS:
    @field_validator('field_name')                    # Single field
    @field_validator('field1', 'field2', 'field3')   # Multiple fields
    @field_validator('*')                             # All fields
    @field_validator('field', mode='before')          # Before conversion
    @field_validator('field', mode='after')           # After conversion (default)
    
    def validate_field(cls, v: type, info) -> type:   # info = validation context
        if condition:
            raise ValueError('Error message')
        return v
"""


# ═════════════════════════════════════════════════════════════════════════════
# 2. HOW TO ADD A NEW FIELD
# ═════════════════════════════════════════════════════════════════════════════

"""
SCENARIO 1: Add a required field (no default value)
──────────────────────────────────────────────────────

Where: In model class, in appropriate section (e.g., # ===== HEALTH METRICS =====)

    from typing import Optional
    from pydantic import BaseModel, Field
    
    class SummarizedActivityModel(BaseModel):
        # ... existing fields ...
        
        # ===== NEW SECTION =====
        new_field: int = Field(
            ...,  # Means required
            description="What this field represents",
            example=123,
            gt=0  # Greater than 0 validation
        )

Then add to model_config if needed, and optionally add validator.


SCENARIO 2: Add an optional field with default value
─────────────────────────────────────────────────────

    class SummarizedActivityModel(BaseModel):
        # ... existing fields ...
        
        optional_field: Optional[str] = Field(
            default=None,  # Optional with None default
            description="Description here",
            example="example"
        )

Or with non-None default:

    optional_field: bool = Field(
        default=False,  # Non-None default
        description="Description"
    )


SCENARIO 3: Add field with validation constraints
──────────────────────────────────────────────────

    temperature: float = Field(
        ...,
        description="Temperature in Celsius",
        ge=-50.0,  # Greater than or equal
        le=50.0,   # Less than or equal
        example=25.5
    )

Or using regex pattern:

    email: str = Field(
        ...,
        description="Email address",
        pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

Or using constraints in validator (more complex):

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v


SCENARIO 4: Add nested model as field
──────────────────────────────────────

First define nested model:

    class LocationInfo(BaseModel):
        latitude: float
        longitude: float
        altitude: float = Field(default=0)

Then use in parent model:

    from app.models.locations import LocationInfo
    
    class SummarizedActivityModel(BaseModel):
        # ... existing fields ...
        
        location: Optional[LocationInfo] = Field(
            default=None,
            description="Activity location"
        )

Usage: model.location.latitude


SCENARIO 5: Add List or Dict fields
────────────────────────────────────

    from typing import List, Dict
    
    class Model(BaseModel):
        tags: List[str] = Field(
            default_factory=list,  # Important! for mutable defaults
            description="List of tags"
        )
        
        metadata: Dict[str, Any] = Field(
            default_factory=dict,
            description="Key-value metadata"
        )
        
        # With validation:
        tags_validated: List[str] = Field(
            ...,
            min_length=1,      # At least 1 item
            max_length=10      # At most 10 items
        )
"""


# ═════════════════════════════════════════════════════════════════════════════
# 3. HOW TO ADD A VALIDATOR
# ═════════════════════════════════════════════════════════════════════════════

"""
BASIC VALIDATOR PATTERN:
────────────────────────

    @field_validator('field_name')
    @classmethod
    def validate_field_name(cls, v: type) -> type:
        '''
        Description of what this validates
        
        Logic: Explanation of validation rules
        Modify: How to change the validation
        '''
        if condition:
            raise ValueError('Error message')
        return v


EXAMPLE 1: Simple range validation
──────────────────────────────────

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        '''Age must be 0-150 years'''
        if v < 0 or v > 150:
            raise ValueError('Age must be between 0 and 150')
        return v

To modify: Change the 0 and 150 limits.


EXAMPLE 2: Conditional validation (depends on other fields)
───────────────────────────────────────────────────────────

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        '''End time must be after start time'''
        if 'start_time' in info.data:
            if v <= info.data['start_time']:
                raise ValueError('End time must be after start time')
        return v

To modify: Access other fields via info.data['field_name']


EXAMPLE 3: Validator for multiple fields
─────────────────────────────────────────

    @field_validator('temperature', 'humidity', 'pressure')
    @classmethod
    def validate_positive(cls, v: float) -> float:
        '''All weather metrics must be positive'''
        if v < 0:
            raise ValueError('Value must be positive')
        return v

To modify: Add/remove field names in decorator


EXAMPLE 4: Validator with mode='before' (pre-parsing)
──────────────────────────────────────────────────────

    @field_validator('date_string', mode='before')
    @classmethod
    def normalize_date(cls, v: str) -> str:
        '''Normalize date format before parsing'''
        if isinstance(v, datetime):
            return v.isoformat()
        return v.strip()

Common use: Normalize string input before conversion


EXAMPLE 5: Conditional error message
─────────────────────────────────────

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        '''Score must be between 0 and 100'''
        if v < 0:
            raise ValueError('Score cannot be negative')
        elif v > 100:
            raise ValueError('Score cannot exceed 100 (got {})'.format(v))
        elif v > 90:
            # Warning but still valid (could log warning here)
            pass
        return v


EXAMPLE 6: Cross-field validation
──────────────────────────────────

Create root_validator (validates whole model):

    from pydantic import model_validator
    
    class ActivityModel(BaseModel):
        distance: float
        duration: int
        
        @model_validator(mode='after')
        def check_distance_duration_ratio(self):
            '''Ensure reasonable speed'''
            if self.distance > 0 and self.duration > 0:
                avg_speed = self.distance / (self.duration / 3600)
                if avg_speed > 200:  # km/h
                    raise ValueError('Implied speed too high')
            return self


WHERE TO ADD VALIDATORS:
────────────────────────
Place them after all Field definitions and before helper methods.
Organize by field/concern:

    # ===== FIELD VALIDATORS =====
    
    @field_validator('field1')
    def validate_field1(cls, v): ...
    
    @field_validator('field2')
    def validate_field2(cls, v): ...
    
    # Cross-field validation
    @model_validator(mode='after')
    def check_field_relationships(self): ...
"""


# ═════════════════════════════════════════════════════════════════════════════
# 4. HOW TO ADD A HELPER METHOD
# ═════════════════════════════════════════════════════════════════════════════

"""
HELPER METHOD BASICS:
─────────────────────

    class Model(BaseModel):
        # Fields
        field1: int
        field2: float
        
        # Helper methods (after validators)
        def helper_method(self) -> return_type:
            '''Description'''
            # Logic using self.field1, self.field2, etc.
            return result


EXAMPLE 1: Simple calculation helper
────────────────────────────────────

    class ActivityModel(BaseModel):
        distance: int  # meters
        duration: int  # seconds
        
        def get_average_speed_kmh(self) -> float:
            '''Calculate average speed in km/h'''
            if self.duration == 0:
                return 0.0
            speed_ms = self.distance / self.duration
            speed_kmh = speed_ms * 3.6
            return round(speed_kmh, 2)

Usage: activity.get_average_speed_kmh()


EXAMPLE 2: Using datetime helpers
──────────────────────────────────

    from datetime import datetime
    
    class SleepModel(BaseModel):
        calendar_date: str  # "2024-05-15"
        
        def get_date_object(self) -> datetime:
            '''Parse date string to datetime'''
            return datetime.strptime(self.calendar_date, '%Y-%m-%d')
        
        def get_days_ago(self) -> int:
            '''How many days ago was this?'''
            date_obj = self.get_date_object()
            age = datetime.now() - date_obj
            return age.days

Usage: sleep.get_days_ago()


EXAMPLE 3: Property decorator (access like attribute)
──────────────────────────────────────────────────────

    from functools import cached_property
    
    class ActivityModel(BaseModel):
        distance: int
        duration: int
        calories: int
        
        @property
        def duration_minutes(self) -> float:
            '''Access as: activity.duration_minutes (not method)'''
            return self.duration / 60
        
        @cached_property  # Computed once then cached
        def efficiency_score(self) -> float:
            '''Calories per minute'''
            if self.duration_minutes == 0:
                return 0.0
            return self.calories / self.duration_minutes

Usage: activity.duration_minutes  # No () needed


EXAMPLE 4: Conversion to other format
──────────────────────────────────────

    class ActivityModel(BaseModel):
        # Fields...
        
        def to_dict_for_chunking(self) -> dict:
            '''Convert to human-readable format for embedding'''
            return {
                "type": self.activity_type,
                "duration_hours": round(self.duration / 3600, 2),
                "distance_km": round(self.distance / 1000, 2),
                "calories": self.calories,
            }
        
        def to_summary(self) -> str:
            '''Convert to readable text summary'''
            return (
                f"{self.activity_type}: "
                f"{self.distance/1000:.1f}km in "
                f"{self.duration/3600:.1f}h"
            )

Usage in Task 9: activity.to_dict_for_chunking()


EXAMPLE 5: Method with parameters
──────────────────────────────────

    class ActivityModel(BaseModel):
        calories: int
        
        def get_calories_in_unit(self, unit: str) -> float:
            '''Convert calories to different units'''
            conversions = {
                'kcal': 1.0,
                'kJ': self.calories * 4.184,
                'cal': self.calories * 1000,
            }
            return conversions.get(unit, self.calories)

Usage: activity.get_calories_in_unit('kJ')


EXAMPLE 6: Validation in method (manual checking)
──────────────────────────────────────────────────

    class ActivityModel(BaseModel):
        distance: int
        avg_speed: float
        max_speed: float
        
        def validate_speed_consistency(self) -> bool:
            '''Check if avg <= max (shouldn't fail but can verify)'''
            if self.avg_speed > self.max_speed:
                raise ValueError(
                    f'Average speed ({self.avg_speed}) '
                    f'exceeds max speed ({self.max_speed})'
                )
            return True
"""


# ═════════════════════════════════════════════════════════════════════════════
# 5. HOW TO CHANGE FIELD TYPES
# ═════════════════════════════════════════════════════════════════════════════

"""
COMMON TYPE CONVERSIONS:
────────────────────────

Old Code:
    field: int = Field(...)

Change to String:
    field: str = Field(..., min_length=1)

Change to Float:
    field: float = Field(..., ge=0.0)

Make Optional:
    field: Optional[str] = Field(default=None, ...)

Change from Optional to Required:
    OLD: field: Optional[int] = Field(default=None)
    NEW: field: int = Field(..., ge=0)
         ^ Add ... to make required

Add List:
    OLD: field: str = Field(...)
    NEW: field: List[str] = Field(default_factory=list)

Change Dict type:
    OLD: metadata: Dict[str, Any] = Field(default_factory=dict)
    NEW: metadata: Dict[str, int] = Field(default_factory=dict)


EXAMPLE: Changing timestamp field type
──────────────────────────────────────

Currently: start_time_in_seconds: int  # milliseconds

Change to datetime:
    1. Update field type:
        start_time: datetime = Field(
            ...,
            description="Start time as datetime object"
        )
    
    2. Update validator:
        @field_validator('start_time', mode='before')
        @classmethod
        def parse_start_time(cls, v):
            if isinstance(v, int):
                return datetime.fromtimestamp(v / 1000)
            return v
    
    3. Update any helpers that use this field


EXAMPLE: Changing from string to enum
──────────────────────────────────────

From: activity_type: str = Field(...)

To enum (strict choices):
    from enum import Enum
    
    class ActivityType(str, Enum):
        CYCLING = "cycling"
        RUNNING = "running"
        SWIMMING = "swimming"
    
    # In model:
    activity_type: ActivityType = Field(...)

Validation happens automatically!
"""


# ═════════════════════════════════════════════════════════════════════════════
# 6. PYDANTIC V2 PATTERNS USED
# ═════════════════════════════════════════════════════════════════════════════

"""
KEY DIFFERENCES FROM V1:
────────────────────────

V1 Pattern:                          V2 Pattern:
────────────────────────────────────────────────────────────────
class Config:                        model_config = ConfigDict(
    validate_assignment = True           validate_assignment=True
                                     )

@validator('field')                  @field_validator('field')
def val(cls, v):                     def val(cls, v):
    return v                             return v

.dict()                              .model_dump()

.json()                              .model_dump_json()

.schema()                            .model_json_schema()

from pydantic import validator       from pydantic import field_validator

parse_obj()                          model_validate()

.copy()                              .model_copy()


ConfigDict COMMON OPTIONS:
──────────────────────────

model_config = ConfigDict(
    validate_default=True,           # Validate default values
    use_attribute_docstrings=True,   # Use field docstrings
    str_strip_whitespace=True,       # Auto-strip whitespace
    validate_assignment=True,        # Validate when assigning to field
    from_attributes=True,            # Allow ORM mode (SQLModel)
    populate_by_name=True,           # Allow both field_name and fieldName
)
"""


# ═════════════════════════════════════════════════════════════════════════════
# 7. COMMON MODIFICATION SCENARIOS
# ═════════════════════════════════════════════════════════════════════════════

"""
SCENARIO 1: Make a required field optional
───────────────────────────────────────────

Before:
    heart_rate: int = Field(..., description="HR in bpm")

After:
    heart_rate: Optional[int] = Field(
        default=None,
        description="HR in bpm (optional)"
    )

Update validator if exists:
    @field_validator('heart_rate', mode='before')
    @classmethod
    def validate_heart_rate(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None  # ← Add this!
        if v < 0 or v > 250:
            raise ValueError('Invalid HR')
        return v


SCENARIO 2: Add a new constraint to existing field
──────────────────────────────────────────────────

Before:
    age: int = Field(...)

After (add constraint):
    age: int = Field(..., ge=0, le=150)

Or add validator:
    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 0 or v > 150:
            raise ValueError('Age must be 0-150')
        return v


SCENARIO 3: Create a subset/view model
───────────────────────────────────────

Garmin data might be huge, but API only needs certain fields:

    from app.models.activities import SummarizedActivityModel
    
    class ActivitySummaryModel(BaseModel):
        '''Smaller version for API responses'''
        activity_type: str
        distance_km: float
        duration_hours: float
        calories: int
        
        @staticmethod
        def from_full_model(activity: SummarizedActivityModel) -> 'ActivitySummaryModel':
            return ActivitySummaryModel(
                activity_type=activity.activity_type,
                distance_km=activity.distance / 1000,
                duration_hours=activity.duration / 3600,
                calories=activity.calories,
            )

Usage in API:
    full_activity = SummarizedActivityModel(...)
    api_response = ActivitySummaryModel.from_full_model(full_activity)


SCENARIO 4: Add computed field from existing fields
────────────────────────────────────────────────────

    from pydantic import computed_field
    
    class ActivityModel(BaseModel):
        distance: int  # meters
        duration: int  # seconds
        
        @computed_field
        @property
        def avg_speed_kmh(self) -> float:
            if self.duration == 0:
                return 0.0
            ms = self.distance / self.duration
            return ms * 3.6

The computed field is included in .model_dump()!


SCENARIO 5: Add validation that depends on data source
──────────────────────────────────────────────────────

If data from different sources has different rules:

    class ActivityModel(BaseModel):
        activity_type: str
        distance: int
        source: str = Field(default="garmin")  # Where data came from
        
        @field_validator('distance')
        @classmethod
        def validate_distance(cls, v: int, info) -> int:
            # Different validation per source
            if info.data.get('source') == 'strava':
                max_distance = 300000  # Strava max
            else:
                max_distance = 500000  # Garmin max
            
            if v > max_distance:
                raise ValueError(f'Distance too high for {info.data.get("source")}')
            return v
"""


# ═════════════════════════════════════════════════════════════════════════════
# 8. TESTING YOUR MODIFICATIONS
# ═════════════════════════════════════════════════════════════════════════════

"""
QUICK TESTING IN PYTHON REPL:
──────────────────────────────

    # Import model
    from app.models.activities import SummarizedActivityModel
    
    # Test valid data
    activity = SummarizedActivityModel(
        activity_id=123,
        activity_type="cycling",
        start_time_in_seconds=1715904000000,
        duration=7200,
        distance=50000,
        avg_moving_speed=6.94,
        max_moving_speed=12.5,
        calories=450
    )
    
    # Test field access
    print(activity.activity_type)  # "cycling"
    print(activity.get_average_speed_kmh())  # 24.98
    
    # Test validation failure
    try:
        bad = SummarizedActivityModel(
            activity_id=-1,  # ← Should fail (gt=0)
            ...
        )
    except ValueError as e:
        print(f"Validation failed: {e}")
    
    # Convert to dict
    data = activity.model_dump()
    
    # JSON serialization
    json_str = activity.model_dump_json()


PYTEST TEST TEMPLATE:
─────────────────────

    import pytest
    from app.models.activities import SummarizedActivityModel
    
    class TestSummarizedActivityModel:
        
        def test_valid_activity(self):
            '''Test creating valid activity'''
            activity = SummarizedActivityModel(
                activity_id=123,
                activity_type="cycling",
                start_time_in_seconds=1715904000000,
                duration=7200,
                distance=50000,
                avg_moving_speed=6.94,
                max_moving_speed=12.5,
                calories=450
            )
            assert activity.activity_type == "cycling"
            assert activity.distance == 50000
        
        def test_negative_activity_id_fails(self):
            '''Test validation rejects negative ID'''
            with pytest.raises(ValueError):
                SummarizedActivityModel(
                    activity_id=-1,  # Invalid!
                    ...
                )
        
        def test_helper_method(self):
            '''Test helper method calculation'''
            activity = SummarizedActivityModel(...)
            assert activity.get_duration_hours() == 2.0
        
        def test_optional_fields(self):
            '''Test model works with optional fields missing'''
            activity = SummarizedActivityModel(
                activity_id=123,
                activity_type="cycling",
                start_time_in_seconds=1715904000000,
                duration=7200,
                distance=50000,
                avg_moving_speed=6.94,
                max_moving_speed=12.5,
                # calories optional - can omit
                # avg_heart_rate optional - can omit
            )
            assert activity.calories == 0


TO RUN:
    pytest tests/test_models.py -v
"""


# ═════════════════════════════════════════════════════════════════════════════
# QUICK CHECKLIST FOR MODIFICATIONS
# ═════════════════════════════════════════════════════════════════════════════

"""
When you modify models:

✅ Update docstring at top
✅ Add Field() documentation  
✅ Add validator if needed
✅ Update model_config if needed
✅ Add helper method if useful
✅ Update to_dict_for_chunking() if field affects RAG
✅ Write test for new field/validator
✅ Run: python -m pytest tests/test_models.py -v
✅ Check type hints are correct
✅ Update docstring examples
✅ Verify imports at top of file
"""
