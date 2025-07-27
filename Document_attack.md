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
Resolver Configuration: forwarders { 10.0.0.50; 10.0.0.40; };

Cache Miss → Resolver queries ALL forwarders simultaneously
First Response → Gets cached, subsequent responses ignored
```

#### 2. Speed-Based Cache Poisoning
```
🏃‍♂️ Attacker: Instant response (~5ms) → WINS
🐌 Proxy: 500ms delay + Auth DNS (~530ms) → LOSES
```

#### 3. Cache TTL Exploitation
```
Poisoned Entry: www.bank.lab → 10.0.0.50 (cached for 10 seconds)
Attack Window: Reopens every time cache expires
```

---

## Part 3: Phishing Exploitation (HTTP Traffic Hijacking)

### Post-DNS Poisoning Attack Flow

Once DNS cache is poisoned (`www.bank.lab` → `10.0.0.50`), all HTTP traffic gets redirected to attacker's phishing server.

#### Phase 1: Victim Accesses Bank Website

```
┌─────┐    1. HTTP Request           ┌─────────────┐
│     │ ──────────────────────────► │   Resolver  │
│     │ curl http://www.bank.lab    │ 10.0.0.20   │
│     │                             └─────────────┘
│     │                                    │
│ Victim                                   │ 2. DNS Query (cached)
│     │                                    │ www.bank.lab
│     │                                    ▼
│     │                             ┌─────────────┐
│     │                             │    Cache    │
│     │                             │ 💾 POISONED │
│     │                             │ 10.0.0.50   │
│     │                             └─────────────┘
│     │                                    │
│     │    3. DNS Response                 │
│     │ ◄──────────────────────────────────┘
│     │    www.bank.lab → 10.0.0.50
│     │    (Poisoned IP)
│     │
│     │    4. HTTP Connection
│     │ ──────────────────────────────────────────┐
│     │                                           │
│     │                                           ▼
│     │                                    ┌─────────────┐
│     │                                    │  Attacker   │
│     │                                    │ 10.0.0.50   │
│     │                                    │             │
│     │                                    │ Phishing    │
│     │                                    │ Server      │
│     │                                    │ (Flask)     │
│     │                                    └─────────────┘
│     │                                           │
│     │    5. Fake Bank HTML Page                 │
│     │ ◄─────────────────────────────────────────┘
│     │    (Professional login form)
└─────┘
```

#### Phase 2: Credential Harvesting

```
┌─────┐    6. POST Login Credentials  ┌─────────────┐
│     │ ──────────────────────────► │  Attacker   │
│     │ username=victim@bank.lab    │ 10.0.0.50   │
│     │ password=mypassword123      │             │
│     │                             │ Phishing    │ 7. Save Credentials
│ Victim                            │ Server      │ ────────────────┐
│     │                             │             │                 │
│     │                             └─────────────┘                 ▼
│     │                                    │                ┌─────────────┐
│     │    8. Success Page + Redirect      │                │   /data/    │
│     │ ◄──────────────────────────────────┘                │ creds.log   │
│     │    "Login successful!"                              │             │
│     │    → Redirects to real bank                         │ victim@...  │
└─────┘                                                     │ mypass...   │
                                                           └─────────────┘
```

### Phishing Server Components

#### 1. Fake Bank Lab Website
- **Professional Design**: Mimics legitimate banking interface
- **SSL Appearance**: Shows secure styling to fool users
- **Login Form**: Captures username/password submissions
- **Realistic Branding**: Bank Lab logos and color scheme

#### 2. Credential Logging System
- **Real-time Capture**: Saves credentials immediately upon submission
- **Admin Dashboard**: `/admin` endpoint for monitoring captures
- **Persistent Storage**: Logs stored in `/data/creds.log`
- **Stealth Operation**: Redirects to real bank after capture

#### 3. Social Engineering Elements
- **Trust Indicators**: Security badges, SSL icons
- **Urgency Tactics**: Login prompts, session timeouts
- **Familiar Interface**: Matches expected banking experience

### Demonstration Commands

#### Setup Phishing Environment:
```bash
# 1. Ensure DNS is already poisoned (from Part 2)
docker exec victim dig "@10.0.0.20" www.bank.lab +short
# Should return: 10.0.0.50

# 2. Start phishing server
docker exec -it attacker python3 phishing_server.py
# Server starts on 10.0.0.50:80
```

#### Test HTTP Hijacking:
```bash
# Terminal 1: Monitor phishing server logs
docker exec -it attacker python3 phishing_server.py

# Terminal 2: Victim accesses bank website
docker exec victim curl http://www.bank.lab

# Expected: Returns fake banking HTML page
# Victim sees professional login form
```

#### Demonstrate Credential Theft:
```bash
# Victim submits login credentials
docker exec victim curl -X POST http://www.bank.lab/login \
  -d "username=victim@bank.lab&password=mypassword123" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Expected Results:
# 1. Attacker server logs: "🎯 CREDENTIAL CAPTURED!"
# 2. Victim receives: "Login Successful" page
# 3. Credentials saved to /data/creds.log
```

#### Verify Credential Capture:
```bash
# Check captured credentials
docker exec attacker cat /data/creds.log

# Expected output:
# [YYYY-MM-DD HH:MM:SS] CAPTURED - IP: 10.0.0.10 | Username: victim@bank.lab | Password: mypassword123 | User-Agent: curl/...

# Access admin dashboard
docker exec victim curl http://www.bank.lab/admin
# Shows real-time credential capture interface
```

### Attack Success Indicators

#### 1. DNS Redirection Success:
```bash
# All bank traffic goes to attacker
$ docker exec victim nslookup www.bank.lab
Server: 10.0.0.20
Address: 10.0.0.20:53

Name: www.bank.lab
Address: 10.0.0.50  # ✓ Attacker's server
```

#### 2. HTTP Traffic Hijacking:
```bash
# Victim gets phishing content
$ docker exec victim curl -s http://www.bank.lab | grep -i "bank lab"
<title>Bank Lab - Secure Login</title>
<h1>🏦 Bank Lab</h1>
# ✓ Phishing page served
```

#### 3. Credential Harvesting:
```bash
# Attacker logs show capture
[12:34:56] 🎯 CREDENTIAL CAPTURED!
   Time: 2025-01-27 12:34:56
   IP: 10.0.0.10
   Username: victim@bank.lab
   Password: mypassword123
# ✓ Credentials stolen
```

### Real-World Impact Simulation

#### User Experience (Victim's Perspective):
1. **Types**: `www.bank.lab` in browser
2. **DNS Resolution**: Happens invisibly (poisoned cache)
3. **Website Loads**: Professional banking interface appears
4. **Login Process**: Enters credentials normally
5. **Success Message**: "Login successful, redirecting..."
6. **Redirection**: Taken to real bank website
7. **No Suspicion**: Everything appears normal

#### Attacker Benefits:
- **Stolen Credentials**: Username and password captured
- **Session Data**: User-Agent, IP address logged
- **Persistence**: Multiple victims can be harvested
- **Stealth**: Attack remains undetected

#### Security Breach Scope:
- **Complete Account Takeover**: Attacker has banking credentials
- **Identity Theft**: Personal information compromised  
- **Financial Fraud**: Potential unauthorized transactions
- **Trust Exploitation**: User's confidence in DNS security undermined

This phishing exploitation demonstrates the complete attack chain: DNS poisoning → Traffic hijacking → Credential theft → Account compromise.

---

### Attack Limitations

1. **TTL Bound**: Attack effect lasts only 10 seconds (zone TTL)
2. **Race Dependency**: Requires timing advantage over legitimate servers  
3. **Detection Risk**: Unusual DNS response patterns may trigger alerts

### Next Phase: Phishing Exploitation

Once DNS cache is poisoned, the attacker can exploit the redirected traffic for credential harvesting, as demonstrated in Part 3 above.

---