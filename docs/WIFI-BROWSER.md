# Wi-Fi and browser capability

Captured: 2026-08-23

## Proven local-network path

The E7 manually opened a same-subnet plain-HTTP page served from the host. The
probe accepted eight requests from the local subnet and rejected none. The
E7-identifying root request, stylesheet, JavaScript, GIF, favicon, capability
beacons, and XHR request all completed.

The XHR returned HTTP status 200. This proves working E7-to-host Wi-Fi, HTTP,
multi-resource page loading, JavaScript execution, and same-origin asynchronous
requests without relying on external DNS or modern TLS.

## Browser identity and geometry

- Platform: Symbian/3, Series60/5.3.
- Device: Nokia E7-00.
- Firmware embedded in user agent: `111.040.1511`.
- Rendering engine: AppleWebKit/535.1, Mobile Safari/535.1 compatibility.
- Physical browser screen report: 640×360.
- Document viewport during the probe: 640×284.
- Device pixel ratio: 1.

The initial probe's conservative IPv4 redactor also replaced the dotted Nokia
Browser application version because it syntactically resembled an IPv4
address. The WebKit version and all capability conclusions were unaffected.
Version 2 of the probe redacts only the exact host/client addresses.

## JavaScript feature presence

The browser reported these interfaces as present:

- JavaScript and XMLHttpRequest;
- touch events;
- canvas;
- HTML audio and video elements;
- local storage and application cache;
- WebSocket;
- geolocation.

Web Workers were not present.

Feature presence does not prove full standards conformance, codec support,
remote service compatibility, or permission success. Each feature needed by a
future application should receive a focused behavioural test.

## Advertised download content

The HTTP `Accept` header included XHTML, HTML, XML, Java archives and JAD
descriptors, OMA DRM/download types, Nokia widgets, OPML, and generic content.
This is useful evidence for choosing delivery formats, but it is not proof that
an unsigned package can be installed or that a downloaded application will
run.

The browser accepted gzip and deflate transfer encodings and sent English as
its primary language preference.
