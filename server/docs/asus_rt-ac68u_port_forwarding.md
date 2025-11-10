# ASUS RT-AC68U FastAPI Hosting Guide

This note combines the WAN port-forwarding walkthrough for the ASUS RT-AC68U and the
steps to recover if a new DHCP reservation temporarily breaks connectivity on macOS.

## Configure Port Forwarding

1. Sign in to the router dashboard at `http://192.168.1.1` (default user/pass is
   `admin/admin` unless changed).
2. Reserve a LAN IP for the Mac running FastAPI:
   - `Advanced Settings → LAN → DHCP Server`.
   - Under **Manually Assigned IP**, add the Mac's Wi-Fi MAC address (see
     `System Settings → Network → Wi-Fi → Details… → Hardware`) and choose an unused
     IP inside the DHCP pool, e.g. `192.168.1.50`.
   - Click **Add**, then **Apply** and reconnect the Mac so it picks up the reserved IP.
3. Create the port-forwarding rules:
   - Go to `Advanced Settings → WAN → Virtual Server / Port Forwarding`.
   - Enable port forwarding if it is disabled.
   - Add an entry for FastAPI:
     - **Service Name:** `FastAPI`
     - **Port Range:** `8000` (or the external port you prefer)
     - **Local IP:** `192.168.1.50`
     - **Local Port:** `8000`
     - **Protocol:** `TCP`
   - (Optional) Add a second entry for the static HTML host:
     - **Service Name:** `StaticDemo`
     - **Port Range:** `5500`
     - **Local IP:** `192.168.1.50`
     - **Local Port:** `5500`
     - **Protocol:** `TCP`
   - Click the **+** button after each entry, then **Apply** to save.
4. Verify the router's WAN IP: `Network Map → Internet status`. It should match the WAN
   address printed by the `.command` scripts (e.g. `96.241.xxx.xxx`). If not, you may be
   behind upstream NAT or CGNAT and will need to expose the service using an upstream
   port-forward or a tunneling solution (ngrok, Tailscale, Cloudflare Tunnel, etc.).
5. Confirm the firewall is allowing forwarded traffic:
   - `Advanced Settings → Firewall → General`.
   - Ensure the firewall is enabled but not blocking the forwarded port. No extra rule is
     typically required once the Virtual Server entry exists.
6. Optional hardening:
   - `Advanced Settings → WAN → DDNS` to configure an ASUS DDNS hostname.
   - Consider enabling HTTPS or a reverse proxy for long-term exposure.

After the rules are active and `run_fastapi.command` is running, test from an external
network (e.g. mobile hotspot) using `http://<WAN-IP>:8000/`.

## Recover Mac Connectivity After DHCP Changes

If the Mac loses internet access immediately after creating the DHCP reservation:

1. On macOS, open `System Settings → Network → Wi-Fi → Details… → TCP/IP`.
   - Ensure **Configure IPv4** is `Using DHCP`.
   - Click **Renew DHCP Lease** (or toggle Wi-Fi off/on) to obtain a fresh address.
2. Reboot the Mac if it still does not pick up the reserved IP.
3. Revisit the router's `LAN → DHCP Server` page and verify:
   - The DHCP server remains enabled.
   - The reserved IP is inside the DHCP pool (default `192.168.1.2 – 192.168.1.254`).
   - Gateway (`192.168.1.1`) and subnet mask (`255.255.255.0`) are correct.
   - DNS fields are populated (ISP defaults or `8.8.8.8`/`1.1.1.1`).
4. If the Mac still cannot connect:
   - Temporarily delete the reservation, apply, and reconnect to restore connectivity.
   - Choose a different unused IP inside the DHCP pool and recreate the reservation.
   - Avoid manual IP assignments on the Mac that fall outside the router's subnet.

Once the Mac successfully renews the lease and obtains the reserved address, the port
forwarding rules will route WAN traffic to the FastAPI server without further
adjustments.
