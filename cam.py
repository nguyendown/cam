import argparse
import os
import time
import requests
import subprocess
import traceback

from pathlib import Path
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
    events:
      VMD:
        command: null
        interval: 3
      linedetection:
  5:
    channel_command: play-audio -s notification ch5.ogg
    events:
      VMD:
        command: play-audio -s notification vmd.ogg
        interval: 7
      linedetection:
        command: null
        interval: 5
  6:
    events:
      linedetection:
"""


def retry():
    global last_retry_command_time
    current_time = time.time()
    if (
        retry_command
        and current_time - retry_command_interval > last_retry_command_time
    ):
        subprocess.Popen(retry_command, shell=True)
        last_retry_command_time = current_time
    print("retry in", retry_interval)
    time.sleep(retry_interval)


def process_chunk(chunk):
    # print(chunk)
    start = chunk.find(b"hannelID>") + 9
    end = chunk.find(b"<", start)
    channel_id = int(chunk[start:end])

    if channel_id not in channels:
        return

    start = chunk.find(b"<dateTime>", end) + 10
    end = chunk.find(b"<", start)
    date_time = chunk[start:end]

    start = chunk.find(b"<eventType>", end) + 11
    end = chunk.find(b"<", start)
    event = chunk[start:end].decode()

    events = channels[channel_id].get("events")
    if event in events:
        print("{0:2} | {1} | {2}".format(channel_id, date_time.decode(), event))

        event_config = events.get(event)
        current_time = time.time()
        t = last_command_time_list.get(channel_id)
        last_command_time = t.get(event) if t else 0
        command_interval = (
            event_config.get("interval") if event_config else None
        ) or default_command_interval
        command = (
            (event_config.get("command") if event_config else None)
            or channels[channel_id].get("channel_command")
            or default_command
        )
        if command and current_time - last_command_time >= command_interval:
            subprocess.Popen(command, shell=True)
            last_command_time_list[channel_id] = {}
            last_command_time_list[channel_id][event] = current_time


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", help="Config path.")
    parser.add_argument("-t", "--test", help="Test chunks.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )

    args = parser.parse_args()

    current_path = Path(__file__).absolute().parent
    config_path = args.config or current_path / "config.yaml"
    os.chdir(current_path)

    global last_command_time_list
    last_command_time_list = {}
    config = safe_load(config_template)

    try:
        with open(config_path, "r") as f:
            new_config = safe_load(f)
            config.update(new_config)
    except IOError as e:
        print("exception caught:", e)

    global verbose
    verbose = args.verbose or config.get("verbose") or False
    if verbose:
        print(config)

    host = config.get("host")
    if not host:
        host = input("enter host: ")
        config["host"] = host

    username = config.get("username")
    if not username:
        username = input("enter username: ")
        config["username"] = username

    password = config.get("password")
    if not password:
        password = input("enter password: ")
        config["password"] = password

    connect_timeout = config.get("connect_timeout")

    global retry_interval
    global retry_command
    global retry_command_interval
    global last_retry_command_time
    retry_interval = config.get("retry_interval") or 0
    retry_command = config.get("retry_command")
    retry_command_interval = config.get("retry_command_interval") or 0
    last_retry_command_time = 0

    global default_command
    global default_command_interval
    default_command = config.get("default_command")
    default_command_interval = config.get("default_command_interval") or 0

    global channels
    channels = config.get("channels")
    if not channels:
        config.update(safe_load(config_channel))
        channels = config["channels"]

    if args.test:
        with open(args.test, "rb") as f:
            for chunk in f:
                process_chunk(chunk)
        return

    try:
        with open(config_path, "w") as f:
            dump(config, f, sort_keys=False)
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
                process_chunk(chunk)

        except KeyboardInterrupt:
            break
        except Exception as e:
            if verbose:
                traceback.print_exc()
            else:
                print("exception caught:", e)
            retry()
            continue

        print("socket closed")
        retry()


if __name__ == "__main__":
    main()
