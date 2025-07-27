# DNS-Cache-Poisoning-and-Phishing-Attack

Without defense
in resolbers named config:
add forwarders { 10.0.0.50; 10.0.0.40; };


docker-compose down
docker-compose up --build -d
docker exec -it victim dig "@10.0.0.20" www.bank.lab

docker exec -it victim dig "@10.0.0.20" www.bank.lab +short

docker exec -it attacker python3 attack.py

for checking logs:

docker logs -f proxy-dns


for phishing:
docker exec -it attacker python3 phishing_server.py


# Configure victim DNS (if not already done)
docker exec victim sh -c "echo 'nameserver 10.0.0.20' > /etc/resolv.conf"

# Test DNS poisoning
docker exec victim nslookup www.bank.lab

# Test phishing site access from victim
docker exec victim curl http://www.bank.lab

# Test credential submission from victim
docker exec victim curl -X POST http://www.bank.lab/login -d "username=victim@bank.lab&password=mypassword123" -H "Content-Type: application/x-www-form-urlencoded"




































with defense
docker exec -it defense python3 defense.py

query:
docker exec -it victim dig "@10.0.0.70" www.bank.lab

or add in resolber config just 
 forwarders { 10.0.0.70; };

 then rebuild and give command 

 docker exec victim dig "@10.0.0.20" www.bank.lab