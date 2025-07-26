# Live DNS Defense Demonstration

## 🚀 Setup Environment

```powershell
# Start all containers
docker-compose up -d

# Verify all containers are running
docker ps
```

Expected containers:
- resolver (10.0.0.20)
- proxy-dns (10.0.0.40) 
- auth-dns (10.0.0.30)
- auth-dns-2 (10.0.0.60) ← NEW
- attacker (10.0.0.50)
- victim (10.0.0.10)

---

## 📋 Live Demo Steps

### **Phase 1: Normal Operation (No Attack)**

```powershell
# Terminal 1: Test normal DNS resolution
docker exec victim dig @10.0.0.20 www.bank.lab +short
```
**Expected Result**: `10.0.0.80` (legitimate)

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

```powershell
# Terminal 2: Test multiple times to confirm cache poisoning
docker exec victim dig @10.0.0.20 www.bank.lab +short
docker exec victim dig @10.0.0.20 www.bank.lab +short
```
**Result**: Always `10.0.0.50` (cached poisoned result)

---

### **Phase 3: Defense Activated (Attack Still Running!)**

```powershell
# Terminal 3: Start defense (while attack.py still running in Terminal 1)
docker exec resolver python3 /app/defense.py
```

**Defense Output:**
```
[DEFENSE] Starting DNS Defense Proxy...
[DEFENSE] Monitoring servers: ['10.0.0.40', '10.0.0.60', '10.0.0.50']
[DEFENSE] Consensus threshold: 2 votes required
[DEFENSE] Listening on port 5353...
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

## 🔍 How It Works

### **Configuration (named.conf.options):**
```
forwarders { 127.0.0.1:5353; 10.0.0.50; 10.0.0.40; };
```

### **Defense OFF:**
1. BIND tries `127.0.0.1:5353` (no defense running)
2. Falls back to `10.0.0.50, 10.0.0.40`
3. Attacker wins race condition → `10.0.0.50`

### **Defense ON:**
1. BIND queries `127.0.0.1:5353` (defense proxy)
2. Defense proxy queries all 3 servers:
   - `10.0.0.40` → `10.0.0.80` (legitimate)
   - `10.0.0.60` → `10.0.0.80` (legitimate)
   - `10.0.0.50` → `10.0.0.50` (attacker)
3. Consensus: `10.0.0.80` wins (2 vs 1)
4. Defense returns `10.0.0.80` to BIND

---

## 📊 Demo Summary

| Phase | Attack Status | Defense Status | Result | Explanation |
|-------|---------------|----------------|--------|-------------|
| 1 | ❌ Off | ❌ Off | `10.0.0.80` | Normal operation |
| 2 | ✅ Running | ❌ Off | `10.0.0.50` | Race condition attack succeeds |
| 3 | ✅ Running | ✅ Running | `10.0.0.80` | Consensus blocks attack |
| 4 | ✅ Running | ❌ Off | `10.0.0.50` | Attack resumes when defense stops |

## 🎯 Key Demonstration Points

1. **Same attack running continuously** - No need to restart
2. **Live switching** - Defense can be turned on/off instantly  
3. **Consensus voting** - 2 legitimate servers beat 1 attacker
4. **Seamless fallback** - When defense stops, normal behavior resumes
5. **Real-time logs** - Shows exactly how consensus works

Perfect for demonstrating to your teacher how DNS cache poisoning works and how consensus-based defense prevents it!
