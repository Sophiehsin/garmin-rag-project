"""
Pydantic model for Garmin SummarizedActivity data

Logic Overview:
    - Represents a single activity record (cycling, running, etc.)
    - Timestamps stored in milliseconds (Unix epoch format)
    - Distances stored in meters
    - Speeds stored in m/s
    - Conversion to standard units happens in parser.py (Task 5 & 6)

Field Structure:
    Core: activityId, activityType, duration
    Time: startTimeInSeconds (milliseconds)
    Distance: distance (meters)
    Speed: avgMovingSpeed, maxMovingSpeed (m/s)
    Energy: calories
    Optional: sport, elevationGain, etc.

Validation Rules:
    1. activityId must be positive integer
    2. duration should be > 0 (in seconds)
    3. distance should be >= 0 (in meters)
    4. speeds should be >= 0 (in m/s)
    5. calories should be >= 0

How to Modify:
    - Add new field: Add line with Field() definition + update docstring
    - Change type: Modify type annotation (e.g., int → float)
    - Add validator: Use @field_validator decorator below class fields
    - Make optional: Wrap type in Optional[Type] or set default=None
    - Add description: Use Field(description="...") for UI/docs
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SummarizedActivityModel(BaseModel):
    """
    Garmin SummarizedActivity record - represents a single workout/activity session
    
    Example JSON from Garmin:
    {
        "activityId": 12345678,
        "activityType": {
            "typeId": 1,
            "typeKey": "cycling"
        },
        "startTimeInSeconds": 1715904000000,  # milliseconds!
        "duration": 7200,  # seconds
        "distance": 50000,  # meters
        "avgMovingSpeed": 6.94,  # m/s
        "maxMovingSpeed": 12.5,  # m/s
        "calories": 450,
        "elevationGain": 500  # meters
    }
    """

    # ===== CORE FIELDS =====
    activity_id: int = Field(
        ...,
        description="Unique activity identifier from Garmin",
        example=12345678,
        gt=0  # greater than 0
    )
    
    activity_type: str = Field(
        ...,
        description="Activity type key (cycling, running, swimming, etc.)",
        example="cycling",
        min_length=1
    )
    
    # ===== TIME FIELDS =====
    start_time_in_seconds: int = Field(
        ...,
        description="Start time in milliseconds (Unix epoch). Divide by 1000 for seconds. Will be normalized in parser.py",
        example=1715904000000,
        ge=0
    )
    
    duration: int = Field(
        ...,
        description="Duration in seconds",
        example=7200,
        gt=0
    )
    
    # ===== DISTANCE FIELDS =====
    distance: int = Field(
        ...,
        description="Total distance in meters. Convert to km in parser.py (÷1000)",
        example=50000,
        ge=0
    )
    
    elevation_gain: Optional[int] = Field(
        default=None,
        description="Elevation gain in meters",
        example=500,
        ge=0
    )
    
    # ===== SPEED FIELDS =====
    avg_moving_speed: float = Field(
        ...,
        description="Average moving speed in m/s. Convert to km/h in parser.py (×3.6)",
        example=6.94,
        ge=0.0
    )
    
    max_moving_speed: float = Field(
        ...,
        description="Maximum moving speed in m/s. Convert to km/h in parser.py (×3.6)",
        example=12.5,
        ge=0.0
    )
    
    # ===== ENERGY FIELDS =====
    calories: int = Field(
        default=0,
        description="Calories burned in this activity",
        example=450,
        ge=0
    )
    
    # ===== OPTIONAL FIELDS =====
    sport_type: Optional[str] = Field(
        default=None,
        description="Sport type (e.g., 'CYCLING', 'RUNNING')",
        example="CYCLING"
    )
    
    avg_heart_rate: Optional[int] = Field(
        default=None,
        description="Average heart rate (bpm)",
        example=120,
        ge=0
    )
    
    max_heart_rate: Optional[int] = Field(
        default=None,
        description="Maximum heart rate (bpm)",
        example=180,
        ge=0
    )
    
    steps: Optional[int] = Field(
        default=None,
        description="Number of steps (for activities where applicable)",
        ge=0
    )
    
    # ===== PYDANTIC CONFIG =====
    model_config = ConfigDict(
        validate_default=True,
        use_attribute_docstrings=True,
        str_strip_whitespace=True,
    )
    
    # ===== FIELD VALIDATORS =====
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """
        Ensure duration is reasonable (> 0, < 24 hours)
        
        Logic: Activities should be between 1 second and 24 hours
        Modify: Change max value (86400) to different limit
        """
        if v <= 0:
            raise ValueError('Duration must be positive (in seconds)')
        if v > 86400:  # 24 hours
            raise ValueError('Duration cannot exceed 24 hours')
        return v
    
    @field_validator('distance')
    @classmethod
    def validate_distance(cls, v: int, info) -> int:
        """
        Distance should be reasonable compared to duration
        
        Logic: 
            - For cycling: max ~300 km in 24h = 300000 meters
            - For running: max ~150 km in 24h = 150000 meters
            Skip validation if unreasonable (could be data error)
        Modify: Adjust max_distance or enable strict validation
        """
        max_distance = 500000  # 500 km - extremely generous limit
        if v > max_distance:
            raise ValueError(f'Distance {v}m seems unreasonable (> 500km)')
        return v
    
    @field_validator('avg_moving_speed', 'max_moving_speed')
    @classmethod
    def validate_speeds(cls, v: float) -> float:
        """
        Speed validation (m/s to km/h)
        
        Logic:
            - m/s × 3.6 = km/h
            - 30 m/s = 108 km/h (reasonable max for bicycle)
            - 15 m/s = 54 km/h (reasonable max for running)
        Modify: Adjust max value if needed for different sports
        """
        if v < 0:
            raise ValueError('Speed cannot be negative')
        if v > 30:  # 108 km/h - very high for most activities
            raise ValueError(f'Speed {v} m/s seems unreasonable')
        return v
    
    @field_validator('calories')
    @classmethod
    def validate_calories(cls, v: int) -> int:
        """
        Calories should be reasonable
        
        Logic: Intense activity shouldn't burn > 10000 calories
        Modify: Change max_calories value
        """
        if v < 0:
            raise ValueError('Calories cannot be negative')
        if v > 10000:
            raise ValueError('Calories seems unreasonably high')
        return v
    
    @field_validator('avg_heart_rate', 'max_heart_rate', mode='before')
    @classmethod
    def validate_heart_rate(cls, v: Optional[int]) -> Optional[int]:
        """
        Heart rate validation (bpm)
        
        Logic:
            - Normal range: 40-200 bpm
            - Below 40: resting HR (maybe athlete) or data error
            - Above 200: possible data error
        Modify: Adjust min/max values
        """
        if v is None:
            return None
        if v < 0 or v > 250:
            raise ValueError(f'Heart rate {v} bpm is outside valid range')
        return v
    
    # ===== HELPER METHODS =====
    
    def get_duration_minutes(self) -> float:
        """Convert duration from seconds to minutes"""
        return self.duration / 60
    
    def get_duration_hours(self) -> float:
        """Convert duration from seconds to hours"""
        return self.duration / 3600
    
    def get_calories_per_hour(self) -> float:
        """Calculate calories burned per hour"""
        hours = self.get_duration_hours()
        if hours == 0:
            return 0
        return self.calories / hours
    
    def to_dict_for_chunking(self) -> dict:
        """
        Convert model to human-readable text for RAG chunking
        
        Usage in Task 9 (Chunking):
            text = activity.to_dict_for_chunking()
            Creates readable format for embedding
        
        Modify: Change format/fields included
        """
        return {
            "activity_type": self.activity_type,
            "date": datetime.fromtimestamp(self.start_time_in_seconds / 1000).strftime("%Y-%m-%d"),
            "duration_hours": round(self.get_duration_hours(), 2),
            "distance_km": round(self.distance / 1000, 2),
            "avg_speed_kmh": round(self.avg_moving_speed * 3.6, 2),
            "max_speed_kmh": round(self.max_moving_speed * 3.6, 2),
            "calories": self.calories,
            "avg_hr": self.avg_heart_rate,
        }
