"""
Methodology taxonomy: a curated reference table of common research methods
relevant to RIOS's supported domains (economics, agribusiness, econometrics,
ML/forecasting, etc.).

WHY this is safe to hand-write as static data (unlike research gaps or
citations): strengths/limitations/typical_applications describe the method
itself — general, textbook-level facts, not a claim about any specific
paper or finding. The evidence-before-generation principle concerns
fabricating research claims; it doesn't require rediscovering "what is
panel data analysis" from scratch for every run.

Each entry's `keywords` list is used by the recommender to detect whether a
method is actually *mentioned* in the retrieved evidence — that grounding
step is what keeps the final recommendation evidence-based.
"""

from __future__ import annotations

METHODOLOGY_TAXONOMY: dict[str, dict] = {
    "Panel Data Analysis": {
        "keywords": ["panel data", "fixed effects", "random effects", "panel regression"],
        "typical_applications": "Studying change over time across multiple units (firms, farms, countries) while controlling for unobserved heterogeneity.",
        "strengths": "Controls for time-invariant confounders; increases statistical power versus a single cross-section.",
        "limitations": "Requires repeated observations of the same units; sensitive to attrition and unbalanced panels.",
    },
    "Difference-in-Differences": {
        "keywords": ["difference-in-differences", "difference in differences", "diff-in-diff", "did estimator"],
        "typical_applications": "Estimating causal effects of a policy or treatment by comparing changes over time between treated and control groups.",
        "strengths": "Simple, transparent causal identification when a clear treatment/control split and parallel-trends assumption hold.",
        "limitations": "Validity depends heavily on the parallel-trends assumption, which is often untestable directly.",
    },
    "Randomized Controlled Trial": {
        "keywords": ["randomized controlled trial", "randomised controlled trial", " rct ", "field experiment", "random assignment"],
        "typical_applications": "Testing causal impact of an intervention (e.g. a subsidy, training program) under controlled random assignment.",
        "strengths": "Strongest causal identification available; minimizes selection bias by design.",
        "limitations": "Expensive, logistically demanding, and results may not generalize beyond the study context.",
    },
    "Time Series / Forecasting Models": {
        "keywords": ["time series", "arima", "garch", "vector autoregression", " var model", "forecasting model"],
        "typical_applications": "Modeling and forecasting variables that evolve over time, such as prices, yields, or exchange rates.",
        "strengths": "Captures temporal dependence, seasonality, and volatility patterns explicitly.",
        "limitations": "Assumes historical patterns persist; can perform poorly around structural breaks or shocks.",
    },
    "Machine Learning / Deep Learning": {
        "keywords": ["machine learning", "deep learning", "neural network", "random forest", "gradient boosting", "lstm"],
        "typical_applications": "Prediction and pattern recognition in large or high-dimensional datasets, e.g. price forecasting, image-based crop diagnostics.",
        "strengths": "Handles non-linear relationships and large feature sets well; often outperforms classical models on prediction accuracy.",
        "limitations": "Can be a 'black box' with limited interpretability; requires large, clean datasets to avoid overfitting.",
    },
    "Spatial Econometrics": {
        "keywords": ["spatial econometrics", "spatial autocorrelation", "spatial regression", "geographically weighted"],
        "typical_applications": "Modeling relationships where geographic location and proximity matter, e.g. regional price spillovers.",
        "strengths": "Explicitly accounts for spatial dependence that standard regression ignores, avoiding biased estimates.",
        "limitations": "Requires reliable spatial/geographic data; model specification (weight matrix choice) can be subjective.",
    },
    "Structural Equation Modeling": {
        "keywords": ["structural equation model", " sem ", "path analysis", "latent variable model"],
        "typical_applications": "Testing complex relationships among multiple observed and latent variables, common in behavioral/adoption studies.",
        "strengths": "Can model measurement error and test multiple relationships simultaneously.",
        "limitations": "Requires relatively large samples and strong theoretical justification for the specified model structure.",
    },
    "Discrete Choice Models (Logit/Probit)": {
        "keywords": ["logit model", "probit model", "discrete choice", "logistic regression"],
        "typical_applications": "Modeling binary or categorical outcomes, e.g. a farmer's decision to adopt a new technology.",
        "strengths": "Well-established, interpretable coefficients, computationally efficient.",
        "limitations": "Assumes a specific error distribution; can be sensitive to omitted variable bias.",
    },
    "Meta-Analysis": {
        "keywords": ["meta-analysis", "meta analysis", "systematic review"],
        "typical_applications": "Statistically combining results across many prior studies to estimate an overall effect size.",
        "strengths": "Increases statistical power and generalizability by pooling across studies.",
        "limitations": "Vulnerable to publication bias and heterogeneity in how underlying studies were conducted.",
    },
    "Survey-Based / Cross-Sectional Analysis": {
        "keywords": ["survey data", "cross-sectional", "questionnaire", "household survey"],
        "typical_applications": "Capturing a snapshot of behavior, attitudes, or outcomes across a sample at one point in time.",
        "strengths": "Relatively low-cost and fast to implement; flexible for many research questions.",
        "limitations": "Cannot establish causality or capture change over time; susceptible to response and recall bias.",
    },
    "Case Study / Qualitative Analysis": {
        "keywords": ["case study", "qualitative analysis", "interview", "thematic analysis", "grounded theory"],
        "typical_applications": "In-depth exploration of a specific context, institution, or phenomenon that's hard to quantify.",
        "strengths": "Provides rich contextual understanding that quantitative methods can miss.",
        "limitations": "Findings are often not statistically generalizable beyond the case studied.",
    },
    "Computable General Equilibrium Modeling": {
        "keywords": ["computable general equilibrium", " cge model", "general equilibrium model"],
        "typical_applications": "Simulating economy-wide effects of policy changes (e.g. trade tariffs, subsidies) across interlinked markets.",
        "strengths": "Captures cross-sector and economy-wide feedback effects that partial-equilibrium models miss.",
        "limitations": "Heavily dependent on calibration assumptions; results can be sensitive to parameter choices.",
    },
}
