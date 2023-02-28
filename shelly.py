#!/usr/bin/env python3

import argparse
import codecs
import datetime
import http.client
import http.server
import logging
import requests
import sys
import time
import traceback
import urllib.parse


def fetch_and_print(*, target, file):
    timeout = (2, 2)

    ip = target
    switches = {}
    inputs = {}
    ids = [0, 1]

    for id in ids:
        j = requests.get(
            f"http://{ip}/rpc/Switch.GetStatus?id={id}", timeout=timeout
        ).json()
        switches[id] = j
    # https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch#status
    # https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch#switchgetstatus-example
    # {'id': 0, 'source': 'WS_in', 'output': True,
    #  'apower': 23.4, 'voltage': 222.7, 'current': 0.181, 'pf': -0.59,
    #  'aenergy': {'total': 1.153, 'by_minute': [96.102, 413.148, 415.911], 'minute_ts': 1673789533},
    # 'temperature': {'tC': 29.8, 'tF': 85.7}}

    for id in ids:
        j = requests.get(
            f"http://{ip}/rpc/Input.GetStatus?id={id}", timeout=timeout
        ).json()
        inputs[id] = j
    # {"id":0,"state":false}

    # 40ms
    status = requests.get(f"http://{ip}/rpc/Sys.GetStatus", timeout=timeout).json()
    # {"mac":"30C6F78B8258","restart_required":false,"time":"18:54","unixtime":1673805251,"uptime":15938,"ram_size":233024,"ram_free":133100,"fs_size":524288,"fs_free":159744,"cfg_rev":17,"kvs_rev":2,"schedule_rev":0,"webhook_rev":0,"available_updates":{"stable":{"version":"0.12.0"}}}

    # 43ms
    # shelly = requests.get(f"http://{ip}/rpc/Shelly.GetStatus", timeout=timeout).json()
    # {"ble":{},"cloud":{"connected":false},"eth":{"ip":"10.0.0.8"},"input:0":{"id":0,"state":false},"input:1":{"id":1,"state":false},"mqtt":{"connected":false},"switch:0":{"id":0, "source":"WS_in", "output":true, "apower":0.0, "voltage":220.1, "current":0.022, "pf":-0.00, "aenergy":{"total":11.042,"by_minute":[0.000,0.000,0.000],"minute_ts":1673805430},"temperature":{"tC":41.5, "tF":106.7}},"switch:1":{"id":1, "source":"init", "output":false, "apower":0.0, "voltage":3.8, "current":0.000, "pf":0.00, "aenergy":{"total":0.000,"by_minute":[0.000,0.000,0.000],"minute_ts":1673805430},"temperature":{"tC":40.2, "tF":104.3}},"sys":{"mac":"30C6F78B8258","restart_required":false,"time":"18:57","unixtime":1673805431,"uptime":16117,"ram_size":233012,"ram_free":132196,"fs_size":524288,"fs_free":159744,"cfg_rev":17,"kvs_rev":2,"schedule_rev":0,"webhook_rev":0,"available_updates":{"stable":{"version":"0.12.0"}}},"wifi":{"sta_ip":"10.0.0.10","status":"got ip","ssid":"Turris1","rssi":-35},"ws":{"connected":false}}

    # 37ms
    dev = requests.get(f"http://{ip}/rpc/Shelly.GetDeviceInfo", timeout=timeout).json()
    # {"name":null,"id":"shellypro2pm-30c6f78b8258","mac":"30C6F78B8258","model":"SPSW-202PE16EU","gen":2,"fw_id":"20230112-154212/0.13.0-beta1-g74cb0dd","ver":"0.13.0-beta1","app":"Pro2PM","auth_en":false,"auth_domain":null,"profile":"switch"}

    def labels0(**kwargs):
        extra = ""
        for k, v in kwargs.items():
            extra += f',{k}="{v}"'
        return f'{{ip="{ip}"{extra}}}'

    def labels(id, **kwargs):
        return labels0(id=id, **kwargs)

    # by_minute array of numbers  Energy consumption by minute (in Milliwatt-hours) for the last three minutes (the lower the index of the element in the array, the closer to the current moment the minute)
    # minute_ts number Unix timestamp of the first second of the last minute (in UTC)

    # Input
    for id, j in inputs.items():
        print(f"shelly_input{labels(id)}", 1 if j["state"] else 0, file=file)

    # Switch
    for id, j in switches.items():
        print(f"shelly_output{labels(id)}", 1 if j["output"] else 0, file=file)
    for id, j in switches.items():
        if "apower" in j:
            print(f"shelly_active_power_W{labels(id)} {j['apower']:.1f}", file=file)
        else:
            print("Warning: no apower in ", j, file=sys.stderr)
    for id, j in switches.items():
        if "voltage" in j:
            print(f"shelly_voltage_V{labels(id)} {j['voltage']:.1f}", file=file)
        else:
            print("Warning: no voltage in ", j, file=sys.stderr)
    for id, j in switches.items():
        if "current" in j:
            print(f"shelly_current_A{labels(id)} {j['current']:.3f}", file=file)
        else:
            print("Warning: no current in ", j, file=sys.stderr)
    for id, j in switches.items():
        if j["output"] == False or j.get("current", 0.0) == 0.0:
            print(f"shelly_power_factor{labels(id)} NaN", file=file)
        else:
            print(f"shelly_power_factor{labels(id)} {j['pf']:.2f}", file=file)
    for id, j in switches.items():
        print(
            f"shelly_active_energy_total_Wh{labels(id)} {j['aenergy']['total']:.3f}",
            file=file,
        )
    for id, j in switches.items():
        print(
            f"shelly_temperature_celsius{labels(id)} {j['temperature']['tC']:.1f}",
            file=file,
        )
    for id, j in switches.items():
        print(
            f"shelly_temperature_fahrenheit{labels(id)} {j['temperature']['tF']:.1f}",
            file=file,
        )
    for id, j in switches.items():
        # not a counter, but gauge
        print(f"shelly_error_count{labels(id)} {len(j.get('errors', []))}", file=file)
    for id, j in switches.items():
        for error in j.get("errors", []):
            print(f"shelly_errors{labels(id, error=error)} 1", file=file)

    # timer_started_at number Unix timestamp, start time of the timer (in UTC) (shown if the timer is triggered)
    # timer_duration number Duration of the timer in seconds (shown if the timer is triggered)

    mac = status["mac"]

    # Sys
    print(f"shelly_uptime_seconds{labels0()} {status['uptime']}", file=file)
    print(f"shelly_ram_free_bytes{labels0()} {status['ram_free']}", file=file)
    print(f"shelly_ram_size_bytes{labels0()} {status['ram_size']}", file=file)
    print(f"shelly_fs_free_bytes{labels0()} {status['fs_free']}", file=file)
    print(f"shelly_fs_size_bytes{labels0()} {status['fs_size']}", file=file)
    print(f"shelly_info{labels0(mac=mac)} 1", file=file)
    print(
        f"shelly_restart_required{labels0()}",
        1 if status["restart_required"] else 0,
        file=file,
    )

    # dev
    print(
        f"shelly_dev_info{labels0(mac=mac,id=dev['id'],model=dev['model'],gen=dev['gen'],fw_id=dev['fw_id'],ver=dev['ver'],app=dev['app'],profile=dev['profile'])} 1",
        file=file,
    )


import mmap

page_size = mmap.PAGESIZE

# times = os.times()
# times.user
# times.system
# times.elapsed

clock_tick = 100

start_time = time.time()


# This is super ugly, and works only on Linux (and maybe some BSDs).
# On Windows it will throw, which is fine. These metrics are nice
# to have but not critical.
def standard_metrics(file):
    try:
        with open("/proc/self/stat") as f:
            stat = [0, ""] + f.readline().rsplit(") ", 1)[-1].split()
            print(f"process_virtual_memory_bytes {stat[23-1]}", file=file)
            print(
                f"process_resident_memory_bytes {int(stat[24-1]) * page_size}",
                file=file,
            )
            print(f"process_minor_faults_count {stat[10-1]}", file=file)
            print(f"process_major_faults_count {stat[12-1]}", file=file)
            print(f"process_thread_count {stat[20-1]}", file=file)
            # print(f"process_start_time_seconds {int(stat[22-1])/clock_tick}", file=file)  # This is seconds after boot.
            # utime + stime
            cpu_seconds = (int(stat[14 - 1]) + int(stat[15 - 1])) / clock_tick
            print(f"process_cpu_seconds_total {cpu_seconds}", file=file)
            print(f"process_start_time_seconds {start_time}", file=file)
            print(f"process_uptime_seconds {time.time() - start_time}", file=file)
            # process_open_fds  # This is not easy to get on Linux, and in most cases is not useful.
    except Exception as e:
        logging.info("Exception in standard_metrics: %s", e)
        # Continue normal execution


utf8_codec_writer = codecs.getwriter("utf-8")


class S(http.server.BaseHTTPRequestHandler):
    def _set_response(self, code=200, content_type="text/html"):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()

    def log_message(self, format, *args):
        t = datetime.datetime.now().isoformat()
        message = format % args
        logging.info(
            "%s %s %s",
            t,
            self.address_string(),
            message.translate(self._control_char_table),
        )

    def do_GET(self):
        t = time.time()
        try:
            self.handle_method("GET")
            self.log_message(
                '"%s" %s %s Finished in %.3f ms',
                self.requestline,
                "-",
                "-",
                (time.time() - t) * 1.0e3,
            )
        except Exception as e:
            ln = traceback.extract_tb(e.__traceback__, limit=205).format()
            ln = ";".join(ln)
            self.log_message(
                '"%s" %s %s Finished in %.3f ms with exception %s in %s',
                self.requestline,
                "-",
                "-",
                (time.time() - t) * 1.0e3,
                str(e),
                ln,
            )

    def handle_method(self, method):
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)

        if url.path == "/metrics":
            self.handle_metrics(query)
            return

        self._set_response(404)
        self.wfile.write(b"Not Found. Only /metrics request supported")

    def handle_metrics(self, params):
        targets = self.server.default_targets
        if "target" in params:
            targets = params["target"]

        self._set_response(200, "text/plain; version=0.0.4")
        f = utf8_codec_writer(self.wfile)
        for target in targets:
            fetch_and_print(target=target, file=f)
        standard_metrics(file=f)
        f.flush()


def run(*, port=8080, default_targets=[]):
    server_address = ("", port)
    with http.server.ThreadingHTTPServer(server_address, S) as httpd:
        httpd.allow_reuse_address = True
        httpd.request_queue_size = 10
        httpd.default_targets = default_targets
        httpd.timeout = 2.5
        logging.info("Server running on port %d", port)
        httpd.serve_forever()

    logging.info("Server stopped")


def once(args):
    for target in args.default_targets.split(","):
        fetch_and_print(target=target, file=sys.stdout)
    standard_metrics(file=sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        prog="shelly_exporter",
        description="Exports Prometheus metrics for Shelly accessories",
    )
    parser.add_argument("--port", type=int, default=19991)
    parser.add_argument("--default_targets", default="10.0.0.10")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Without starting server, perform one scrape, and output metrics to stdout. Then exit.",
    )
    args = parser.parse_args()

    if args.once:
        once(args)
    else:
        logging.basicConfig(level=logging.INFO)
        run(port=args.port, default_targets=args.default_targets.split(","))


if __name__ == "__main__":
    main()
