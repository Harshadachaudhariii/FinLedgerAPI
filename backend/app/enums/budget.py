from enum import Enum

class BudgetStatusType(str, Enum):
    ON_TRACK="on_track"
    WARNING="warning"
    EXCEEDED= "exceeded"
    
