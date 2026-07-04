```
<<<<INITIAL MANUAL SET UP BEFORE RUNNING SCRIPT>>>>
1.aws configure
AWS Access Key ID [****************FHNK]: 
AWS Secret Access Key [****************utQD]: 
Default region name [us-east-1]:
Default output format [json]:

2.aws configure --profile tttt4

3. (i)Deactivate the acces key from aws profile
(ii)copy and replace arm with (your arn) add it in below command
steps to get arn--- >  IAM >IAM users > your user > Multi-factor authentication (MFA) (1) > Identifier 

aws sts get-session-token --serial-number (your arn) --token-code 031186(authenticator code) --profile tttt4

{
    "Credentials": {
        "AccessKeyId": "ASIAT5NNY7YBDU",
        "SecretAccessKey": "y23lcDdvCB5ti",
        "SessionToken": "IQoJb3JpZ2luX2VjEEkaCmFwLXNvdXRoLTEiRzBFAiEAxAlwuKjYK7+vDXVcvmxuF6/klz31iGeM2Nz7HuGCqJPyoUXD3p23N7nErsPquj5vouklhrtFnAj6MBa83us+4F1we/r+z+umBqWVV1NWmv7qQ+TDt+qNDn6Wpf9z2MEGKJjGtyKbFextR6pkGK3CKLKJiVpnd7AdXwNM4XNUeLNLGqYiQ==",
        "Expiration": "2026-06-12T20:59:45+00:00"
    }
}

Temporary credentials copy in notepad

4. Change the Temporary credentials with creds and run below three commands

aws configure set aws_access_key_id ASIAT5NBJR5 --profile temp-creds-tttt4
aws configure set aws_secret_access_key y23lcoFLRaDyrWoQdvCB5ti --profile temp-creds-tttt4
aws configure set aws_session_token IQoJb3JpZ2luX2VjEEkaCmFwLXNvdXRoLTEiRzBFAiEAxAlwuKjYK7+vDXVcvmxuF6/klz31iGe7vTwtafRAQif4y9tQAT4RS4ow6yr1KnosaZl2yKbFextR6pkGK3CKLKJiVpnd7AdXwNM4XNUeLNLGqYiQ== --profile temp-creds-tttt4

5. Confirm the config using below command
aws sts get-caller-identity --profile temp-creds-tttt4

6. Use below commands to clone the git repo 
search codecommit > clone URL > HTTPS (GRC) > replace profile name
(i)pip install git-remote-codecommit

(ii)git clone codecommit::us-east-1://your-profile-name tttt4@doc-translate-ai-agent 

7. Before pull and push config git global user.email and user.username

git config --global user.name
git config --global user.email


```



```
<<<<<<<<<<<<<<<< STEPS TO RUN THE SCRIPT>>>>>>>>>>>>>>>
Change line number 44 replace the arn with your arn and line 35 add your own username of aws

Initilly we have to go into aws console : 
IAM > users > your user > create access and secret key and use those in below commands

1. SET PROFILE RUN  BELOW COMMAND

Run > aws configure --profile tttt4

AWS Access Key ID [****************FHNK]: 
AWS Secret Access Key [****************utQD]: 
Default region name [us-east-1]:
Default output format [json]:

2. It will ask for number press 1 hit enter
3. It will ask for MFA enter MFA before it expires and enter

Ultimatly this script will delete the console generated creds and will config the temp creds which will work for on 12 hours
