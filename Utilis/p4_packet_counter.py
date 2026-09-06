"""Read P4 switch transmit counters and print them as JSON."""
import argparse
import json
import sys

from bfrt_grpc import client as gc
import time

COUNTER_FIELDS = {
    "tx_ok": "$FramesTransmittedOK",
    "tx_all": "$FramesTransmittedAll",
    "tx_error": "$FramesTransmittedwithError",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--switch", required=True)
    parser.add_argument("--dev-ports", required=True, nargs="+", type=int)
    parser.add_argument("--client-id", required=True, type=int)
    args = parser.parse_args()

    interface = None
    try:
        interface = gc.ClientInterface(
            args.switch,
            client_id=args.client_id,
            device_id=0,
            # perform_subscribe=False
        )

        bfrt_info = interface.bfrt_info_get()
        interface.bind_pipeline_config(bfrt_info.p4_name_get())

        target = gc.Target(device_id=0, pipe_id=0xffff)
        port_stat = bfrt_info.table_get("$PORT_STAT")
        keys = [
            port_stat.make_key([gc.KeyTuple("$DEV_PORT", port)])
            for port in args.dev_ports
        ]
        wanted = port_stat.make_data(
            [gc.DataTuple(field) for field in COUNTER_FIELDS.values()],
            get=True,
        )

        devices = {}
        totals = {name: 0 for name in COUNTER_FIELDS}
        responses = port_stat.entry_get(
            target,
            keys,
            {"from_hw": True},
            wanted,
        )

        for data, key in responses:
            port = str(key.to_dict()["$DEV_PORT"]["value"])
            raw_counters = data.to_dict()
            counters = {
                name: int(raw_counters[field])
                for name, field in COUNTER_FIELDS.items()
            }
            devices[port] = counters
            for name, value in counters.items():
                totals[name] += value

        missing_ports = set(map(str, args.dev_ports)) - set(devices)
        if missing_ports:
            raise RuntimeError(
                f"No counter response for device ports: {sorted(missing_ports)}"
            )
        # change int to str to avoid json.dumps() error when the number is too large
        for device, counters in devices.items():
            devices[device] = {name: str(value) for name, value in counters.items()}
        totals = {name: str(value) for name, value in totals.items()}
            
        print(json.dumps({"devices": devices, "total": totals}))
    finally:
        if interface is not None:
            interface.tear_down_stream()


if __name__ == "__main__":
    start = time.perf_counter()
    main()
    print(
        f"Time taken: {time.perf_counter() - start:.3f} seconds",
        file=sys.stderr,
    )
