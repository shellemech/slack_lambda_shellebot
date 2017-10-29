# slack_lambda_shellebot

Python handler for a custom slack app.

When a new message is posted in the channel, the Slack event API hooks out to my API GW, which triggers the Lambda.
If the message has the search syntax it runs the ec2 query using boto3, and returns the result to slack.

![](https://i.imgur.com/nABUoXe.png)
