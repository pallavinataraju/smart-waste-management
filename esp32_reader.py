
import serial
import json
import time
import requests

PORT = "COM9"
BAUD_RATE = 115200

DJANGO_URL = "http://127.0.0.1:8000/api/sensor-data/"

# Remember the latest valid fill readings.
last_wet_fill = None
last_dry_fill = None


def valid_fill(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 0 <= value <= 100
    )


def read_esp32():
    global last_wet_fill, last_dry_fill

    try:
        with serial.Serial(PORT, BAUD_RATE, timeout=2) as esp:
            print("Connected to ESP32 on", PORT)
            time.sleep(2)

            while True:
                line = esp.readline().decode(
                    "utf-8", errors="ignore"
                ).strip()

                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # Ignore non-JSON debug messages.
                    continue

                print("\nSensor data:", data)

                wet_fill = data.get("wet_bin_fill_percent")
                dry_fill = data.get("dry_bin_fill_percent")

                if valid_fill(wet_fill):
                    last_wet_fill = wet_fill

                if valid_fill(dry_fill):
                    last_dry_fill = dry_fill

                is_deposit_event = (
                    data.get("deposit_verified") is True
                    and isinstance(data.get("deposit_event_id"), int)
                    and not isinstance(data.get("deposit_event_id"), bool)
                )

                # Forward ordinary readings when both cached values
                # are available, or forward a deposit event immediately.
                if (
                    last_wet_fill is not None
                    and last_dry_fill is not None
                ) or is_deposit_event:

                    payload = data.copy()

                    # Keep the last known valid fill values if a
                    # sensor temporarily returns null.
                    if last_wet_fill is not None:
                        payload["wet_bin_fill_percent"] = last_wet_fill

                    if last_dry_fill is not None:
                        payload["dry_bin_fill_percent"] = last_dry_fill

                    print("Sending data to Django...")

                    try:
                        response = requests.post(
                            DJANGO_URL,
                            json=payload,
                            timeout=3
                        )

                        print("Django status:", response.status_code)
                        print("Django response:", response.text)

                    except requests.RequestException as error:
                        print("Django connection error:", error)

                else:
                    print(
                        "Waiting for valid readings from both bins. "
                        "No cached reading is available yet."
                    )

    except serial.SerialException as error:
        print("Serial connection error:", error)


if __name__ == "__main__":
    read_esp32()
