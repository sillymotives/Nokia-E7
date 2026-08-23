# AT capability evidence

Captured: 2026-08-23

The responsive AT channel is Nokia Suite interface `01`. The host device name
was `/dev/ttyACM0` during these captures but is not treated as durable.

## Status

| Query | Result | Interpretation |
| --- | --- | --- |
| `AT+CPAS` | `2` | Activity status unknown |
| `AT+CBC` | `1,14` | Battery connected; externally powered; 14% remaining |
| `AT+CFUN?` | `0` | Minimum cellular functionality |
| `AT+CSQ` | `99,99` | Signal and error rate unknown/not detectable |
| `AT+CSCS?` | `UTF-8` | UTF-8 AT text supported |
| SIM/registration/operator | Error | No usable cellular context exposed |
| `AT+CCLK?` | Error | Clock not readable through this AT channel |

The numeric interpretations follow ETSI TS 127 007 / 3GPP TS 27.007.

## Management surfaces

- `AT+CLAC` returned a broad command catalogue.
- SMS PDU and text modes are supported (`CMGF` values 0 and 1), but `CPMS`
  exposed no message stores.
- `CPBS` and `CPBR` returned errors, so contacts are not available through the
  standard AT phonebook commands.
- Keypad emulation is advertised as `CKPD:(GSM)`.
- Nokia backlight control supports states 0, 1, and 2; state 2 was active.
- Standard `CMEC` control mode is not exposed.

## Boundary

The catalogue includes call, SMS-send, SIM, registration, packet-data,
password, persistent-profile, reset, and Nokia manufacturer/test commands.
Enumeration is not authorisation. No command outside an explicit per-probe
allowlist may be transmitted.

