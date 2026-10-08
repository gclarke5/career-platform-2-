fallback_profile = {
    "full_name": "Gavin Clarke",
    "headline": "Analyst in the making for finance, operations & supply chain",
    "summary": "Information Systems and Business Analytics student at Loyola Marymount University (Class of 2027) with internship experience in wealth management and sports analytics. Builds Excel and Google Sheets models for forecasting, portfolio analysis, and predictive analytics.",
    "email": "gclarke5@lion.lmu.edu",
    "linkedin_url": "https://www.linkedin.com/in/gavin-clarke-81489329b",
    "github_url": None,
    "location": "Huntington Beach, CA",
    "cta_primary": "View Resume",
    "contact": {
        "email": "gclarke5@lion.lmu.edu",
        "linkedin": "https://www.linkedin.com/in/gavin-clarke-81489329b",
    },
}

fallback_experience = [
    {
        "title": "Wealth Investment Management Intern",
        "company": "OnPointe, Wells Fargo",
        "date_range": "May 2026 - Present",
        "summary": "Assisted a group of 4 Financial Advisors and two associates manage over $600M in client assets.",
        "highlights": [
            "Prepared investment performance reports, asset allocation summaries and client review materials",
            "Performed quantitative analysis in Excel utilizing modeling and table functions",
            "Collaborated with advisors and client associates to process account openings, transfers and service requests",
        ],
    },
    {
        "title": "Data Analyst Intern",
        "company": "Orb Analytics",
        "date_range": "January 2025 - Present",
        "summary": "Developed a predictive model for the MLB and worked in NBA models, updating them daily based on game scores.",
        "highlights": [
            "Tasked with researching outlying teams with high or low stats in scoring, rebounding and defense",
            "Reported findings to managers to gain further insights that they could build into the company's predictive models",
        ],
    },
    {
        "title": "Co-Founder",
        "company": "Good Guys Moving Crew",
        "date_range": "December 2023 - Present",
        "summary": "Identified a market gap for affordable moving in my hometown which inspired the founding of the moving crew.",
        "highlights": [
            "Managed pricing and operation strategies, which led to 5 high value jobs in our first month of operating",
            "Focused our marketing strategy on the Nextdoor app, which grabbed the attention of Huntington locals across the entire city",
            "Achieved approx. $12,500 of net profit",
        ],
    },
]

fallback_projects = [
    {
        "title": "Portfolio Performance and Asset Allocation Analysis",
        "slug": "portfolio-performance-asset-allocation",
        "short_summary": "Evaluated diversified client portfolios ranging from $100K-$30M in assets.",
        "description_points": [
            "Analyzed portfolio returns, volatility and sector allocation using Excel",
            "Compared portfolio performance against benchmark indices and identified areas for rebalancing",
            "Presented findings to advisors to support quarterly client reviews",
        ],
        "metrics": None,
        "tools": "Excel",
        "category": "Finance",
    },
    {
        "title": "Operations and Forecasting Project",
        "slug": "operations-forecasting-intel",
        "short_summary": "Projected Intel's chip demand with regression and time series forecasting in Excel (Operations and Supply Chain Management course).",
        "description_points": [
            "Performed data cleaning, regression analysis, and time series forecasting in Excel to project Intel's chip demand",
            "Utilized functions such as EOMONTH, SUMIFS, and regression modeling to identify KPIs of chip sales",
            "Completed trend, seasonal and moving average projections on given data and evaluated which was the most accurate",
            "Created data visualizations based on projections and wrote a memo recommending the most optimal strategy",
            "Developed skills in forecasting, cost analysis and operations planning using real world data and constraints",
        ],
        "metrics": None,
        "tools": "Excel",
        "category": "Operations & supply chain",
    },
    {
        "title": "MLB Predictive Model",
        "slug": "mlb-predictive-model",
        "short_summary": "Built a fully functional MLB game-outcome predictive model in Google Sheets from scratch (Orb Analytics).",
        "description_points": [
            "Utilized functions such as IMPORTHTML to retrieve data from websites and implement it into the model",
            "Used team and individual stats for hitting and pitching (ERA, SGL%, Batting AVG%, etc.)",
            "Provided the project to my boss, who used the model as a base for their current predictive model",
            "Developed skills in sheet formulas, data research, and predictive modeling based on previous MLB seasons data",
        ],
        "metrics": "Adopted as the base for the company's current predictive model",
        "tools": "Google Sheets",
        "category": "Predictive modeling",
    },
]

fallback_site_meta = {
    "availability": "Open to analyst internships and full-time roles in finance, operations and supply chain. Graduating May 2027.",
    "proof_points": "\n".join(
        [
            "Supported 4 financial advisors managing $600M+ in client assets|/resume#experience|Wells Fargo / OnPointe",
            "Built an MLB predictive model my employer adopted as the base of its current model|/projects/mlb-predictive-model|Orb Analytics",
            "Co-founded a local moving business that netted about $12,500|/resume#experience|Good Guys Moving Crew",
        ]
    ),
}
