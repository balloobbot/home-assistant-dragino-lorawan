[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=balloobbot&repository=home-assistant-dragino-lorawan&category=integration)

# Dragino LoRaWAN

Use Dragino devices with Home Assistant's LoRaWAN connections.
Requires Home Assistant 2026.11.0b0 or newer, including 2026.11 beta releases.

## Install

1. Open the HACS link above and download the integration.
2. Restart Home Assistant.
3. Configure a connection supported by your device in the table below.
4. Add your device to the network server using its official catalog profile.
5. Open **Settings > Devices & services** and configure the discovered
   **Dragino LoRaWAN** integration. You can also select it under **Add integration**.

To install manually, copy `custom_components/dragino_lorawan` into your Home
Assistant `config/custom_components` directory and restart.

## Devices

| Model | Entities | Connections |
| --- | --- | --- |
| LT-22222-L | Two relays, two digital outputs, two digital inputs, voltage, current, and counters | ChirpStack and The Things Network / The Things Stack |
| LDS02 | Door state, open alarm, event count, last opening duration, and battery voltage | ChirpStack and The Things Network / The Things Stack |
| LWL02 | Water leak, event count, last leak duration, and battery voltage | ChirpStack and The Things Network / The Things Stack |
| LHT65 | Temperature, humidity, battery voltage, and external probe readings | The Things Network / The Things Stack |

LT-22222-L input measurements depend on its reporting mode. LHT65 illuminance,
external voltage, and external counter entities are disabled by default; enable
the ones that match your attached probe.

Relay and digital-output commands wait up to 30 seconds for acknowledgement.
Their state changes when the device reports it. A timeout does not remove a
queued command from the network server.

Devices are matched by catalog identity. Renaming a custom profile to a supported
model does not make it discoverable. One integration entry handles matching
devices across all configured LoRaWAN connections.

Readings remain unknown until an uplink or status report supplies them.

## Development

The device library is bundled under `custom_components/dragino_lorawan/_vendor`.
It uses the shared LoRaWAN dependency provided by Home Assistant.

Tests use Home Assistant's official pytest helpers and an in-memory connection.
They cover discovery, decoded readings, entity identity, connection loss,
reconnection, and removal, plus output commands and errors.
Payload tests use codec examples, including the ChirpStack LDS02 and LWL02 fixtures. LT-22222-L commands were also exercised against a simulated ChirpStack radio during the original PoC.

```sh
uv sync --group dev
uv run python script/prepare_tests.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The development environment pins Core and its test helpers to the same revision.
CI also tests current Home Assistant `dev`.

Payload references: [Dragino TTN codecs](https://github.com/TheThingsNetwork/lorawan-devices/tree/master/vendor/dragino).

LDS02 and LWL02 profiles were identified from [LoRaWANDeviceProfiles](https://github.com/BenAhrdt/LoRaWANDeviceProfiles/tree/main/DeviceProfiles/Dragino) and checked against the [ChirpStack catalog](https://github.com/chirpstack/chirpstack-device-profiles/tree/master/vendors/dragino).
