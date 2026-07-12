from app.api.report_content import enrich_report_result


def test_enrich_report_result_replaces_low_value_cards_from_answer():
    answer = """
### **苹果公司（AAPL）股票研究报告**

**核心观点：** 苹果公司财务基本面保持稳健增长，但短期技术面偏弱。

#### **一、 历史趋势与技术分析**
* **价格走势：** 股价从$163.50回落至$145.52，短期处于寻找支撑阶段。
* **相对强弱指数（RSI）：** 14日RSI为43.17，市场动能偏中性偏弱。

#### **二、 当前估值与关键财务指标**
* **市盈率（P/E）：** 2025年P/E约为34.09，估值相对较高。
* **营收与净利润：** 营收从$3833亿增长至$4162亿，净利润升至$1120亿。

#### **三、 风险因素**
* **估值过高风险：** 任何业绩不达预期都可能引发显著估值回调。
* **宏观经济与消费支出：** 全球经济放缓可能影响高端消费电子需求。

#### **四、 结论**
AAPL股票目前处于高估值、强基本面、但短期技术面偏弱的状态。对于短期交易者而言，需要等待技术指标转强。
建议投资者密切关注苹果的季度财报、服务业务收入和新产品发布计划。
"""
    result = {
        "answer": answer,
        "summary": "",
        "key_findings": ["已完成数据收集工具：stock_research, news_search。"],
        "risk_factors": [
            {
                "factor": "数据完整性",
                "severity": "medium",
                "description": "当前报告包含后端兜底内容。",
            }
        ],
        "market_trends": ["市场趋势未从工具结果中形成可靠结论。"],
        "recommendations": ["请先核对数据源和报告生成日志。"],
    }

    enriched = enrich_report_result(result)

    assert "34.09" in " ".join(enriched["key_findings"])
    assert "已完成数据收集工具" not in " ".join(enriched["key_findings"])
    assert enriched["risk_factors"][0]["factor"] == "估值过高风险"
    assert "RSI" in " ".join(enriched["market_trends"])
    assert "需要等待技术指标转强" in " ".join(enriched["recommendations"])


def test_enrich_report_result_preserves_useful_structured_cards():
    result = {
        "answer": "### Report\n* This should not replace already useful cards.",
        "key_findings": ["AAPL P/E is 34.09 based on provided financial data."],
        "risk_factors": [
            {
                "factor": "Valuation",
                "severity": "medium",
                "description": "P/E is elevated versus the prior year.",
            }
        ],
        "market_trends": ["RSI is 43.17, indicating neutral to weak momentum."],
        "recommendations": ["Wait for stronger technical confirmation."],
    }

    enriched = enrich_report_result(result)

    assert enriched["key_findings"] == result["key_findings"]
    assert enriched["risk_factors"] == result["risk_factors"]
    assert enriched["market_trends"] == result["market_trends"]
    assert enriched["recommendations"] == result["recommendations"]


def test_enrich_report_result_adds_chart_specs_from_grounded_numbers():
    result = {
        "answer": (
            "AAPL valuation includes P/E of 34.09, EPS of 7.49, "
            "ROE of 151.91%, and RSI of 43.17. "
            "The stock price moved from $163.50 to $145.52 over the period."
        ),
        "chart_specs": [],
    }

    enriched = enrich_report_result(result)

    assert len(enriched["chart_specs"]) >= 1
    metric_chart = enriched["chart_specs"][0]
    assert metric_chart["chart_type"] == "bar"
    assert {point["label"] for point in metric_chart["data"]} >= {
        "P/E",
        "EPS",
        "ROE %",
        "RSI",
    }
