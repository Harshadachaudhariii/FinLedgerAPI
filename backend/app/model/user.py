from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from datetime import date

class User(BaseModel):
    username: str=Field(..., description="Username of the user")
    password: str=Field(..., description="Password of the user")
    created_at: Optional[date]=Field(default=date.today(), description="Date of user creation")