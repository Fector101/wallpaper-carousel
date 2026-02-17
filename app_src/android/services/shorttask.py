import os, time, traceback
from android_notify import Notification

receiver_arg = os.environ.get('PYTHON_SERVICE_ARGUMENT', "")
print("python Shorttask arg", receiver_arg)

fmt = lambda s: f"{int((s % 3600) // 60)}m {int(s % 60)}s"

n = Notification(title="Scheduled Service runtime: --:--")

n.send()

mins = 60 * 15
try:
    for i in range(0, mins):
        n.updateTitle(f"Scheduled Service runtime: {fmt(i)}")
        time.sleep(1)
except Exception as error_in_short_task:
    print(error_in_short_task)
    traceback.print_exc()
