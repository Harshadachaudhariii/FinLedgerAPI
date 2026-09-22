from enum import Enum

class BudgetStatusType(str, Enum):
    ON_TRACK="on_track"
    WARNING="warning"
    EXCEEDED= "exceeded"
    
class TransactionCategory(str, Enum):
    FOOD="Food"
    TRANSPORT="Transport"
    SALARY="Salary"
    RENT ="Rent"
    UTILITIES="Utilities"
    ENTERTAINMENT="Entertainment"
    HEALTH="Health"
    FREELANCE="Freelance"
    GIFT="Gift"
    SHOPPING="Shopping"
    BONUS="Bonus"
    EDUCATION="Education"
    OTHER="Other"