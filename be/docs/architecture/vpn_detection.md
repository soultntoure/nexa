# VPN Detection — Why We Mock It

## The Problem

Our fraud detection system needs to know whether a user is connecting through a VPN. In production, this is handled by **IP intelligence providers** (MaxMind, IPQualityScore, ip2location) that maintain databases of known VPN/proxy/datacenter IP ranges. You send an IP, they return `is_vpn: true/false` with ~85-95% accuracy.

We don't integrate a live provider because:

1. **Cost** — these are paid APIs with per-request pricing
2. **Scope** — this is a hackathon prototype, not a production deployment
3. **Determinism** — mocked data gives us repeatable test scenarios

## How We Handle It

The seed data includes `is_vpn` as a boolean on each IP history record. This simulates what the IP intelligence API would return. The geographic indicator reads this field and applies a **low penalty (+0.1)** because VPN usage is common on trading platforms — many legitimate users use VPNs for privacy.

## VPN vs Impossible Travel

These are different signals:

| Signal | Question | Example |
|--------|----------|---------|
| **VPN** | "Is this IP anonymized?" | David connects from NLD via NordVPN |
| **Impossible travel** | "Could this person physically be here?" | Nina logs in from Kyiv, then São Paulo 2 hours later |

VPN detection flags anonymization. Impossible travel flags physically contradictory locations regardless of VPN — both IPs can be real, non-VPN addresses that are simply too far apart given the time between logins.

## Production Integration

To replace the mock with a real provider:

1. Add an IP lookup service (e.g., `MaxMindService.lookup(ip) -> IPMetadata`)
2. Call it during withdrawal evaluation before indicators run
3. Inject the result into the indicator context (`ctx["is_vpn"]`, `ctx["ip_location"]`)
4. No indicator logic changes needed — they already consume these fields
