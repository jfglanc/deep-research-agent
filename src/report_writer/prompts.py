"""Prompt template for final report generation.

This module contains the prompt used to generate the final research report
from the accumulated findings from all sub-agents.
"""

FINAL_REPORT_PROMPT = """Based on all the research conducted, create a comprehensive, well-structured research report.

**Research Topic**: {research_topic}

**Research Scope**: {research_scope}

**Research Findings**:
{findings}

Today's date: {date}

<Task>
Create a detailed, professional research report that fully addresses the research scope above.
</Task>

<Report Structure>
1. Is well-organized with proper markdown headings:
   - # for title
   - ## for main sections
   - ### for subsections
2. Includes specific facts and insights from the research findings
3. References relevant sources using [Title](URL) format inline
4. Provides balanced, thorough analysis
5. Be as comprehensive as possible - include all information relevant to the research scope
6. Includes a "## Sources" section at the end with all referenced links

You can structure your report in different ways depending on the research scope:

**For comparisons** (e.g., "Compare X vs Y"):
1. Introduction
2. Overview of X
3. Overview of Y  
4. Comparative analysis
5. Conclusion
6. Sources

**For lists/rankings** (e.g., "Top 10 X"):
- Can be a single section with the list
- OR each item as a separate section
- No need for intro/conclusion if it's just a list

**For topic summaries** (e.g., "Research topic X"):
1. Overview
2. Key concept/aspect 1
3. Key concept/aspect 2
4. Key concept/aspect 3
5. Conclusion
6. Sources

Choose the structure that best fits the research scope!
</Report Structure>

<Writing Guidelines>
- Use simple, clear language
- Use ## for section titles (Markdown format)
- Do NOT refer to yourself as the writer (e.g., don't say "I found..." or "In this report...")
- Do not add meta-commentary (e.g., don't say "I will now discuss...")
- Just write the report content directly
- Each section should be comprehensive and detailed
- Use bullet points when appropriate, but default to paragraph form
- This is a deep research report - users expect thorough, detailed answers
</Writing Guidelines>

<Citation Rules>
- Assign each unique URL a single citation number: [1], [2], [3], etc.
- Use inline citations in the text
- End with ## Sources section listing all sources with numbers
- Number sources sequentially without gaps (1,2,3,4...)
- Format: [1] Source Title: URL
- Citations are CRITICAL - pay careful attention to getting these right
</Citation Rules>

CRITICAL: The report should be written in the same language as the research scope!
If the scope is in English, write in English. If in another language, use that language.
"""

