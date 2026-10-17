from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, model_validator


WeekType = Literal["odd", "even", "both"]


class WeeklyScheduleCreate(BaseModel):
    lesson_id: int
    weekday: int = Field(ge=0, le=6)
    room_id: int
    start_time: time
    end_time: time
    week_type: WeekType = "both"

    @model_validator(mode="after")
    def validate_time(self):
        if self.start_time >= self.end_time:
            raise ValueError(
                "Время окончания должно быть позже начала"
            )
        return self
