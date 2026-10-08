

Customers verify encryption through Connection is Secure then directing to certificate details where you can find all the information matches gavinclarke.me once HTTPS is established. My site uses Nginx and Ubuntu. The traffic for HTTPS uses port 443. Traffic between the browser and server is encrypted with TLS. Port 80 only accepts plain HTTP requests and redirects them to HTTPS. 

As evidence, I ran:
curl -I http://gavinclarke.me
The server returned HTTP/1.1 301 Moved Permanently, identified the server as nginx/1.24.0 (Ubuntu), and redirected the request to https://gavinclarke.me/.
I also used:
openssl s_client -connect gavinclarke.me:443 -servername gavinclarke.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
It shows all matching info (domain, issuer, start date, expiration date). A customer can now use the server. 
