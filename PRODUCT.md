# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: **recruiters**. They arrive from a link on Gavin's resume, LinkedIn profile, or an application, and skim quickly to decide whether he is a credible candidate for an analyst role. Their job is to answer, in seconds: who is this, what role does he fit, what proof is there, and how do I reach him.

Secondary: hiring managers who click through to project detail pages to judge analytical thinking, and networking contacts.

## Product Purpose

A personal career site for Gavin Clarke, an Information Systems & Business Analytics student at Loyola Marymount University (Hilton College of Business, Class of May 2027). It gives a stronger signal than a PDF resume by presenting experience and projects with context, method, and measurable outcomes.

Success: a recruiter leaves understanding that Gavin is a fit for **analyst roles in finance, or in operations and supply chain**, has seen concrete proof, and knows how to contact him.

The site targets both **internships** and **full-time new-grad roles** (graduating May 2027), so it should read credibly to recruiters filling either.

## Positioning

Gavin pairs finance exposure (wealth-management internship supporting advisors on $600M+ in client assets, portfolio performance and allocation analysis) with operations and forecasting work (Intel chip-demand forecasting, an MLB predictive model adopted by his employer) and real operating experience co-founding a small moving business. The through-line is Excel/Sheets-based modeling applied to real business decisions.

**Not fintech.** The original spec and some site copy target "fintech"; that positioning is retired. Target domains are finance and operations / supply chain.

## Operating Context

- Server-rendered FastAPI + Jinja2 site with a SQLite/SQLAlchemy content database and an admin flow for editing content.
- Public pages: home, resume, projects list, project detail, contact. `/health` reports database status.
- Deployed on an Azure VM. The site must keep showing the core profile (name, headline, summary, contact links, primary CTA) when the database is unavailable, via fallback content.

## Capabilities and Constraints

- Content is database-driven: profile, experience, projects, skills, education, certifications, links, volunteer work, site metadata.
- Fallback behavior is a hard requirement: the profile must never disappear behind a maintenance or error page.
- `app/fallback_data.py` and `app/seed_data.py` still contain the original "Alex Morgan" default persona. That content is obsolete and is not product truth; fallback content should reflect Gavin's real profile.

## Brand Commitments

- Name: Gavin Clarke. Contact: gclarke5@lion.lmu.edu, LinkedIn (linkedin.com/in/gavin-clarke-81489329b). Location: Huntington Beach, CA.
- No GitHub URL is currently set.

## Evidence on Hand

Real content lives in the database (`career_platform.db`):

- Experience: Wealth Investment Management Intern, OnPointe / Wells Fargo (May 2026–present); Data Analyst Intern, Orb Analytics (Jan 2025–present); Co-Founder, Good Guys Moving Crew (Dec 2023–present, ~$12,500 net profit).
- Projects: Portfolio Performance and Asset Allocation Analysis; Operations and Forecasting Project (Intel chip demand); MLB Predictive Model.
- Skills, education (with relevant coursework), and volunteer work.

Absent and must not be fabricated: testimonials, employer logos, certifications, additional metrics beyond those recorded, live project links or repos, a headshot.

## Product Principles

1. **Recruiter-first in ten seconds.** Role fit, proof, and contact must be legible without scrolling or clicking.
2. **Outcomes over duties.** Lead with numbers and results where they genuinely exist; never inflate them.
3. **Finance and operations, stated plainly.** Every surface should reinforce the target roles, not a generic "analytics" or retired "fintech" story.
4. **Always available.** The core profile survives any backend failure.

## Accessibility & Inclusion

Mobile responsive, readable typography with clear hierarchy, keyboard navigable, sufficient contrast (WCAG AA), easy to skim.
