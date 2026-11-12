
from pydantic import BaseModel, Field, model_validator


class AthleteProfileUpdate(BaseModel):
    max_heart_rate: int | None = Field(
        default=None,
        ge=100,
        le=230
    )

    resting_heart_rate: int | None = Field(
        default=None,
        ge=30,
        le=120
    )

    @model_validator(mode="after")
    def validate_profile(self):
        if not self.model_fields_set:
            raise ValueError(
                "Provide at least one field to update"
            )

        if (
            self.max_heart_rate is not None
            and self.resting_heart_rate is not None
            and self.resting_heart_rate >= self.max_heart_rate
        ):
            raise ValueError(
                "Resting heart rate must be below maximum heart rate"
            )

        return self
