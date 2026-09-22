from enum import Enum

class TransactionPaymentMethod(str, Enum):
    DebitCard= "Debit Card"
    CreditCard= "Credit Card"
    UPI="UPI"
    CASH="Cash"
    BankTransfer="Bank Transfer"

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

class TransactionMerchant(str, Enum):
    EmployerPayroll ="Employer Payroll"
    ApartmentManagement="Apartment Management"
    LocalGroceryRestaurant= "Local Grocery & Restaurant"
    LocalTransport="Local Transport"
    UtilityProvider ="Utility Provider"
    FreelanceClient ="Freelance Client"
    EntertainmentService ="Entertainment Service"
    HealthcareProvider ="Healthcare Provider"
    RetailStore= "Retail Store"
    OnlineLearningPlatform ="Online Learning Platform"
    FAMILY = "Family"

class TransactionStatus(str, Enum):
    COMPLETED = "completed"  
    PENDING="pending"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
