# Live DNS Defense Demo - Dedicated Container

## 🚀 Setup Environment

```powershell
# Start all containers
docker-compose up -d

# Verify all containers are running
docker ps
```

Expected containers:
- resolver (10.0.0.20) ← BIND DNS resolver
- proxy-dns (10.0.0.40) ← Delayed proxy
- auth-dns (10.0.0.30) ← Legitimate DNS
- auth-dns-2 (10.0.0.60) ← Second legitimate DNS
- attacker (10.0.0.50) ← Malicious DNS
- victim (10.0.0.10) ← Test client
- **defense (10.0.0.70)** ← NEW: Defense proxy container

---

## 📋 Live Demo Flow

### **Phase 1: Normal Operation (No Attack)**

```powershell
# Test normal DNS resolution
docker exec victim dig @10.0.0.20 www.bank.lab +short
```
**Expected Result**: `10.0.0.80` (legitimate from auth-dns servers)

---

### **Phase 2: Attack Running (No Defense)**

```powershell
# Terminal 1: Start the attack
docker exec -d attacker python3 /app/attack.py

# Terminal 2: Clear DNS cache and test
docker exec resolver rndc flush
docker exec victim dig @10.0.0.20 www.bank.lab +short
```

**Expected Result**: `10.0.0.50` (poisoned - attack succeeds!)

**Why Attack Succeeds:**
- Resolver queries: `10.0.0.70` (defense not running - fails)
- Falls back to: `10.0.0.50, 10.0.0.40, 10.0.0.60`
- Attacker (10.0.0.50) responds fastest → wins race condition

---

### **Phase 3: Defense Activated (Attack Still Running!)**

```powershell
# Terminal 3: Start defense (while attack.py still running!)
docker exec defense python3 /app/defense.py
```

**Defense Output:**
```
[DEFENSE] Starting DNS Defense Proxy on 10.0.0.70:53...
[DEFENSE] Monitoring servers: ['10.0.0.40', '10.0.0.60', '10.0.0.50']
[DEFENSE] Consensus threshold: 2 votes required
[DEFENSE] ✅ Defense proxy active - Ready to block attacks!
```

```powershell
# Terminal 2: Clear cache and test with defense active
docker exec resolver rndc flush
docker exec victim dig @10.0.0.20 www.bank.lab +short
```

**Defense Process (Terminal 3 shows):**
```
[DEFENSE] DNS query received from ('10.0.0.20', 12345)
[DEFENSE] Query for domain: www.bank.lab
[DEFENSE] Resolving www.bank.lab with consensus validation...
[DEFENSE] Server 10.0.0.40 returned: 10.0.0.80
[DEFENSE] Server 10.0.0.60 returned: 10.0.0.80
[DEFENSE] Server 10.0.0.50 returned: 10.0.0.50
[DEFENSE] Consensus analysis:
  10.0.0.80: 2 vote(s) from ['10.0.0.40', '10.0.0.60']
  10.0.0.50: 1 vote(s) from ['10.0.0.50']
[DEFENSE] ✅ CONSENSUS REACHED: 10.0.0.80 (2 votes >= 2 threshold)
[DEFENSE] ✅ Sent consensus response: www.bank.lab -> 10.0.0.80
```

**Expected Result**: `10.0.0.80` (legitimate - attack blocked!)

---

### **Phase 4: Defense Turned Off (Attack Resumes)**

```powershell
# Terminal 3: Stop defense (Ctrl+C)
# Attack.py still running in Terminal 1!

# Terminal 2: Clear cache and test without defense
docker exec resolver rndc flush  
docker exec victim dig @10.0.0.20 www.bank.lab +short
```

**Expected Result**: `10.0.0.50` (poisoned again - attack resumes!)

---

## 🔍 Architecture Overview

### **Resolver Configuration:**
```
forwarders { 10.0.0.70; 10.0.0.50; 10.0.0.40; 10.0.0.60; };
```

### **Defense OFF (10.0.0.70 not responding):**
```
Victim → Resolver → [10.0.0.70 FAIL] → Falls back to → [10.0.0.50, 10.0.0.40, 10.0.0.60]
                                                        ↓
                                                    Attacker wins race
                                                        ↓
                                                  Result: 10.0.0.50
```

### **Defense ON (10.0.0.70 active):**
```
Victim → Resolver → 10.0.0.70 (Defense) → Query [10.0.0.40, 10.0.0.60, 10.0.0.50] → Consensus
                          ↓                                                              ↓
                    Return 10.0.0.80                                            2 vs 1 voting
                                                                                     ↓
                                                                             Result: 10.0.0.80
```

---

## 📊 Demo Summary Table

| Phase | Attack Status | Defense Status | DNS Path | Result | Explanation |
|-------|---------------|----------------|----------|--------|-------------|
| 1 | ❌ Off | ❌ Off | Direct to auth servers | `10.0.0.80` | Normal operation |
| 2 | ✅ Running | ❌ Off | Falls back to race condition | `10.0.0.50` | Attacker wins race |
| 3 | ✅ Running | ✅ Running | Through defense proxy | `10.0.0.80` | Consensus blocks attack |
| 4 | ✅ Running | ❌ Off | Falls back to race condition | `10.0.0.50` | Attack resumes |

---

## 🎯 Key Demo Points for Teacher

1. **Clean Architecture**: Defense runs on dedicated IP (10.0.0.70)
2. **Valid BIND Config**: No custom ports, just IP addresses
3. **Live Switching**: Turn defense on/off without restarting containers
4. **Consensus Voting**: Shows exactly how 2 legitimate servers beat 1 attacker
5. **Seamless Fallback**: When defense stops, attack immediately resumes
6. **Real-time Logs**: Defense shows voting process in detail

## 🚨 Troubleshooting

### If resolver still fails to start:
```powershell
docker-compose logs resolver
```

### If defense doesn't respond:
```powershell
docker exec defense python3 /app/defense.py
# Check for port binding errors
```

### Reset everything:
```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

Perfect demonstration of how **consensus-based DNS defense** prevents cache poisoning attacks!
