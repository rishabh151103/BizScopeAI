from .analytics import (
    analyze_revenue_trend,
    analyze_profitability,
    analyze_customer_performance,
    analyze_customer_type,
    analyze_category_performance,
    analyze_discount_performance,
    analyze_regional_performance,
    analyze_monthly_performance,
    analyze_correlations,
    analyze_business_comparisons,
    analyze_significant_changes,
    analyze_segment_changes,
    analyze_change_contribution,
    analyze_order_metrics,
    analyze_marketing_performance,
    analyze_customer_retention,
    analyze_distribution_statistics,
    analyze_outliers,
    analyze_product_performance,
    analyze_category_revenue_trend
)

from .visualization import (
    plot_revenue_trend,
    plot_category_revenue_trend,
    plot_product_performance,
    plot_profitability,
    plot_customer_performance,
    plot_customer_type_performance,
    plot_category_performance,
    plot_discount_performance,
    plot_regional_performance,
    plot_monthly_performance,
    plot_correlations,
    plot_business_comparison,
    plot_significant_changes,
    plot_segment_changes,
    plot_change_contribution,
    plot_marketing_performance,
    plot_customer_retention,
    plot_outliers,
    plot_outlier_summary,
)


ANALYTICS_REGISTRY = {
    "revenue_trend": {
    "function": analyze_revenue_trend,
    "description": (
        "Analyzes revenue over time to determine whether revenue is "
        "increasing, decreasing, or stable. Use this tool when the "
        "question is specifically about the overall revenue trend "
        "over time."
    ),
    "answers": [
        "Has revenue increased or decreased over time?",
        "Is our overall revenue trending upward or downward?",
        "How has revenue changed over the period?",
        "What is the overall revenue trend?",
    ],
},

    "category_revenue_trend": {
        "function": analyze_category_revenue_trend,
        "description": (
            "Calculates monthly revenue separately for each product category, "
            "including month-over-month absolute and percentage changes."
        ),
        "answers": [
            "How has revenue changed over time by category?",
            "Which product categories are growing or declining month by month?",
            "Compare monthly revenue trends across product categories.",
        ],
    },

    "profitability": {
        "function": analyze_profitability,
        "description": (
            "Analyzes overall profitability and compares products "
            "using revenue, cost, profit, and profit margin."
        ),
        "answers": [
            "How profitable is the business?",
            "Which product is most profitable?",
            "What are our profit margins?"
        ],
    },

    "product_performance": {
        "function": analyze_product_performance,
        "description": (
            "Compares individual products using revenue, profit, "
            "units sold, and profit margin."
        ),
        "answers": [
            "Which product is performing best?",
            "Which product generates the most revenue?",
            "Which product generates the most profit?",
            "How are our products performing?"
        ],
    },

    "customer_performance": {
        "function": analyze_customer_performance,
        "description": (
            "Analyzes individual customer performance using revenue "
            "and profit."
        ),
        "answers": [
            "Which customer generates the most revenue?",
            "Which customers are most profitable?"
        ],
    },

    "customer_type": {
    "function": analyze_customer_type,
    "description": (
        "Compares business performance across customer types such as "
        "New and Returning customers. Use this tool when the question "
        "asks whether a specific customer type contributes more revenue, "
        "profit, orders, units, or has a higher average order value."
    ),
    "answers": [
        "Which customer type generates the most revenue?",
        "Do returning customers contribute more revenue than new customers?",
        "Are returning customers responsible for most of our revenue?",
        "Which customer type is most profitable?",
        "How do New and Returning customers compare?",
        "What share of revenue comes from each customer type?",
      ],
    },

    "category_performance": {
        "function": analyze_category_performance,
        "description": (
            "Compares product categories using total revenue, total profit, "
            "units sold, average row-level profit margin, and aggregate "
            "profit margin calculated as total profit divided by total revenue."
        ),
        "answers": [
            "Which category performs best?",
            "Which category generates the most revenue?"
        ],
    },

    "discount_performance": {
        "function": analyze_discount_performance,
        "description": (
            "Compares revenue, profit, average row-level margin, and aggregate "
            "profit margin across the discount values present in the dataset, "
            "grouped by product category. Requires category, discount, revenue, "
            "and profit columns."
        ),
        "answers": [
            "How does Furniture profit margin vary by discount level?",
            "Compare profit by discount level for each category.",
            "Does discount level relate to profit margin by category?",
        ],
    },

    "regional_performance": {
        "function": analyze_regional_performance,
        "description": (
            "Compares geographic regions using total revenue, total profit, "
            "units sold, and average row-level profit margin; supports ranking "
            "regions by these measured results."
        ),
        "answers": [
            "Which region performs best?",
            "Which region generates the most revenue?",
            "Rank regions by total profit and calculate the gap between the top two.",
            "Compare average profit margin across regions.",
        ],
    },

    "monthly_performance": {
        "function": analyze_monthly_performance,
        "description": (
            "Provides monthly revenue, cost, profit, units, orders, "
            "and growth metrics."
        ),
        "answers": [
            "How did the business perform month by month?",
            "How did monthly profit change?"
        ],
    },

    "correlations": {
        "function": analyze_correlations,
        "description": (
            "Measures statistical correlations between numerical "
            "business variables such as revenue, profit, cost, "
            "marketing spend, units, and price."
        ),
        "answers": [
            "What variables are correlated?",
            "Is marketing spend correlated with revenue?"
        ],
    },

    "business_comparisons": {
        "function": analyze_business_comparisons,
        "description": (
            "Compares business performance across available dimensions "
            "such as customer type, region, product, and category."
        ),
        "answers": [
            "Compare business performance across segments."
        ],
    },

    "significant_changes": {
    "function": analyze_significant_changes,
    "description": (
        "Identifies the largest increases and decreases in monthly "
        "revenue and profit. Use this tool when the question asks for "
        "the biggest, largest, sharpest, or most significant change "
        "between months."
    ),
    "answers": [
        "What was the biggest monthly revenue drop?",
        "Which month had the largest revenue decrease?",
        "What was the largest monthly revenue increase?",
        "Which month experienced the biggest profit decline?",
        "What was the biggest change in revenue?",
        "Which month had the sharpest revenue fall?",
    ],
},

    "segment_changes": {
        "function": analyze_segment_changes,
        "description": (
            "Compares revenue for a specific business segment between "
            "two periods and calculates the change."
        ),
        "answers": [
            "How did a specific product change between two periods?",
            "How did a region's revenue change between two periods?"
        ],
    },

    "change_contribution": {
        "function": analyze_change_contribution,
        "description": (
            "Determines which business segments contributed to a "
            "known change in revenue."
        ),
        "answers": [
            "Which product contributed most to the revenue decline?",
            "Which region caused the revenue change?"
        ],
    },

    "order_metrics": {
        "function": analyze_order_metrics,
        "description": (
            "Analyzes order-level metrics including order count, "
            "average order value, median order value, units per order, "
            "and revenue per unit."
        ),
        "answers": [
            "What is our average order value?",
            "How many orders do we have?",
            "What is the average number of units per order?"
        ],
    },

    "marketing_performance": {
        "function": analyze_marketing_performance,
        "description": (
            "Analyzes marketing spending relative to revenue and profit."
        ),
        "answers": [
            "Is marketing spending generating enough revenue?",
            "How effective is our marketing spending?",
            "How much revenue do we generate per marketing rupee?"
        ],
    },

    "customer_retention": {
    "function": analyze_customer_retention,
    "description": (
        "Analyzes repeat-customer behavior and retention. Use this "
        "tool when the question asks about repeat customers, one-time "
        "customers, customer retention, or the share of customers or "
        "revenue associated with repeat purchasing behavior."
    ),
    "answers": [
        "What percentage of customers are repeat customers?",
        "How many customers are one-time versus repeat customers?",
        "What percentage of revenue comes from repeat customers?",
        "How strong is customer retention?",
        "Are most customers repeat customers?",
    ],
},

    "distribution_statistics": {
        "function": analyze_distribution_statistics,
        "description": (
            "Calculates statistical distribution metrics such as mean, "
            "median, standard deviation, quartiles, minimum, and maximum."
        ),
        "answers": [
            "What is the distribution of revenue?",
            "What are the statistical characteristics of our sales?"
        ],
    },

    "outliers": {
        "function": analyze_outliers,
        "description": (
            "Detects unusually high or low observations using "
            "IQR-based outlier detection."
        ),
        "answers": [
            "Are there unusual values in the data?",
            "Are there revenue outliers?",
            "Are there unusually high or low transactions?"
        ],
    },
}


VISUALIZATION_REGISTRY = {
    "revenue_trend": {
        "function": plot_revenue_trend,
        "result_key": "monthly_revenue",
    },

    "category_revenue_trend": {
        "function": plot_category_revenue_trend,
        "result_key": "category_monthly_revenue",
    },

    "profitability": {
        "function": plot_profitability,
        "result_key": "profit_by_product",
    },

    "product_performance": {
        "function": plot_product_performance,
        "result_key": "product_analysis",
    },

    "customer_performance": {
        "function": plot_customer_performance,
        "result_key": "customer_analysis",
    },

    "customer_type": {
        "function": plot_customer_type_performance,
        "result_key": "customer_type_analysis",
    },

    "category_performance": {
        "function": plot_category_performance,
        "result_key": "category_analysis",
    },

    "discount_performance": {
        "function": plot_discount_performance,
        "result_key": "discount_analysis",
    },

    "regional_performance": {
        "function": plot_regional_performance,
        "result_key": "regional_analysis",
    },

    "monthly_performance": {
        "function": plot_monthly_performance,
        "result_key": "monthly_analysis",
    },

    "correlations": {
        "function": plot_correlations,
        "result_key": "correlation_matrix",
    },

    "business_comparisons": {
        "function": plot_business_comparison,
        "result_key": None,
    },

    "significant_changes": {
        "function": plot_significant_changes,
        "result_key": "monthly_changes",
    },

    "segment_changes": {
        "function": plot_segment_changes,
        "result_key": None,
    },

    "change_contribution": {
        "function": plot_change_contribution,
        "result_key": None,
    },

    "marketing_performance": {
        "function": plot_marketing_performance,
        "result_key": None,
    },

    "customer_retention": {
        "function": plot_customer_retention,
        "result_key": None,
    },

    "outliers": {
        "function": plot_outlier_summary,
        "result_key": "outlier_summary",
    },
}
