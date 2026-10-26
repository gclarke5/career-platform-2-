# Zoho Mail outbound authentication check

**Domain:** `gavinclarke.me`
**Test message:** "Test 02: New Outbound", sent Thu, 15 Oct 2026 11:21:58 -0700 from Zoho Mail
**From:** `career-platform@gavinclarke.me`
**Received by:** iCloud Mail, delivered to INBOX
**Analyzed:** 2026-10-15

This checks that mail sent from Zoho passes SPF, DKIM and DMARC for `gavinclarke.me` after the DNS changes. The DNS state before those changes is in [dns-before-zoho.md](dns-before-zoho.md).

## Result

| Check | Result | Domain | Evidence |
|---|---|---|---|
| SPF | pass | `gavinclarke.me` | Envelope sender `career-platform@gavinclarke.me` was sent from `165.173.182.52` (`sender5-of-o52.zoho.com`), which the SPF record `include:zohomail.com` allows. |
| DKIM | pass | `gavinclarke.me` | Signature has `d=gavinclarke.me` and selector `s=zmail`, and iCloud checked it against the `zmail._domainkey` record. |
| DMARC | pass | `gavinclarke.me` | The visible From domain is `gavinclarke.me`. SPF and DKIM both passed on that same domain. The policy is `p=none`. |
| ARC | pass | `zohomail.com` | Zoho's own forwarding signature (`s=zohoarc`). Not tied to my domain. |
| BIMI | skipped | n/a | "insufficient dmarc": BIMI requires `p=quarantine` or `p=reject`. Expected with `p=none`. |

## What this shows

- **DKIM:** the `zmail._domainkey` TXT record in Cloudflare holds Zoho's key. DNS alone couldn't confirm that, but a DKIM pass with selector `zmail` does.
- **SPF and DMARC:** outbound mail from Zoho authenticates fully for `gavinclarke.me`.
- **Possible next step:** once a few weeks of DMARC reports look clean, tighten DMARC from `p=none` to `p=quarantine`. That would also allow BIMI.

## Relevant headers (as received)

These are the authentication and routing headers only. I left out the message body and the long encoded blobs (Apple spam scores, Proofpoint data, the full ARC and DKIM signature values).

```
Return-path: <career-platform@gavinclarke.me>
Received: from sender5-of-o52.zoho.com (sender5-of-o52.zoho.com [165.173.182.52]) by p00-icloudmta-smtpin-us-central-1n-100-percent-25 (Postfix) with ESMTPS id 434DEC00096; Thu, 15 Oct 2026 18:22:03 +0000 (UTC)
Received: from mail.zoho.com by mx.zohomail.com with SMTP id 1792088519042909.8728290109242; Thu, 15 Oct 2026 11:21:59 -0700 (PDT)
X-Apple-MoveToFolder: INBOX
Authentication-Results: bimi.icloud.com; bimi=skipped reason="insufficient dmarc"
Authentication-Results: arc.icloud.com; arc=pass
Authentication-Results: dmarc.icloud.com; dmarc=pass header.from=gavinclarke.me
X-DMARC-Policy: v=DMARC1; p=none; rua=mailto:career-platform@gavinclarke.me
X-DMARC-Info: pass=pass; dmarc-policy=none; s=r1; d=r1; pdomain=gavinclarke.me
Authentication-Results: dkim-verifier.icloud.com; dkim=pass header.d=gavinclarke.me header.i=career-platform@gavinclarke.me header.b=KTs59t1B
Received-SPF: pass (spf.icloud.com: domain of career-platform@gavinclarke.me designates 165.173.182.52 as permitted sender) receiver=spf.icloud.com; client-ip=165.173.182.52; helo=sender5-of-o52.zoho.com; envelope-from=career-platform@gavinclarke.me
Authentication-Results: spf.icloud.com; spf=pass (spf.icloud.com: domain of career-platform@gavinclarke.me designates 165.173.182.52 as permitted sender) smtp.mailfrom=career-platform@gavinclarke.me
ARC-Authentication-Results: i=1; mx.zohomail.com; dkim=pass header.i=gavinclarke.me; spf=pass smtp.mailfrom=career-platform@gavinclarke.me; dmarc=pass header.from=<career-platform@gavinclarke.me>
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/relaxed; t=1792088521; s=zmail; d=gavinclarke.me; i=career-platform@gavinclarke.me; h=Date:Date:From:From:To:To:Message-Id:Message-Id:Subject:Subject:MIME-Version:Content-Type:Reply-To:Cc; bh=…; b=KTs59t1B…
Date: Thu, 15 Oct 2026 11:21:58 -0700
From: Gavin Clarke <career-platform@gavinclarke.me>
Message-Id: <1a140ccb141.8504a361420358.1159627982648448272@gavinclarke.me>
Subject: Test 02: New Outbound
User-Agent: Zoho Mail
```
