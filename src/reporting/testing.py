import json
import datetime

instance = "i-1234567"
status = "compliant"


#summary = []

#summary[instance] = []
summary = {instance:[{"Status": status}]}
summ = json.dumps(summary)
print(summ)

print(datetime.datetime.now().date())

print(datetime.datetime.utcnow().replace(second=0, microsecond=0))

print(datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-%p'))