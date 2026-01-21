# Sisqual Example
## Shift Possibilities per Team
- Storage
    - 8:30 // 15:30
- Checkout
    - 10:00 // 11:00
    - 11:00 // 21:00
    - 21:00 // 22:00
- Management
    - 10:00 // 11:00
    - 11:00 // 14:00
    - 14:00 // 19:00
    - 19:00 // 21:00
    - 21:00 // 22:00

## Employees
- Emp_20072412	(Management - 1)
- Emp_20066543	(Management - 2)
- Emp_20067009	(Checkout - 1)(Management - 3)
- Emp_20054956	(Checkout - 2)(Management - 4)
- Emp_20056459	(Checkout - 1)
- Emp_20062688	(Checkout - 3)(Management - 4)
- Emp_20067696	(Checkout - 2)
- Emp_20058959	(Checkout - 2)
- Emp_20068397	(Checkout - 2)
- Emp_20038706	(Checkout - 2)
- Emp_20066338	(Checkout - 3)
- Emp_900027719	(Checkout - 4)
- Emp_20051291	(Storage - 1)
- Emp_20055066	(Checkout - 4)
- Emp_900027718	(Checkout - 5)

## Minimium per shift per team
- Storage
    - Weekday
        - 8:30 // 15:30 -> 1
- Checkout
    - Weekday
        - 10:00 // 11:00 -> 1
        - 11:00 // 21:00 -> 1
        - 21:00 // 22:00 -> 1
    - Weekend
        - 11:00 // 21:00 -> 1
- Management
    - Weekday
        - 10:00 // 11:00 -> 1
        - 11:00 // 14:00 -> 1
        - 14:00 // 19:00 -> 1
        - 19:00 // 21:00 -> 1
        - 21:00 // 22:00 -> 1
    - Saturday
        - 11:00 // 14:00 -> 1
        - 14:00 // 19:00 -> 1
        - 19:00 // 21:00 -> 1
    - Sunday
        - 11:00 // 14:00 -> 1
        - 19:00 // 21:00 -> 1

## Time Frame
- **Start Day**: 1 october (year unknown) // wednesday
- **End Day**: 31 october (year unknown) // friday

## Types of Unavailability 
- Unavaliable (NOT)
- Holidays (HOL)
- Day Off (DO)
- Time Constraint (HH:MM-HH:MM)
- Medical Reason (Med)

## Schedule Unavailability
- Emp_20072412
    - Holidays
        - 13 oct - 19 oct
- Emp_20066543
    - Holidays
        - 20 oct - 26 oct
- Emp_20067009
- Emp_20054956
    - Unavailable
        - 5 oct
    - Holidays
        - 27 oct - 31 oct
- Emp_20056459
    - Time Constraint
        - 7 oct (10:00-14:00)
    - Day Off
        - 10 oct
- Emp_20062688
    - Holidays
        - 2 oct - 12 oct
        - 27 oct - 31 oct
- Emp_20067696
- Emp_20058959
    - Unavailable
        - 1 oct 
- Emp_20068397
- Emp_20038706
- Emp_20066338
    - Time Constraint
        - 4 oct (11:00-16:00)
- Emp_900027719
- Emp_20051291
    - Holidays
        - 28 oct - 31 oct
    - Unavailable
        - 27 oct
- Emp_20055066
    - Medical Reason
        - 1 oct - 12 oct
- Emp_900027718

