# Seeding Data Scenarios

## Overview
16 customer scenarios across 3 risk tiers designed to test fraud detection.

## Clean Customers (Expected: APPROVE)
1. **Sarah Chen** - Reliable Regular (18 months, 80 trades, standard activity)
2. **James Wilson** - VIP Whale (3 years, 150 trades, high volume)
...

## Medium Risk (Expected: ESCALATE)
7. **David Park** - Business Traveler (VPN + multi-country IPs)
...

## Fraud Customers (Expected: BLOCK)
11. **Victor Petrov** - No-Trade Fraudster (shared device with Sophie)
...

## Fraud Pattern Summary
- Shared devices: 4 customers
- Shared IPs: 2 customers
- Velocity abuse: 1 customer (5 withdrawals/hour)
- Impossible travel: 1 customer (Kyiv → São Paulo in 30min)
