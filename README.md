# lambda-challenge

The following assumptions are made in order for this lambda function to 
run properly.

1. Environmental variables imported via os.environ are properly identified
    in the Lambda function configuration
2. A CloudTrail Trail is configured to send API activity to an S3 bucket
3. The S3 bucket has an event configured to trigger the Lambda function 

Future iterations could also take some of the functions below and place them
into a Lambda layer for re-use. Could also expand on slack alerting to alert on
error codes and other response types in a seperate python file to import.
