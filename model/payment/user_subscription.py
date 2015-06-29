from biicode.common.model.brl.brl_user import BRLUser
from biicode.common.utils.serializer import Serializer
from biicode.server.model.epoch.time_period import TimePeriod


# KEEP SYNC WITH STRIPE BACKEND PLANS, STRIPE CAN'T STORE PLAN PROPERTIES
# NAME, PRICE, NUM_USERS (private contributors), NUM_PRIVATE_BLOCKS (-1 UNLIMITED)
FREE_PLAN_ID = "free"
PLANS_CURRENCY = "eur"
CURRENT_PLANS = {"DEIMOS": {"name": "Deimos Plan", "amount": 150, "num_users": 25,
                            "num_private_blocks": -1, "active": False},
                 "PERSONAL12TRIAL": {"name": "Personal 12 Months Trial", "amount": 7, "num_users": 1,
                                     "num_private_blocks": -1, "active": False},
                 "2MONTHSTRIAL": {"name": "Personal 2 Months Trial", "amount": 7, "num_users": 1,
                                  "num_private_blocks": -1, "active": False},
                 "free": {"name": "Free", "amount": 0, "num_users": 0,
                          "num_private_blocks": 0, "active": True},
                 "personal_7_1_x": {"name": "Personal", "amount": 7, "num_users": 1,
                                    "num_private_blocks": -1, "active": True},
                 "startup_35_5_x": {"name": "Startup", "amount": 35,
                                    "num_users": 5, "num_private_blocks": -1, "active": True},
                 "team_65_10_x": {"name": "Team", "amount": 65,
                                  "num_users": 10, "num_private_blocks": -1, "active": True},
                 "corporate_150_25_x": {"name": "Corporate", "amount": 150,
                                        "num_users": 25, "num_private_blocks": -1, "active": True},
                 "enterprise_275_50_x": {"name": "Enterprise", "amount": 275,
                                         "num_users": 50, "num_private_blocks": -1, "active": True},
                 }


class UserSubscription(object):
    """This class manages has the historical user payment plans, the current
    plan and manages the modification of them.
    EX: Current plan is a plan of 20 users"""

    MAX_PERIOD_UNTIL_CANCEL = TimePeriod("DAY", 15)

    def __init__(self, brl_user):
        self.ID = brl_user  # BRLUser
        self.customer_id = None  # cus_4fdAW5ftNQow1a
        self.plan_id = None  # Store for performance, need to know plan properties often for perms

    @property
    def max_users(self):
        '''Get the num users according to plan'''
        return CURRENT_PLANS[self.plan_id]["num_users"]

    @property
    def max_private_blocks(self):
        '''Get the num private blocks according to plan'''
        return CURRENT_PLANS[self.plan_id]["num_private_blocks"]

    SERIAL_ID_KEY = "_id"
    SERIAL_CUSTOMER_ID_KEY = "c"
    SERIAL_PLAN_ID = "p"

    @staticmethod
    def deserialize(data):
        """deserialize model"""
        theid = BRLUser(data[UserSubscription.SERIAL_ID_KEY])
        ret = UserSubscription(theid)
        ret.customer_id = data.get(UserSubscription.SERIAL_CUSTOMER_ID_KEY, None)
        ret.plan_id = data.get(UserSubscription.SERIAL_PLAN_ID, FREE_PLAN_ID)
        return ret

    def serialize(self):
        """serialize model"""
        return Serializer().build(
                (self.SERIAL_ID_KEY, self.ID),
                (self.SERIAL_CUSTOMER_ID_KEY, self.customer_id),
                (self.SERIAL_PLAN_ID, self.plan_id)
        )

    def __eq__(self, other):
        """equal method"""
        if self is other:
            return True
        return isinstance(other, self.__class__) \
            and self.ID == other.ID \
            and self.customer_id == other.customer_id \


    def __ne__(self, other):
        """not equal method"""
        return not self.__eq__(other)
