# DNS Cache Poisoning Attack Documentation

## Part 2: DNS Cache Poisoning Attack (Race Condition Exploitation)

### Attack Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Docker Network: 10.0.0.0/24                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    1. DNS Query     ┌─────────────┐                        │
│  │   Victim    │ ───────────────────► │  Resolver   │                        │
│  │ 10.0.0.10   │                      │ 10.0.0.20   │                        │
│  └─────────────┘                      └─────────────┘                        │
│       │                                     │                               │
│       │                                     │                               │
│       │                           2. SIMULTANEOUS QUERIES                   │
│       │                           (Cache Miss Scenario)                     │
│       │                                     │                               │
│       │                              ┌──────┴──────┐                        │
│       │                              │             │                        │
│       │                              ▼             ▼                        │
│       │                       ┌─────────────┐ ┌─────────────┐               │
│       │                       │ Proxy-DNS   │ │  Attacker   │               │
│       │                       │ 10.0.0.40   │ │ 10.0.0.50   │               │
│       │                       │             │ │             │               │
│       │                       │ 500ms DELAY │ │ 0ms INSTANT │               │
│       │                       └─────────────┘ └─────────────┘               │
│       │                              │             │                        │
│       │                              │             │                        │
│       │                              ▼             │                        │
│       │                       ┌─────────────┐      │                        │
│       │                       │  Auth-DNS   │      │                        │
│       │                       │ 10.0.0.30   │      │                        │
│       │                       │             │      │                        │
│       │                       │ LEGITIMATE  │      │ MALICIOUS              │
│       │                       │ 10.0.0.80   │      │ 10.0.0.50              │
│       │                       └─────────────┘      │                        │
│       │                              │             │                        │
│       │                              │             │                        │
│       │                   3. RACE RESULTS:         │                        │
│       │                   ┌─────────────────────────┼─────────────────────┐  │
│       │                   │ SLOW: ~530ms           │ FAST: ~5ms          │  │
│       │                   │ (arrives 2nd)          │ (arrives 1st)       │  │
│       │                   │ ▲                      │ ▲                   │  │
│       │                   │ │                      │ │                   │  │
│       │                   │ │        🏁 FIRST RESPONSE WINS! 🏁         │  │
│       │                   │ │                      │ │                   │  │
│       │                   │ │                      │ │                   │  │
│       │                   │ │              ┌───────┴─┴──────┐            │  │
│       │                   │ │              │   Resolver     │            │  │
│       │                   │ │              │ 💾 CACHE LOGIC │            │  │
│       │                   │ │              │ First = Cached │            │  │
│       │                   │ │              │ Later = Ignored│            │  │
│       │                   │ │              └───────┬────────┘            │  │
│       │                   │ │                      │                     │  │
│       │                   │ └──────────────────────┼─────────────────────┘  │
│       │                   └────────────────────────┼────────────────────────┘
│       │                                             │
│       │                   4. 🚨 CACHE POISONED! 🚨   │
│       │                   www.bank.lab → 10.0.0.50  │
│       │                   (TTL: 10 seconds)          │
│       │                                             │
│       │    5. DNS Response                          │
│       │ ◄──────────────────────────────────────────┘
│       │    (Poisoned IP)
│       │                                   
│       │                                   
│  ┌─────────────┐                         
│  │ Victim Now  │ 6. HTTP Traffic to EVIL SERVER
│  │ Connects To │ ────────────────────────────────────┐
│  │ 10.0.0.50   │                                     │
│  │ (Thinking   │          Phishing Website           ▼
│  │ it's bank)  │                               ┌─────────────┐
│  └─────────────┘                               │ Attacker's  │
│                                                │ Phishing    │
│                                                │ Server      │
│                                                │ 10.0.0.50   │
│                                                │             │
│                                                │ Fake Bank   │
│                                                │ Login Page  │
│                                                └─────────────┘
│                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Attack Configuration

**Resolver Configuration (Modified for Attack):**
```bash
options {
    directory "/var/cache/bind";
    recursion yes;
    allow-query { any; };
    forwarders { 10.0.0.50; 10.0.0.40; };  # BOTH attacker AND proxy!
    forward only;
    dnssec-validation no;
};
```

**Key Attack Components:**
- **Target Domain**: `www.bank.lab`
- **Legitimate IP**: `10.0.0.80` (Real bank server)
- **Poisoned IP**: `10.0.0.50` (Attacker's malicious server)
- **Attack Vector**: Race condition timing exploitation

### Race Condition Attack Flow

#### Phase 1: Attack Setup

```
┌─────────────┐
│  Attacker   │    1. Start malicious DNS server
│ 10.0.0.50   │ ──────────────────────────────────► [attack.py listening on port 53]
└─────────────┘                                     
                   2. Ready to respond INSTANTLY
                      to any DNS query with poison IP
```

#### Phase 2: The Race Begins (Cache Miss Scenario)

```
Victim Query: dig www.bank.lab (CACHE MISS)
┌─────┐    1. DNS Query        ┌─────────┐
│     │ ─────────────────────► │         │
│     │    www.bank.lab        │         │
│     │                        │         │    
│     │                        │         │    2. Resolver queries BOTH SIMULTANEOUSLY:
│     │                        │ Resolver│    ┌─────────────────────────────────────┐
│     │                        │         │ ───┤ • 10.0.0.50 (Attacker) - INSTANT   │
│     │                        │         │    │ • 10.0.0.40 (Proxy) - 500ms DELAY  │
│ Victim                       │         │    └─────────────────────────────────────┘
│     │                        │         │           │              │
│     │                        │         │           │              │
│     │                        │         │           ▼              ▼
│     │                        │         │    ┌─────────────┐ ┌─────────────┐
│     │                        │         │    │ Attacker    │ │ Proxy-DNS   │
│     │                        │         │    │ 10.0.0.50   │ │ 10.0.0.40   │
│     │                        │         │    │             │ │ 500ms DELAY │
│     │                        │         │    │ INSTANT     │ │             │
│     │                        │         │    │ RESPONSE    │ └─────────────┘
│     │                        │         │    └─────────────┘       │
│     │                        │         │           │              │
│     │                        │         │           │              ▼
│     │                        │         │           │       ┌─────────────┐
│     │                        │         │           │       │ Auth-DNS    │
│     │                        │         │           │       │ 10.0.0.30   │
│     │                        │         │           │       │ Returns:    │
│     │                        │         │           │       │ 10.0.0.80   │
│     │                        │         │           │       └─────────────┘
│     │                        │         │           │              │
│     │                        │         │           │              │
│     │                        │         │    3. RACE OUTCOME:      │
│     │                        │         │    ┌─────────────────────┼──────────┐
│     │                        │         │    │ ~5ms: Attacker      │ ~530ms:  │
│     │                        │         │ ◄──┤ responds FIRST      │ Proxy    │
│     │                        │         │    │ www.bank.lab        │ responds │
│     │                        │         │    │ → 10.0.0.50         │ SECOND   │
│     │                        │         │    │ 💾 CACHED!          │ (ignored)│
│     │                        │         │    └─────────────────────┼──────────┘
│     │                        │         │                         │
│     │    4. Poisoned Response│         │    ⚠️  CACHE POISONED!    │
│     │ ◄──────────────────────│         │    First response wins   │
│     │    www.bank.lab        │         │    Cached for 10 seconds │
│     │    → 10.0.0.50 (EVIL!) │         │                         │
└─────┘                        └─────────┘                         │
                                                    Legitimate response
                                                    arrives too late → IGNORED
```

### Critical Cache Behavior:

```
🏁 THE RACE:
   ├─ Attacker (10.0.0.50): Responds in ~5ms  → WINNER! (Gets cached)
   └─ Proxy → Auth (10.0.0.40 → 10.0.0.30): Responds in ~530ms → IGNORED

📝 CACHE LOGIC:
   1. First response received = Gets cached (TTL: 10 seconds)
   2. Subsequent responses = Completely ignored (cache already exists)
   3. All future queries = Served from poisoned cache

⚠️  RESULT: www.bank.lab → 10.0.0.50 (cached for 10 seconds)
```

### Detailed Timing Analysis

#### Race Condition Timeline (Cache Miss):

```
Time    Event                                   Server          Status
────────────────────────────────────────────────────────────────────────
T=0ms   Victim sends DNS query                 Victim          Query start
T=2ms   Resolver receives query                Resolver        Cache MISS
T=3ms   Resolver checks forwarders config      Resolver        Both servers listed
T=5ms   Resolver sends SIMULTANEOUS queries    Resolver        Race begins!
        ├─ Query to 10.0.0.50 (Attacker)                     
        └─ Query to 10.0.0.40 (Proxy)                        

T=6ms   Attacker receives query                Attacker        Instant processing
T=7ms   Attacker crafts malicious response     Attacker        Poison: 10.0.0.50
T=8ms   Attacker sends response                Attacker        → Resolver
T=9ms   Resolver receives FIRST response       Resolver        🚨 POISON CACHED!
T=10ms  Resolver responds to victim            Resolver        Game over

T=11ms  Proxy receives query                   Proxy           Start 500ms delay
T=511ms Proxy delay completes                  Proxy           Forward to auth
T=515ms Proxy forwards to Auth DNS             Proxy           → 10.0.0.30
T=525ms Auth DNS processes query               Auth-DNS        Legitimate response
T=530ms Auth DNS responds                      Auth-DNS        www.bank.lab → 10.0.0.80
T=535ms Proxy receives auth response           Proxy           Forward to resolver  
T=540ms Proxy sends to resolver                Proxy           Too late!
T=541ms Resolver receives SECOND response      Resolver        ❌ IGNORED (cached)

🎯 FINAL RESULT: Cache poisoned with 10.0.0.50 for 10 seconds!
   ├─ Attacker wins race: 9ms response time
   ├─ Proxy loses race: 540ms response time  
   └─ Cache entry: www.bank.lab → 10.0.0.50 (TTL: 10s)
```

### Cache Miss vs Cache Hit Behavior

#### Scenario 1: Cache Miss (Attack Window)
```bash
# No cached entry exists
$ docker exec resolver rndc flush  # Clear cache
$ docker exec victim dig "@10.0.0.20" www.bank.lab

# Result: Race condition triggered
# Winner: Attacker (first response)
# Cache: www.bank.lab → 10.0.0.50 (poisoned)
```

#### Scenario 2: Cache Hit (No Attack Possible)
```bash
# Cached entry exists (within 10-second TTL)
$ docker exec victim dig "@10.0.0.20" www.bank.lab  # Immediate from cache
$ docker exec victim dig "@10.0.0.20" www.bank.lab  # Still from cache
$ docker exec victim dig "@10.0.0.20" www.bank.lab  # Still from cache

# Result: No upstream queries sent
# Response: Cached result (poisoned or legitimate)
# Time: ~5ms (cache lookup only)
```

#### Scenario 3: Cache Expiration (Attack Window Reopens)
```bash
# Wait for TTL expiration (10 seconds)
$ sleep 11
$ docker exec victim dig "@10.0.0.20" www.bank.lab

# Result: Cache miss again → New race condition
# Opportunity: Attacker can poison cache again
```

### Key Attack Principles

#### 1. Simultaneous Query Exploitation
```
Resolver Configuration:
forwarders { 10.0.0.50; 10.0.0.40; };

Behavior:
├─ Cache Miss → Resolver queries ALL forwarders simultaneously
├─ Cache Hit  → Resolver serves from cache (no upstream queries)
└─ First Response → Gets cached, subsequent responses ignored
```

#### 2. Speed-Based Cache Poisoning
```
🏃‍♂️ Attacker Strategy:
   ├─ Listen on port 53
   ├─ Respond INSTANTLY to queries
   ├─ Inject poison IP (10.0.0.50)
   └─ Win race condition

🐌 Legitimate Path Weakness:
   ├─ Proxy introduces 500ms delay
   ├─ Auth DNS processing time
   ├─ Multiple network hops
   └─ Always loses the race
```

#### 3. Cache Behavior Exploitation
```
DNS Cache Logic:
┌─────────────────────────────────────────────────────────────┐
│ if (cache_entry_exists && ttl_not_expired):                │
│     return cached_response  # No upstream queries          │
│ else:                                                       │
│     query_all_forwarders()  # Race condition opportunity   │
│     cache_first_response()  # Winner takes all             │
│     ignore_subsequent_responses()                           │
└─────────────────────────────────────────────────────────────┘

Attack Window:
├─ Cache Miss: Vulnerable to poisoning
├─ Cache Hit: Attack not possible  
└─ Cache Expiry: Vulnerable again
```

### Cache Poisoning Impact

#### Before Attack:
```bash
$ dig @10.0.0.20 www.bank.lab
; ANSWER SECTION:
www.bank.lab.    10    IN    A    10.0.0.80    # ✓ Legitimate
```

#### During Attack:
```bash
$ python3 attack.py  # Attacker starts malicious DNS server
$ dig @10.0.0.20 www.bank.lab
; ANSWER SECTION:  
www.bank.lab.    10    IN    A    10.0.0.50    # ✗ POISONED!
```

#### Attack Persistence:
```bash
# Cache remains poisoned for TTL duration (10 seconds)
$ dig @10.0.0.20 www.bank.lab  # Still poisoned
$ dig @10.0.0.20 www.bank.lab  # Still poisoned
$ dig @10.0.0.20 www.bank.lab  # Still poisoned
# ... for 10 seconds until cache expires
```

### Attack Demonstration Sequence

#### Step 1: Environment Setup
```bash
# 1. Ensure attack configuration in resolver
# File: resolver/named.conf.options
# Verify: forwarders { 10.0.0.50; 10.0.0.40; };

# 2. Start environment
docker-compose down
docker-compose up --build -d

# 3. Verify services are running
docker ps | grep -E "(resolver|attacker|proxy|auth)"
```

#### Step 2: Clear Cache (Create Attack Window)
```bash
# Clear resolver cache to ensure cache miss
docker exec resolver rndc flush

# Verify cache is empty
docker exec resolver rndc dumpdb -cache
docker exec resolver cat /var/cache/bind/named_dump.db | grep bank.lab
# Should return nothing (cache empty)
```

#### Step 3: Start Attack Server
```bash
# Terminal 1: Start malicious DNS server
docker exec -it attacker python3 attack.py

# Expected output:
# 🚀 Starting malicious DNS server...
# 📋 Attack Strategy:
#    1. Resolver forwards to BOTH proxy (slow) and attacker (fast)
#    2. Proxy has 500ms delay
#    3. Attacker responds immediately with poison IP
#    4. First response wins!
# ✅ DNS server started! Waiting for queries...
```

#### Step 4: Execute Attack (Trigger Race Condition)
```bash
# Terminal 2: Monitor in real-time
docker logs -f resolver &
docker logs -f proxy-dns &

# Terminal 3: Victim performs DNS query (triggers race)
time docker exec victim dig "@10.0.0.20" www.bank.lab

# Expected timing: ~10ms response (fast = poisoned)
# Expected result: www.bank.lab → 10.0.0.50
```

#### Step 5: Verify Cache Poisoning Success
```bash
# Test multiple queries to confirm cache poisoning
for i in {1..5}; do
  echo "Query $i:"
  docker exec victim dig "@10.0.0.20" www.bank.lab +short
  sleep 1
done

# Expected: All queries return 10.0.0.50 (poisoned IP)
# Timing: All responses ~5ms (from cache)
```

#### Step 6: Monitor Attack Logs
```bash
# Attacker terminal should show:
# [HH:MM:SS] 🎯 FAST RESPONSE: www.bank.lab -> 10.0.0.50 (from 10.0.0.20)

# Proxy logs should show:
# [DELAY] Adding 500ms delay for query from 10.0.0.20:XXXXX
# [FORWARD] Forwarding query to auth server 10.0.0.30:53
# [RESPONSE] Sending response back to 10.0.0.20:XXXXX
```

#### Step 7: Demonstrate Cache Persistence
```bash
# Show that poisoned cache persists for TTL duration
echo "Testing cache persistence (10-second TTL):"
for i in {1..12}; do
  echo "Second $i: $(docker exec victim dig "@10.0.0.20" www.bank.lab +short)"
  sleep 1
done

# Expected behavior:
# Seconds 1-10: Returns 10.0.0.50 (poisoned, from cache)
# Second 11+: May return legitimate IP if cache expires and no attack running
```

### Attack Success Indicators

#### 1. Timing Evidence
```bash
# Fast response indicates cache poisoning
$ time docker exec victim dig "@10.0.0.20" www.bank.lab

# Attack Success (Poisoned):
# Response time: ~10ms (first query after cache clear)
# Answer: www.bank.lab → 10.0.0.50

# Normal Operation (Legitimate):  
# Response time: ~530ms (first query after cache clear)
# Answer: www.bank.lab → 10.0.0.80
```

#### 2. Cache Analysis
```bash
# Dump and examine resolver cache
$ docker exec resolver rndc dumpdb -cache
$ docker exec resolver cat /var/cache/bind/named_dump.db | grep -A3 -B3 bank.lab

# Attack Success Shows:
# www.bank.lab.    [TTL]  IN  A  10.0.0.50
#                         ↑       ↑
#                    remaining    poisoned IP
#                      time
```

#### 3. Consistent Poisoned Responses
```bash
# All queries within TTL return same poisoned IP
$ for i in {1..5}; do docker exec victim dig "@10.0.0.20" www.bank.lab +short; done

# Attack Success Output:
# 10.0.0.50
# 10.0.0.50  
# 10.0.0.50
# 10.0.0.50
# 10.0.0.50
```

#### 4. Attacker Log Confirmation
```bash
# Attacker server logs successful poisoning
[HH:MM:SS] 🎯 FAST RESPONSE: www.bank.lab -> 10.0.0.50 (from 10.0.0.20)
[HH:MM:SS] ✅ Cache poisoning successful!
```

### Attack Impact Assessment

#### Immediate Technical Impact:
- **DNS Resolution**: `www.bank.lab` → `10.0.0.50` (attacker's server)
- **Cache Duration**: 10 seconds of sustained poisoning
- **User Impact**: All bank website access redirected to attacker
- **Network Effect**: Affects all users using poisoned resolver

#### Security Consequences:
```
🔴 CRITICAL: Complete DNS hijacking achieved
   ├─ Victim believes attacker's server is legitimate bank
   ├─ All HTTP/HTTPS traffic redirected to attacker
   ├─ Perfect setup for credential harvesting
   └─ User has no indication of compromise

⚠️  STEALTH: Attack is invisible to end user
   ├─ DNS queries return normally (just wrong IP)
   ├─ No error messages or warnings
   ├─ Browser shows intended domain name
   └─ SSL warnings only if attacker lacks valid certificate
```

#### Real-World Scenario Simulation:
1. **User Intent**: Visit legitimate bank website
2. **DNS Query**: `www.bank.lab` 
3. **Poisoned Response**: `10.0.0.50` (attacker's server)
4. **User Action**: Connects to attacker unknowingly
5. **Exploitation**: Phishing site captures credentials

This poisoned DNS state creates the perfect foundation for the phishing attack demonstrated in Part 3, where the victim will unknowingly connect to the attacker's fake banking website.

### Attack Limitations

1. **TTL Bound**: Attack effect lasts only 10 seconds (zone TTL)
2. **Single Domain**: Only affects `www.bank.lab` queries
3. **Race Dependency**: Requires timing advantage over legitimate servers
4. **Detection Risk**: Unusual DNS response patterns may trigger alerts

### Security Implications

**Immediate Impact:**
- Victim believes `www.bank.lab` is at `10.0.0.50`
- All HTTP traffic redirected to attacker's server
- Perfect setup for phishing attacks

**Extended Impact:**
- User credentials harvesting
- Session hijacking opportunities  
- Man-in-the-middle attack platform
- Trust relationship exploitation

This cache poisoning attack creates the foundation for the phishing exploitation demonstrated in Part 3.

---