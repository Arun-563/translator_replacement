#see the comments at last to add new clusters.
import os
import sys
from tkinter import N
import shutil
import zipfile
from shutil import make_archive
from datetime import datetime
import json
import subprocess
import configparser
# printing list

accname=""
profile=""
my_dict = {'1': 'tttt4'}

for x,y in my_dict.items():
    print(x, ":" , y)     

account=input("select number :")

print("selected value is: "+my_dict[account])

match my_dict[account]:
    
    case "tttt4":
        accname="269336772098"
        profile="tttt4"
    
    case _:
        print("Please select proper value")
# variables i am using

username = "gopal.ad"
#accname=430059503983 now taking it from switch statement
print("selected account is :"+str(accname))
print("selected profile is :"+str(profile))
# taking inputs

tokencode=input("Enter  token code: ")
#profile="arizona" now taking it from switch statement

os.system("aws sts get-session-token --serial-number arn:aws:iam::269336772098:mfa/gopal.ad --token-code {2} --profile {3} > credentials.json ".format(accname,username,tokencode,profile) )


# json part

fp=open("credentials.json")
data=json.load(fp)
#print("Here is the data whic we have imported\n",data)
#  Use the slicing to get a particular value from a json file.
Accessid=(data['Credentials']['AccessKeyId'])
#print("Accessid is:"+Accessid)
Secretid=(data['Credentials']['SecretAccessKey'])
#print("Secretid is:"+Secretid)
SessionTokenid=(data['Credentials']['SessionToken'])
#print("SessionTokenid is:"+SessionTokenid)
fp.close()

#os.system("myfile.bat > myfile2.json")


# print("aws sts get-session-token --serial-number arn:aws:iam::"+accname+":mfa/"+username+" --token-code "+ tokencode + " --profile "+ profile)

# login codes creation

file2 = open("login.bat","w")
file2.write( "aws configure set aws_access_key_id {0} --profile temp-creds-{1}\n\n".format(Accessid,profile))

file2.write( "aws configure set aws_secret_access_key {0}  --profile temp-creds-{1}\n\n".format(Secretid,profile))

file2.write( "aws configure set aws_session_token {0} --profile temp-creds-{1}\n\n".format(SessionTokenid,profile))
file2.close()

# running the code

os.system("login.bat")


os.remove("credentials.json")
#os.remove("myfile.bat")
os.remove("login.bat")

print('''

Logins are :''')

match my_dict[account]:
    case "tttt4":
         print("Temp Token Configured Successfully")

    case _:
        print("Please select proper value")
        
def retrieve_access_key(profile):
    # Get the current user's home directory
    home_dir = os.path.expanduser("~")
    # Define the path to the AWS credentials file
    credentials_file = os.path.join(home_dir, '.aws', 'credentials')
 
    try:
        # Load the AWS credentials file
        config = configparser.RawConfigParser()
        config.read(credentials_file)
 
        # Get the access key ID for the specified profile
        access_key_id = config.get(profile, 'aws_access_key_id')
 
        return access_key_id
 
    except Exception as e:
        print("An error occurred:", str(e))
 
def deactivate_access_key(access_key_id, profile):
    try:
        tempcreds = "temp-creds-" + profile
        # Deactivate the access key
        subprocess.run(['aws', 'iam', 'update-access-key', '--access-key-id', access_key_id, '--status', 'Inactive', '--profile', tempcreds])
 
        print(f"Access key with ID '{access_key_id}' for profile '{profile}' has been deactivated.")
 
    except Exception as e:
        print("An error occurred:", str(e))
 
# Retrieve the access key ID for the specified profile
access_key_id = retrieve_access_key(profile)
 
# If access key ID is retrieved successfully, deactivate the access keys
if access_key_id:
    deactivate_access_key(access_key_id, profile)
else:
    print(f"Access key ID not found for profile '{profile}'.")