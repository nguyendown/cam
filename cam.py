import time
import requests
import subprocess

from yaml import safe_load, dump

ALERT_STREAM_PATH = "/ISAPI/Event/notification/alertStream"

config_path = "config.yaml"
config_template = """
host:
username:
password:
connect_timeout: null
retry_interval: 2
retry_command: play-audio -s notification retry.ogg
retry_command_interval: 7
default_command: play-audio -s notification event.ogg
default_command_interval: 5
channels: null
"""

config_channel = """
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
    current_time = time.time()
    if (
        retry_command
        and current_time - retry_command_interval > last_retry_command_time
    ):
        subprocess.Popen(retry_command, shell=True)
        last_retry_time = current_time
    print("retry in", retry_interval)
    time.sleep(retry_interval)


def main():
    last_command_time_list = {}
    data = safe_load(config_template)

    try:
        with open(config_path, "r") as f:
            new_data = safe_load(f)
            data.update(new_data)
    except IOError as e:
        print("exception caught:", e)

    # print(data)

    host = data.get("host")
    if not host:
        host = input("enter host: ")
        data["host"] = host

    username = data.get("username")
    if not username:
        username = input("enter username: ")
        data["username"] = username

    password = data.get("password")
    if not password:
        password = input("enter password: ")
        data["password"] = password

    connect_timeout = data.get("connect_timeout") or 1

    global retry_interval
    global retry_command
    global retry_command_interval
    global last_retry_command_time
    retry_interval = data.get("retry_interval") or 0
    retry_command = data.get("retry_command")
    retry_command_interval = data.get("retry_command_interval") or 0
    last_retry_command_time = 0

    default_command = data.get("default_command")
    default_command_interval = data.get("default_command_interval") or 0

    channels = data.get("channels")
    if not channels:
        data.update(safe_load(config_channel))
        channels = data["channels"]

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
                timeout=(connect_timeout, None),
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

                if channel_id not in channels:
                    continue

                start = chunk.find(b"<dateTime>", end) + 10
                end = chunk.find(b"<", start)
                date_time = chunk[start:end]

                start = chunk.find(b"<eventType>", end) + 11
                end = chunk.find(b"<", start)
                event_type = chunk[start:end].decode()

                event_types = channels[channel_id]["event_types"]
                if event_type in event_types:
                    current_time = time.time()
                    last_command_time = last_command_time_list.get(event_type) or 0
                    command_interval = (
                        event_types[event_type]["interval"]
                        or default_command_interval
                        or 0
                    )
                    command = (
                        event_types[event_type]["command"]
                        or channels[channel_id]["channel_command"]
                        or default_command
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
