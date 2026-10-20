# What happens when you open a website

What happens between typing a domain, pressing Enter, and seeing the page.

## The request and response, step by step

```mermaid
sequenceDiagram
    autonumber
    actor U as You
    participant B as Browser
    participant OS as OS + home router
    participant RR as Recursive resolver<br/>(ISP or 1.1.1.1)
    participant NS as Root → TLD → authoritative<br/>name servers
    participant NET as Internet<br/>(ISP and backbone routers)
    participant S as Web server<br/>(proxy + app + DB)

    U->>B: types example.com, presses Enter
    B->>B: is it a URL or a search? adds https://<br/>checks HSTS list and its DNS cache

    rect rgba(120,120,120,0.12)
    Note over B,NS: 1. DNS: name → IP address
    B->>OS: resolve example.com (OS cache, hosts file)
    OS->>RR: DNS query (UDP 53, or DoH)
    RR->>NS: root: "ask .com" → TLD: "ask these name servers" → authoritative
    NS-->>RR: A / AAAA record (IP), with a TTL
    RR-->>OS: IP (cached for TTL)
    OS-->>B: IP
    end

    rect rgba(120,120,120,0.12)
    Note over B,S: 2. Connection: TCP then TLS
    B->>NET: SYN to IP:443 (NAT rewrites your private IP to your public one)
    NET->>S: routed hop by hop
    S-->>B: SYN-ACK
    B->>S: ACK (TCP open)
    B->>S: TLS ClientHello (SNI = example.com)
    S-->>B: certificate + key share
    B->>B: checks cert chain, expiry, and that the name matches
    B->>S: Finished (keys agreed, encrypted from here on)
    end

    rect rgba(120,120,120,0.12)
    Note over B,S: 3. Request
    B->>S: GET / HTTP/2<br/>Host, cookies, Accept, User-Agent
    S->>S: proxy/CDN → app server → database → builds HTML
    end

    rect rgba(120,120,120,0.12)
    Note over B,S: 4. Response (same path, in reverse)
    S-->>NET: 200 OK + headers + HTML, split into TCP packets
    NET-->>OS: routers forward packets (they may take different routes)
    OS-->>B: NAT maps them back to your device
    B->>B: TCP reorders packets and resends lost ones, TLS decrypts
    end

    rect rgba(120,120,120,0.12)
    Note over B,S: 5. Render
    B->>B: parses HTML → DOM, finds CSS, JS, images
    B->>S: more GETs on the same connection (or from cache/CDN)
    S-->>B: assets
    B->>B: CSS → layout → paint, JS runs
    B-->>U: page on screen
    end
```

## The path across the network

```mermaid
flowchart LR
    B[Browser] -->|HTTP inside TLS<br/>inside TCP inside IP| R1[Home router<br/>NAT]
    R1 --> ISP[ISP network]
    ISP --> BB[Backbone /<br/>peering]
    BB --> E[Server's edge<br/>CDN or load balancer]
    E --> APP[App server]
    APP --> DB[(Database)]
    DB -.-> APP
    APP -.->|response| E
    E -.-> BB -.-> ISP -.-> R1 -.-> B
```

## Key points

- **DNS only returns an address.** After the first lookup, every cache along
  the way (browser, OS, resolver) keeps the answer until its TTL runs out, so
  later visits skip step 1.
- **The response follows the request's path backwards.** It's addressed to your
  public IP and port, and your router's NAT table sends it to your device.
  Individual packets can take different routes, and TCP puts them back in
  order.
- **Each layer has one job:** IP gets packets to the machine, TCP makes the
  delivery reliable and ordered, TLS encrypts it and proves the server's
  identity, and HTTP carries the request itself.
- **One page means many requests.** The first response is just HTML. The
  browser then fetches the CSS, JavaScript and images, usually over the same
  connection.
