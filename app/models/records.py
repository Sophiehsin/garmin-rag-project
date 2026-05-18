"""
Pydantic model for Garmin PersonalRecord data

Logic Overview:
    - Represents personal records (personal bests) for specific activities
    - Stores activity name, type, value, and the date achieved
    - Date is in text format (needs parsing in Task 5)
    - Records are milestone achievements (new PR)

Field Structure:
    Core: personalRecordId, personalRecordType (activity type)
    Record: value (the PR value), recordUnit (meters, seconds, etc.)
    Date: recordDate (text format), createDate
    Optional: linkedActivityId (if from specific activity)

Validation Rules:
    1. personalRecordType must be non-empty
    2. value should be > 0 (can't have 0 meter PR)
    3. recordDate must be parseable text date format
    4. recordUnit must be valid (m, km, seconds, etc.)

How to Modify:
    - Add new record metric: Add field + validator
    - Change date parsing: Modify recordDate handling + add new format support
    - Add achievement info: Create @property for achievement level
    - Add nested data: Use nested Pydantic model for compound data
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class PersonalRecordModel(BaseModel):
    """
    Garmin PersonalRecord - represents a personal best achievement
    
    Example JSON from Garmin:
    {
        "personalRecordId": 98765,
        "personalRecordType": {
            "typeId": 1,
            "typeKey": "fastest_5k_time",
            "displayOrder": 1
        },
        "value": 1234.5,
        "recordUnit": {
            "unitId": 2,
            "factor": 1.0,
            "key": "meter"
        },
        "recordDate": "May 15, 2024",
        "createDate": "2024-05-15T14:30:00.000",
        "linkedActivityId": 12345678
    }
    """
    
    # ===== CORE IDENTIFICATION =====
    personal_record_id: int = Field(
        ...,
        description="Unique record identifier from Garmin",
        example=98765,
        gt=0
    )
    
    personal_record_type: str = Field(
        ...,
        description="Type of personal record (e.g., 'fastest_5k_time', 'farthest_distance')",
        example="fastest_5k_time",
        min_length=1
    )
    
    # ===== RECORD VALUE =====
    value: float = Field(
        ...,
        description="The personal record value (e.g., 1234.5 for distance in meters, 1800 for time in seconds)",
        example=1234.5,
        gt=0.0  # must be positive
    )
    
    record_unit: str = Field(
        ...,
        description="Unit of measurement (meter, kilometer, second, hour, bpm, etc.)",
        example="meter",
        min_length=1
    )
    
    # ===== DATES =====
    record_date: str = Field(
        ...,
        description="Date when record was achieved. Text format like 'May 15, 2024'. Will be parsed in parser.py",
        example="May 15, 2024"
    )
    
    create_date: Optional[str] = Field(
        default=None,
        description="Date when record was created in system (ISO 8601 format)",
        example="2024-05-15T14:30:00.000"
    )
    
    # ===== OPTIONAL FIELDS =====
    linked_activity_id: Optional[int] = Field(
        default=None,
        description="ID of the activity that set this personal record",
        example=12345678,
        ge=0
    )
    
    activity_type: Optional[str] = Field(
        default=None,
        description="Type of activity this record relates to (cycling, running, etc.)",
        example="cycling"
    )
    
    display_order: Optional[int] = Field(
        default=None,
        description="Display order in UI (lower = higher priority)",
        example=1,
        ge=0
    )
    
    # ===== PYDANTIC CONFIG =====
    model_config = ConfigDict(
        validate_default=True,
        use_attribute_docstrings=True,
        str_strip_whitespace=True,
    )
    
    # ===== FIELD VALIDATORS =====
    
    @field_validator('personal_record_type', 'activity_type', mode='before')
    @classmethod
    def validate_activity_type_string(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate activity type string
        
        Logic: Should be non-empty string without special characters
        Modify: Add specific activity type whitelist if needed
        """
        if v is None:
            return None
        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError('Activity type cannot be empty')
        return v.strip().lower()
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v: float, info) -> float:
        """
        Validate record value is reasonable
        
        Logic: Different units have different max values
            - Distance in meters: max 1,000,000 (1000 km)
            - Time in seconds: max 864,000 (10 days)
            - Speed in m/s: max 100 (360 km/h)
        Modify: Make stricter or looser depending on needs
        """
        if v <= 0:
            raise ValueError('Record value must be positive')
        if v > 10000000:  # Very generous upper limit
            raise ValueError(f'Record value {v} seems unreasonably high')
        return v
    
    @field_validator('record_unit')
    @classmethod
    def validate_record_unit(cls, v: str) -> str:
        """
        Validate record unit is valid
        
        Logic: Check against known Garmin unit types
        Modify: Add more unit types or make stricter
        """
        valid_units = {
            'meter', 'kilometer', 'mile', 'foot',  # Distance
            'second', 'minute', 'hour',  # Time
            'meters_per_second', 'km_h', 'mph',  # Speed
            'bpm',  # Heart rate
            'watts',  # Power
        }
        
        v_lower = v.strip().lower()
        
        # Allow any unit if strict validation disabled
        # Modify: Set strict_unit_validation = False to allow any unit
        strict_unit_validation = True
        
        if strict_unit_validation and v_lower not in valid_units:
            raise ValueError(f'Unknown unit: {v}. Valid units: {valid_units}')
        
        return v_lower
    
    @field_validator('record_date')
    @classmethod
    def validate_record_date(cls, v: str) -> str:
        """
        Validate record date format
        
        Logic: Date should be parseable and not in future
        Expected formats from Garmin:
            - "May 15, 2024"
            - "2024-05-15"
        Modify: Support additional date formats
        """
        if not v or not isinstance(v, str):
            raise ValueError('Record date must be a non-empty string')
        
        # Try common Garmin date format: "Month Day, Year"
        date_formats = [
            '%B %d, %Y',  # "May 15, 2024"
            '%Y-%m-%d',   # "2024-05-15"
            '%m/%d/%Y',   # "05/15/2024"
            '%d-%b-%Y',   # "15-May-2024"
        ]
        
        parsed_date = None
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(v.strip(), date_format)
                break
            except ValueError:
                continue
        
        if parsed_date is None:
            raise ValueError(
                f'Cannot parse record date: {v}. Supported formats: '
                f'{", ".join(date_formats)}'
            )
        
        # Check if date is in future (shouldn't happen)
        if parsed_date > datetime.now():
            raise ValueError(f'Record date cannot be in the future: {v}')
        
        return v.strip()
    
    @field_validator('create_date', mode='before')
    @classmethod
    def validate_create_date(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate ISO 8601 create date
        
        Logic: Should be parseable ISO format
        Modify: Support additional formats if needed
        """
        if v is None:
            return None
        
        try:
            # Try parsing ISO format
            if v.endswith('Z'):
                datetime.fromisoformat(v[:-1] + '+00:00')
            else:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v.strip()
        except ValueError:
            raise ValueError(f'Invalid create date format: {v}')
    
    @field_validator('linked_activity_id')
    @classmethod
    def validate_linked_activity_id(cls, v: Optional[int]) -> Optional[int]:
        """
        Validate linked activity ID
        
        Logic: Should be positive if present
        Modify: Can be stricter if needed
        """
        if v is not None and v < 0:
            raise ValueError('Activity ID cannot be negative')
        return v
    
    # ===== HELPER METHODS & PROPERTIES =====
    
    def get_achievement_level(self) -> str:
        """
        Categorize record achievement level based on value
        
        Logic: Higher values = higher achievement
        Modify: Adjust thresholds for different units
        
        Returns: "elite" | "advanced" | "intermediate" | "beginner"
        """
        # Simple heuristic: split into quartiles
        if self.value >= 1000:
            return "elite"
        elif self.value >= 500:
            return "advanced"
        elif self.value >= 100:
            return "intermediate"
        else:
            return "beginner"
    
    def get_record_date_parsed(self) -> datetime:
        """
        Parse record_date string to datetime object
        
        Logic: Handles multiple date formats
        Modify: Add more format support in validate_record_date()
        
        Usage: Used in Task 5 for timestamp normalization
        """
        date_formats = [
            '%B %d, %Y',  # "May 15, 2024"
            '%Y-%m-%d',   # "2024-05-15"
            '%m/%d/%Y',   # "05/15/2024"
            '%d-%b-%Y',   # "15-May-2024"
        ]
        
        for date_format in date_formats:
            try:
                return datetime.strptime(self.record_date.strip(), date_format)
            except ValueError:
                continue
        
        # Should not reach here if validator passed
        raise ValueError(f'Cannot parse record date: {self.record_date}')
    
    def get_record_age_days(self) -> int:
        """Calculate how many days ago this record was set"""
        record_dt = self.get_record_date_parsed()
        age = datetime.now() - record_dt
        return age.days
    
    def to_dict_for_chunking(self) -> dict:
        """
        Convert model to human-readable text for RAG chunking
        
        Usage in Task 9 (Chunking):
            Creates readable format for embedding
        Modify: Change fields or format
        """
        return {
            "record_type": self.personal_record_type,
            "achievement": self.get_achievement_level(),
            "value": self.value,
            "unit": self.record_unit,
            "date": self.record_date,
            "age_days": self.get_record_age_days(),
            "activity_type": self.activity_type,
        }
