# DNS Cache Poisoning and Phishing Attack Demonstration

## Part 1: Normal DNS Operation (Without Attack)

### Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Docker Network: 10.0.0.0/24                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    DNS Query     ┌─────────────┐    Forward    ┌─────────────┐
│  │   Victim    │ ───────────────► │  Resolver   │ ─────────────► │ Proxy-DNS   │
│  │ 10.0.0.10   │                  │ 10.0.0.20   │               │ 10.0.0.40   │
│  └─────────────┘                  └─────────────┘               └─────────────┘
│       │                                 │                             │
│       │                                 │                             │ 500ms delay
│       │                                 │                             ▼
│       │                           Cache Storage               ┌─────────────┐
│       │                           (TTL: 10s)                 │  Auth-DNS   │
│       │                                 │                    │ 10.0.0.30   │
│       │                                 │                    └─────────────┘
│       │            DNS Response         │                           │
│       │ ◄───────────────────────────────┘                           │
│       │                                                             │
│       │                                                             │
│       │                          Zone: bank.lab                    │
│       │                          www.bank.lab → 10.0.0.80          │
│       │                                                             │
│  ┌─────────────┐                                              ┌─────────────┐
│  │Legitimate   │                                              │ Bank Server │
│  │Bank Website │ ◄────────────────────────────────────────────┤ 10.0.0.80   │
│  │             │              HTTP Traffic                    │             │
│  └─────────────┘                                              └─────────────┘
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Configuration for Normal Operation

**Resolver Configuration (`/etc/bind/named.conf.options`):**
```bash
options {
    directory "/var/cache/bind";
    recursion yes;
    allow-query { any; };
    forwarders { 10.0.0.40; };  # Only proxy (legitimate path)
    forward only;
    dnssec-validation no;
};
```

**Expected Result:**
- Domain: `www.bank.lab`
- Valid IP: `10.0.0.80` (Legitimate bank server)
- Poisoned IP: `10.0.0.50` (Attacker's server)

### Operation Flow

#### Scenario 1: First Query (Cache Miss - Uncached)

```
Step-by-Step Process:
┌─────┐    1. dig www.bank.lab    ┌─────────┐
│     │ ──────────────────────► │         │
│     │                         │         │    2. Forward Query
│     │                         │         │ ──────────────────► ┌─────────┐
│     │                         │         │                     │         │
│     │                         │ Resolver│                     │ Proxy   │
│     │                         │         │                     │         │
│     │                         │         │                     │         │ 3. Add 500ms delay
│     │                         │         │                     │         │ ────────────────►
│     │                         │         │                     │         │
│ Victim                        │         │                     │         │    4. Forward to Auth
│     │                         │         │                     │         │ ──────────────────► ┌─────────┐
│     │                         │         │                     │         │                     │         │
│     │                         │         │    6. Return Response│         │                     │ Auth-DNS│
│     │                         │         │ ◄──────────────────────────────┤    5. DNS Response  │         │
│     │                         │         │    (Cache for 10s)   │         │ ◄──────────────────────────────┤
│     │    7. DNS Response      │         │                     │         │                     │         │
│     │ ◄────────────────────── │         │                     │         │                     │         │
│     │    www.bank.lab         │         │                     └─────────┘                     └─────────┘
│     │    → 10.0.0.80          │         │
└─────┘                         └─────────┘

Total Time: ~500ms+ (Network + Proxy Delay + Auth Response)
```

**Timeline:**
1. **T=0ms**: Victim sends DNS query to resolver
2. **T=5ms**: Resolver forwards query to proxy
3. **T=10ms**: Proxy receives query, starts 500ms delay
4. **T=510ms**: Proxy forwards to authoritative DNS
5. **T=520ms**: Auth DNS responds with 10.0.0.80
6. **T=525ms**: Proxy returns response to resolver
7. **T=530ms**: Resolver caches result (TTL: 10s) and responds to victim

**Result**: `www.bank.lab` → `10.0.0.80` (✅ Legitimate)

#### Scenario 2: Subsequent Query (Cache Hit - Cached)

```
Step-by-Step Process:
┌─────┐    1. dig www.bank.lab    ┌─────────┐
│     │ ──────────────────────► │         │
│     │                         │         │
│     │                         │         │    2. Check Cache
│     │                         │         │ ──────────────┐
│     │                         │ Resolver│               │
│     │                         │         │ ◄─────────────┘
│     │                         │         │    Cache Hit!
│ Victim                        │         │    (TTL remaining)
│     │                         │         │
│     │    3. Immediate Response │         │
│     │ ◄────────────────────── │         │
│     │    www.bank.lab         │         │
│     │    → 10.0.0.80          │         │
└─────┘    (from cache)         └─────────┘

Total Time: ~5-10ms (Cache lookup only)
```

**Timeline:**
1. **T=0ms**: Victim sends DNS query to resolver
2. **T=2ms**: Resolver checks cache, finds entry
3. **T=3ms**: Cache hit! TTL still valid (< 10 seconds old)
4. **T=5ms**: Resolver responds immediately from cache

**Result**: `www.bank.lab` → `10.0.0.80` (✅ Legitimate, Fast)

### Performance Comparison

| Query Type | Response Time | Cache Status | Network Calls | Result |
|------------|---------------|--------------|---------------|---------|
| **First Query** | ~530ms | Miss | 3 hops | 10.0.0.80 |
| **Cached Query** | ~5ms | Hit | 0 hops | 10.0.0.80 |

### Cache Behavior Analysis

**TTL (Time To Live) Settings:**
- **Zone TTL**: 10 seconds (from db.bank.lab)
- **Negative Cache TTL**: 10 seconds
- **Cache Duration**: Response cached for 10 seconds

**Cache Lifecycle:**
```
T=0s:    First query → Cache miss → Full resolution chain → Cache entry created
T=1-9s:  Subsequent queries → Cache hit → Immediate response
T=10s:   Cache expires → Next query will be cache miss
T=10s+:  Cache miss → Full resolution chain → New cache entry
```

### Demonstration Commands

**Setup Environment:**
```bash
# Start the environment
docker-compose down
docker-compose up --build -d

# Configure resolver for normal operation (edit resolver/named.conf.options)
# Change forwarders to: forwarders { 10.0.0.40; };
# Then rebuild: docker-compose up resolver --build -d
```

**Test Cache Miss (First Query):**
```bash
# Clear any existing cache first
docker exec resolver rndc flush

# Test first query (should take ~500ms+)
time docker exec victim dig "@10.0.0.20" www.bank.lab

# Expected output:
# www.bank.lab.    10    IN    A    10.0.0.80
# Query time: ~530 msec
```

**Test Cache Hit (Subsequent Query):**
```bash
# Test immediate follow-up query (should be fast)
time docker exec victim dig "@10.0.0.20" www.bank.lab

# Expected output:
# www.bank.lab.    [remaining TTL]    IN    A    10.0.0.80
# Query time: ~5 msec
```

**Verify Cache Status:**
```bash
# Check resolver cache
docker exec resolver rndc dumpdb -cache
docker exec resolver cat /var/cache/bind/named_dump.db | grep bank.lab
```

**Monitor Logs:**
```bash
# Watch resolver logs
docker logs -f resolver

# Watch proxy logs  
docker logs -f proxy-dns

# Watch auth DNS logs
docker logs -f auth-dns
```

### Key Observations

1. **Normal Operation**: DNS resolution follows proper hierarchy
2. **Performance Impact**: 500ms delay demonstrates network latency effects
3. **Cache Efficiency**: Subsequent queries served instantly from cache
4. **Security**: All responses are legitimate (10.0.0.80)
5. **TTL Management**: 10-second cache prevents excessive upstream queries

This establishes the baseline for comparison with attack scenarios in subsequent parts.

---