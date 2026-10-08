

Customers verify encryption through Connection is Secure then directing to certificate details where you can find all the information matches gavinclarke.me before establishing HTTPS. My site uses Nginx and Ubunu. The traffic for HTTPS uses port 443 and 80. Should be TLS encryption on browser and server as well. Port 80 only accepts regular requests. 

As evidence, I ran:
curl -I https://gavinclarke.me
The server returned HTTP/1.1 301 Moved Permanently, identified the server as nginx/1.24.0 (Ubuntu), and redirected the request to https://gavinclarke.me/.
I also used:
openssl s_client -connect gavinclarke.me:443 -servername gavinclarke.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
It shows all matching info (trust date issuer expiration date..etc). A customer can now use the server. 
