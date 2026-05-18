"""
Pydantic model for Garmin SleepData

Logic Overview:
    - Represents sleep records for a calendar date
    - Timestamps in ISO 8601 format with millisecond precision
    - Duration stored in seconds
    - Sleep quality tracked via different sleep stages (deep/light/REM/awake)
    - Conversion to standard formats happens in parser.py

Field Structure:
    Core: calendarDate, sleepStartTimestampGMT, sleepEndTimestampGMT
    Duration: deepSleepSeconds, lightSleepSeconds, remSleepSeconds, awakeSleepSeconds
    Health: averageHeartRate, averageRespiration, spo2 metrics
    Quality: sleepScores, sleepWindowConfirmationType

Validation Rules:
    1. Timestamps must be valid ISO 8601 format
    2. All sleep seconds should be >= 0
    3. Total sleep seconds = deep + light + REM + awake + unmeasurable
    4. Heart rate & SpO2 must be in valid ranges

How to Modify:
    - Add new sleep metric: Add field + validator + update docstring
    - Change timestamp format: Modify startTimeInSeconds type + parsing logic
    - Add sleep score logic: Create @property for calculated scores
    - Make field optional: Use Optional[Type] with default=None
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SleepDataModel(BaseModel):
    """
    Garmin SleepData record - represents a single night's sleep
    
    Example JSON from Garmin:
    {
        "sleepStartTimestampGMT": "2024-05-14T15:41:04.0",
        "sleepEndTimestampGMT": "2024-05-14T22:01:04.0",
        "calendarDate": "2024-05-15",
        "sleepWindowConfirmationType": "ENHANCED_CONFIRMED_FINAL",
        "deepSleepSeconds": 6720,
        "lightSleepSeconds": 11460,
        "remSleepSeconds": 1920,
        "awakeSleepSeconds": 2700,
        "unmeasurableSeconds": 0,
        "averageHeartRate": 49.0,
        "averageRespiration": 16.0
    }
    """
    
    # ===== CORE FIELDS =====
    calendar_date: str = Field(
        ...,
        description="Calendar date in YYYY-MM-DD format",
        example="2024-05-15",
        pattern=r'^\d{4}-\d{2}-\d{2}$'  # Regex validation for date format
    )
    
    # ===== TIMESTAMP FIELDS (ISO 8601) =====
    sleep_start_timestamp_gmt: str = Field(
        ...,
        description="Sleep start time in ISO 8601 format with GMT timezone. Will be parsed in parser.py",
        example="2024-05-14T15:41:04.0",
    )
    
    sleep_end_timestamp_gmt: str = Field(
        ...,
        description="Sleep end time in ISO 8601 format with GMT timezone",
        example="2024-05-14T22:01:04.0",
    )
    
    # ===== SLEEP DURATION FIELDS (all in seconds) =====
    deep_sleep_seconds: int = Field(
        ...,
        description="Deep sleep duration in seconds",
        example=6720,
        ge=0
    )
    
    light_sleep_seconds: int = Field(
        ...,
        description="Light sleep duration in seconds",
        example=11460,
        ge=0
    )
    
    rem_sleep_seconds: int = Field(
        ...,
        description="REM sleep duration in seconds",
        example=1920,
        ge=0
    )
    
    awake_sleep_seconds: int = Field(
        ...,
        description="Awake/restless time during sleep in seconds",
        example=2700,
        ge=0
    )
    
    unmeasurable_seconds: int = Field(
        default=0,
        description="Time that couldn't be measured/classified",
        ge=0
    )
    
    # ===== HEALTH METRICS =====
    average_heart_rate: Optional[float] = Field(
        default=None,
        description="Average heart rate during sleep (bpm)",
        example=49.0,
        ge=0.0
    )
    
    max_heart_rate: Optional[float] = Field(
        default=None,
        description="Maximum heart rate during sleep (bpm)",
        example=65.0,
        ge=0.0
    )
    
    min_heart_rate: Optional[float] = Field(
        default=None,
        description="Minimum heart rate during sleep (bpm)",
        example=42.0,
        ge=0.0
    )
    
    average_respiration: Optional[float] = Field(
        default=None,
        description="Average respiration rate during sleep (breaths/minute)",
        example=16.0,
        ge=0.0
    )
    
    highest_respiration: Optional[float] = Field(
        default=None,
        description="Highest respiration rate during sleep",
        example=24.0,
        ge=0.0
    )
    
    lowest_respiration: Optional[float] = Field(
        default=None,
        description="Lowest respiration rate during sleep",
        example=11.0,
        ge=0.0
    )
    
    # ===== SPO2 METRICS =====
    average_spo2: Optional[float] = Field(
        default=None,
        description="Average SpO2 (blood oxygen saturation) % during sleep",
        example=96.0,
        ge=85.0,  # Below 85% is concerning
        le=100.0
    )
    
    lowest_spo2: Optional[float] = Field(
        default=None,
        description="Lowest SpO2 % during sleep",
        example=88.0,
        ge=70.0,  # Below 70% is dangerous
        le=100.0
    )
    
    # ===== SLEEP QUALITY & CLASSIFICATION =====
    sleep_window_confirmation_type: Optional[str] = Field(
        default=None,
        description="Sleep window confirmation type (e.g., 'ENHANCED_CONFIRMED_FINAL')",
        example="ENHANCED_CONFIRMED_FINAL"
    )
    
    retro: Optional[bool] = Field(
        default=False,
        description="Whether this is a retroactive/corrected sleep record"
    )
    
    awake_count: Optional[int] = Field(
        default=0,
        description="Number of times user woke up during sleep",
        ge=0
    )
    
    avg_sleep_stress: Optional[float] = Field(
        default=None,
        description="Average sleep stress level (0-100, lower is better)",
        example=14.67,
        ge=0.0,
        le=100.0
    )
    
    # ===== SLEEP SCORES =====
    overall_sleep_score: Optional[int] = Field(
        default=None,
        description="Overall sleep score out of 100",
        example=76,
        ge=0,
        le=100
    )
    
    sleep_quality_score: Optional[int] = Field(
        default=None,
        description="Sleep quality score out of 100",
        example=82,
        ge=0,
        le=100
    )
    
    sleep_recovery_score: Optional[int] = Field(
        default=None,
        description="Sleep recovery score out of 100",
        example=75,
        ge=0,
        le=100
    )
    
    # ===== PYDANTIC CONFIG =====
    model_config = ConfigDict(
        validate_default=True,
        use_attribute_docstrings=True,
        str_strip_whitespace=True,
    )
    
    # ===== FIELD VALIDATORS =====
    
    @field_validator('calendar_date')
    @classmethod
    def validate_calendar_date(cls, v: str) -> str:
        """
        Validate date format and reasonableness
        
        Logic: Date should be parseable and within last 5 years
        Modify: Extend/reduce date range as needed
        """
        try:
            parsed_date = datetime.strptime(v, '%Y-%m-%d')
            # Check if date is reasonable (not future, not too old)
            if parsed_date.year < 2018:
                raise ValueError('Date is too old (before 2018)')
            return v
        except ValueError as e:
            raise ValueError(f'Invalid date format or value: {v}')
    
    @field_validator('sleep_start_timestamp_gmt', 'sleep_end_timestamp_gmt')
    @classmethod
    def validate_iso_timestamps(cls, v: str) -> str:
        """
        Validate ISO 8601 timestamp format
        
        Logic: Should be parseable ISO format with GMT/Z timezone
        Modify: Support additional timezone formats if needed
        """
        try:
            # Try parsing with .0 milliseconds (Garmin format)
            if v.endswith('.0'):
                datetime.fromisoformat(v[:-2] + 'Z')
            else:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f'Invalid ISO 8601 timestamp: {v}')
    
    @field_validator('deep_sleep_seconds', 'light_sleep_seconds', 'rem_sleep_seconds', 'awake_sleep_seconds')
    @classmethod
    def validate_sleep_seconds(cls, v: int) -> int:
        """
        Validate sleep duration segments
        
        Logic: Each segment should be 0-14 hours (50400 seconds)
        Modify: Adjust max duration if needed
        """
        max_sleep_seconds = 50400  # 14 hours
        if v > max_sleep_seconds:
            raise ValueError(f'Sleep segment {v}s exceeds 14 hours')
        return v
    
    @field_validator('average_heart_rate', 'max_heart_rate', 'min_heart_rate', mode='before')
    @classmethod
    def validate_heart_rates(cls, v: Optional[float]) -> Optional[float]:
        """
        Heart rate validation for sleep
        
        Logic: Sleep HR typically 40-100 bpm (lower than awake)
        Modify: Adjust valid range for different populations
        """
        if v is None:
            return None
        if v < 30 or v > 150:
            raise ValueError(f'Sleep heart rate {v} bpm is unrealistic')
        return v
    
    @field_validator('average_respiration', 'highest_respiration', 'lowest_respiration', mode='before')
    @classmethod
    def validate_respiration(cls, v: Optional[float]) -> Optional[float]:
        """
        Respiration rate validation
        
        Logic: Normal sleep respiration 8-25 breaths/minute
        Modify: Adjust range if needed
        """
        if v is None:
            return None
        if v < 5 or v > 40:
            raise ValueError(f'Respiration rate {v} bpm is unrealistic')
        return v
    
    @field_validator('average_spo2', 'lowest_spo2', mode='before')
    @classmethod
    def validate_spo2(cls, v: Optional[float]) -> Optional[float]:
        """
        SpO2 validation
        
        Logic: Healthy SpO2 is 95-100%, concerning < 90%
        Modify: Flag or reject readings below certain threshold
        """
        if v is None:
            return None
        if v < 70 or v > 100:
            raise ValueError(f'SpO2 {v}% is outside valid range')
        return v
    
    # ===== HELPER METHODS & PROPERTIES =====
    
    def get_total_sleep_seconds(self) -> int:
        """Calculate total sleep time (all stages combined)"""
        return (
            self.deep_sleep_seconds
            + self.light_sleep_seconds
            + self.rem_sleep_seconds
            + self.awake_sleep_seconds
            + self.unmeasurable_seconds
        )
    
    def get_total_sleep_hours(self) -> float:
        """Convert total sleep to hours"""
        return self.get_total_sleep_seconds() / 3600
    
    def get_sleep_efficiency(self) -> float:
        """
        Calculate sleep efficiency: actual sleep / total time in bed
        
        Logic: (deep + light + REM) / total_time_in_bed * 100
        Modify: Include/exclude different sleep stages in calculation
        """
        total = self.get_total_sleep_seconds()
        if total == 0:
            return 0.0
        actual_sleep = (
            self.deep_sleep_seconds
            + self.light_sleep_seconds
            + self.rem_sleep_seconds
        )
        return (actual_sleep / total) * 100
    
    def get_deep_sleep_percentage(self) -> float:
        """Deep sleep as percentage of total sleep"""
        total = self.get_total_sleep_seconds()
        if total == 0:
            return 0.0
        return (self.deep_sleep_seconds / total) * 100
    
    def get_rem_sleep_percentage(self) -> float:
        """REM sleep as percentage of total sleep"""
        total = self.get_total_sleep_seconds()
        if total == 0:
            return 0.0
        return (self.rem_sleep_seconds / total) * 100
    
    def to_dict_for_chunking(self) -> dict:
        """
        Convert model to human-readable text for RAG chunking
        
        Usage in Task 9 (Chunking):
            Creates readable format with sleep quality information
        Modify: Change fields or format
        """
        return {
            "date": self.calendar_date,
            "total_sleep_hours": round(self.get_total_sleep_hours(), 2),
            "deep_sleep_hours": round(self.deep_sleep_seconds / 3600, 2),
            "light_sleep_hours": round(self.light_sleep_seconds / 3600, 2),
            "rem_sleep_hours": round(self.rem_sleep_seconds / 3600, 2),
            "sleep_efficiency": round(self.get_sleep_efficiency(), 1),
            "avg_hr": self.average_heart_rate,
            "avg_spo2": self.average_spo2,
            "sleep_quality_score": self.sleep_quality_score,
        }
