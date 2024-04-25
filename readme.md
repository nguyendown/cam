Usage
=====

``` shell
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

``` shell
source .venv/bin/activate
python3 cam.py
```

Script sẽ đọc config từ file `config.yaml`. Nếu không có file config,
nó sẽ yêu cầu nhập `host`, `username` và `password`.

```
enter host: https://192.168.1.20
enter username: user
enter password: password
```

Config sẽ được lưu lại để không cần phải nhập lại trong các lần chạy
tiếp theo.

Config
======

`host`: Địa chỉ camera/NVS. (`http://192.168.1.20`)

`username`: Username. User phải có quyền "Remote: Notify Surveillance
Center / Trigger Alarm Output"

`password`: Password.

`connect_timeout`: Timeout khi kết nối đến `host`.

`retry_interval`: Khoảng thời gian giữa các lần thử lại kết nối.

`retry_command`: Command mỗi khi thử lại kết nối.

`retry_command_interval`: Khoảng thời gian giữa các cần chạy `retry_command`.

`default_command`: Command mỗi khi có event.

`default_command_interval`: Khoảng thời gian giữa các lần chạy `default_command`.

`channels`: Danh sách các channel cần theo dõi.

Channel
-------

`channel_command`: Command riêng của channel. Override config `default_command`.

`events`: Danh sách các event cần theo dõi e.g. VMD, linedetection.

Event
-----

`command`: Command riêng của event. Override config `channel_command`
và `default_command`.

`interval`: Khoảng thời gian giữa các lần chạy command.

Command
=======

play-audio
----------

Nhanh. Ảnh hưởng đến cuộc gọi.

```
play-audio -s notification event.ogg
```

termux-notification
-------------------

Chậm hơn. Không ảnh hưởng đến cuộc gọi.

```
termux-notification -i 1
```
