Shelly 2PM Pro monitoring for Prometheus
========================================

This is a simple Python script that allows to convert status information
from Shelly 2PM Pro (other models comming), and export using Prometheus
exposition format.


Requirements
============

Python 3.7+

Python packages: `requests` (In the future this requirement will be removed)

On Debian/Ubuntu: `apt install python3-requests`

Alternatively use pip3 directly: `pip3 install -r requirements.txt`

Usage
=====

Run exporter:

```shell
$ ./shelly.py
INFO:root:Server running on port 19991
```

By default it will listen on all interfaces on port `19991`

Run with `--help` to see some extra configuration options.

This exporter uses target pattern, similar to blackbox and snmp
exporters. Pass IP (or DNS name) in a target query parameter.

Example to test, assuming two of your Shellies has address `10.0.0.8` and
`10.0.0.9`

Test:

 - http://localhost:19991/metrics?target=10.0.0.8
 - http://localhost:19991/metrics?target=10.0.0.9

For quick tests, you can also run exporter in a text mode. For example:
`./shelly.py --default_targets=10.0.0.8,10.0.0.9 --once`

Once you are happy with test results, configure your Prometheus.

Example `prometheus.yml`

```yaml
scrape_configs:
  # .. other jobs

  - job_name: "shelly"
    scrape_interval: 5s
    static_configs:
      - targets:
        - "10.0.0.8"
        labels:
          model: "shelly_2pm"
          name: "hall_light"
      - targets:
        - "10.0.0.9"
        labels:
          model: "shelly_2pm"
          name: "bedroom"
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: localhost:19991  # The shelly exporter's real hostname:port.
```

If you plan to only monitor one shelly, just run exporter with
`--default_target=10.0.0.8` for example, and use simpler Prometheus
config file:

```yaml
scrape_configs:
  # .. other jobs

  - job_name: "shelly"
    scrape_interval: 5s
    static_configs:
      - targets:
        - "localhost:19991"
      - labels:
          model: "shelly_2pm"
          name: "hall_light"
```

Note: Exporter also supports querying multiple shellies, using multiple
`target` query parameters:

Example: http://localhost:19991/metrics?target=10.0.0.8&target=10.0.0.9

This is not recommended beyond simple tests, as targets are queries
sequentially (not in parallel), and if one of them is down, it could
cause entire scrape to file due to timeout.

Note: If the target cannot be reached or exception is thrown during
processing data from Shelly, exporter will not return any metrics, and
terminate HTTP request from Prometheus. This is by design, and not a bug.
You can use standard (and always present) `up` metric to detect exporter
or Shelly being down in alerts.

TODO
====

- Support 1PM Pro, 4PM Pro, etc.
- Use `urllib3` or `http.client` directly instead of `requests`
- Resolve shelly bug 23769, causing 2PM Pro to reboot every few
  hours or days, depending on frequency of scrapes.
- When scraping multiple shellies (using multiple target arguments),
  metrics are not sorted optimally.
- `standard_metrics` function is very Linux-specific
