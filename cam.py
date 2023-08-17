import time
import requests
import subprocess

from yaml import load, dump
from yaml import Loader, Dumper

ALERT_STREAM_PATH = "/ISAPI/Event/notification/alertStream"

config_path = "config.yaml"
config_yaml = """
host:
username:
password:
retry_interval: 2
retry_command: play-audio -s notification retry.ogg
command: play-audio -s notification event.ogg
channels:
  4:
    channel_command: termux-notification -i 1
    event_types:
      VMD:
        command: null
        interval: 3
  5:
    channel_command: play-audio -s notification ch5.ogg
    event_types:
      VMD:
        command: play-audio -s notification vmd.ogg
        interval: 7
      linedetection:
        command: null
        interval: 5
"""


def retry():
    if retry_command:
        subprocess.Popen(retry_command, shell=True)
    print("retry in", retry_interval)
    time.sleep(retry_interval)


def main():
    last_command_time_list = {}

    try:
        with open(config_path, "r") as f:
            data = load(f, Loader=Loader)
    except IOError as e:
        print("exception caught:", e)
        data = load(config_yaml, Loader=Loader)

    # print(data)

    host = data["host"]
    if not host:
        host = input("enter host: ")
        data["host"] = host

    username = data["username"]
    if not username:
        username = input("enter username: ")
        data["username"] = username

    password = data["password"]
    if not password:
        password = input("enter password: ")
        data["password"] = password

    global retry_interval
    global retry_command
    retry_interval = data["retry_interval"] or 2
    retry_command = data["retry_command"]

    try:
        with open(config_path, "w") as f:
            dump(data, f, sort_keys=False)
    except Exception as e:
        print("exception caught:", e)

    session = requests.Session()

    while True:
        try:
            response = session.get(
                host + ALERT_STREAM_PATH,
                auth=requests.auth.HTTPDigestAuth(username, password),
                verify=False,
                stream=True,
            )

            if response.status_code != 200:
                print(response.status_code, "auth failed.")
                retry()
                continue

            print("auth success")
            print("ID | Date time           | Event type")

            raw = response.raw
            while not raw.closed:
                chunk = raw.read(128)
                start = chunk.find(b"Content-Length: ") + 16
                end = chunk.find(b"\r\n\r\n", start)
                content_length = int(chunk[start:end])
                chunk = chunk[end + 4 :] + raw.read(content_length - 128 + end + 4)
                # print(chunk)

                start = chunk.find(b"hannelID>", end) + 9
                end = chunk.find(b"<", start)
                channel_id = int(chunk[start:end])

                if channel_id not in data["channels"]:
                    continue

                start = chunk.find(b"<dateTime>", end) + 10
                end = chunk.find(b"<", start)
                date_time = chunk[start:end]

                start = chunk.find(b"<eventType>", end) + 11
                end = chunk.find(b"<", start)
                event_type = chunk[start:end].decode()

                event_types = data["channels"][channel_id]["event_types"]
                if event_type in event_types:
                    current_time = time.time()
                    last_command_time = last_command_time_list.get(event_type) or 0
                    command_interval = (
                        data["channels"][channel_id]["event_types"][event_type][
                            "interval"
                        ]
                        or 0
                    )
                    command = (
                        data["channels"][channel_id]["event_types"][event_type][
                            "command"
                        ]
                        or data["channels"][channel_id]["channel_command"]
                        or data["command"]
                    )
                    if command and current_time - last_command_time >= command_interval:
                        subprocess.Popen(command, shell=True)
                        last_command_time_list[event_type] = current_time

                    print(
                        "{0:2} | {1} | {2}".format(
                            channel_id, date_time.decode(), event_type
                        )
                    )
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("exception caught:", e)
            retry()
            continue

        print("socket closed")
        retry()


if __name__ == "__main__":
    main()