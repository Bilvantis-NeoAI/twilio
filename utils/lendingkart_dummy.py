# 1. Target Status Function
def get_target_status(phone_number):
    print("lendingkart function called")
    return "Last week status  is 15% more compared to the prior week. The next target has a gap of 22.75%. over all good"

# 2. Incentives Function
def incentive_details(phone_number):
    print("lendingkart function called")

    return "You have earned an incentive of 1250 as you met the target. if you exceed the target you will get additional 10% on the recovery interest"

# 3. Penalty Charges Function
def penalty_details(phone_number):
    print("lendingkart function called")

    return "After the due date flat 2% for a month and after that additional 5% every month as per guidelines"

# 4. Guidelines to Improve Collections Function
def collection_improvements(phone_number):
    print("lendingkart function called")
    return "Requires focus on top customers and defaulters. Use AI app developed for it"
# 5. Top Focus Defaulters Function
def top_defaulters(phone_number):
    print("lendingkart function called")

    return """Rajesh Kumar -- 8 times
        Priya Sharma -- 6 times
        Amit Patel -- 5 times
        Neha Gupta -- 4 times
        Sanjay Singh -- 3 times
        Total Amount to be Collected: 125000"""

if __name__ == "__main__":
    phone_number="+919963029130"
    print(get_target_status(phone_number))
    print(incentive_details(phone_number))
    print(top_defaulters(phone_number))
    print(penalty_details(phone_number))
    print(collection_improvements(phone_number))



