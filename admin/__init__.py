# Script for create users in command line

from biicode.server.store.mongo_store import MongoStore
from biicode.server.store.mongo_server_store import MongoServerStore
from biicode.server.conf import BII_MONGO_URI
from biicode.server.user.user_service import UserService
import sys
from biicode.common.model.brl.brl_user import BRLUser
import getpass


connection = MongoStore.makeConnection(BII_MONGO_URI)
database_name = BII_MONGO_URI.split("/").pop()
server_store = MongoServerStore(connection, database_name)


def new_user(login, email, password):   
    service = UserService(server_store, login)
    service.register(login, email, password, True)
    user = server_store.read_user(login)
    user.active = True
    server_store.update_user(user)
    
def change_password(login, password):   
    user = server_store.read_user(login)
    user.password = password
    server_store.update_user(user)
    

def input_new_user():
    print "\n--------new user---------\n"
    login = raw_input("Login: ")
    email = raw_input("Email: ")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Password confirmation: ")
    if password != password_confirm:
        print "Password doesn't match"
        return
    new_user(login, email, password)
    print "User created!"
    
def input_change_password():
    print "\n-------change password---------\n"
    login = raw_input("Login: ")
    password = getpass.getpass("New password: ")
    password_confirm = getpass.getpass("Password confirmation: ")
    if password != password_confirm:
        print "Password doesn't match"
        return
    change_password(login, password)
    print "Password updated!"
        
    
def main():
    
    actions = {1: input_new_user, 2: input_change_password}
    
    while(1):
        print "--------------------"
        print "1. User: Create user"
        print "2. User: Change password"
        print "--------------------"
        action = input("\nChoose action: ")
        try:    
            actions[action]()
            return
        except KeyError:
            pass
        except Exception as e:
            print "ERROR: %s" % str(e)
    
if __name__ == "__main__":
    main()