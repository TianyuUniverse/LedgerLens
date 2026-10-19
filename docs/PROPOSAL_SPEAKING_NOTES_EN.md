# LedgerLens - Simple English Proposal Speaking Notes

Use **LedgerLens_Proposal_AI_Memory_EN_Simple.pptx** for the ten-slide opening presentation. One speaker presents the full script. The simple script is in its speaker notes. The same slide visuals are in **LedgerLens_Proposal_AI_Memory_EN.pdf**.

Main script: **575 words**, about five minutes at 115 words per minute. The suggested times help with practice. Student IDs are on the cover and do not need to be read aloud.

The main script uses short sentences and common words. The school meal, roommate bill, large purchase and savings goal examples are in the Q&A. They are not part of the five-minute main script.

Memory and the new AI features are **plans**. The picture and test scores show our basic version.

## Timing guide

| Slide | Title | Suggested time | Words |
| --- | --- | --- | --- |
| 1 | LedgerLens: AI Personal Finance Assistant | 0:00-0:20 | 39 |
| 2 | Table of Contents | 0:20-0:38 | 35 |
| 3 | User Needs & Pain Points | 0:38-1:09 | 59 |
| 4 | Project Positioning & Users | 1:09-1:40 | 59 |
| 5 | User Research: Initial Insights & Plan | 1:40-2:12 | 61 |
| 6 | Product Workflow | 2:12-2:47 | 67 |
| 7 | System Architecture | 2:47-3:21 | 65 |
| 8 | Core Innovations | 3:21-3:53 | 61 |
| 9 | Validation & Risks | 3:53-4:21 | 54 |
| 10 | Plan & Outlook | 4:21-5:00 | 75 |

## Slide 1 - LedgerLens: AI Personal Finance Assistant

Suggested time: 0:00-0:20 (20 seconds).

Our project, LedgerLens, is an AI money helper for students. It will remember how users group their spending and help them understand their money. I will explain what we want to build and how we plan to test it.

## Slide 2 - Table of Contents

Suggested time: 0:20-0:38 (18 seconds).

We have eight parts. First, we look at users and their problems. Then we explain our research plan and how the system will work. Finally, we talk about our new ideas, tests and next steps.

## Slide 3 - User Needs & Pain Points

Suggested time: 0:38-1:09 (31 seconds).

Students may need to fix the same wrong spending group again and again. A payment name alone may not tell us what the money was used for. Wrong groups can also make spending reports less useful. We want the system to ask when it is not sure, learn from the user's answer and use that memory for later payments.

## Slide 4 - Project Positioning & Users

Suggested time: 1:09-1:40 (31 seconds).

We plan four features. First, the system will remember how each user groups payments. Second, users can ask questions about their spending and change which payments to include. Third, it will help make savings plans that follow the user's limits. Later, we will add monthly spending reports. We also look at tools such as Actual Budget and Firefly III.

## Slide 5 - User Research: Initial Insights & Plan

Suggested time: 1:40-2:12 (32 seconds).

We have not talked to student users yet. We will ask them to try the system and check how it groups their payments. We will test new payments, repeated payments and cases with different uses. We will count how often users need to fix a wrong group. We will also check whether the answers and savings plans are easy to understand.

## Slide 6 - Product Workflow

Suggested time: 2:12-2:47 (35 seconds).

In the planned system, users first add their records. The system looks for a useful memory. If it is not sure, it asks the user to choose a spending group. It saves the answer. With the user's permission, it can use that memory for similar payments later. Users can change or delete memories. The picture shows our basic version. It does not have this memory feature yet.

## Slide 7 - System Architecture

Suggested time: 2:47-3:21 (34 seconds).

Here is our system design. A web page connects to a Python server and a database. The database will store records and user memories. Chat history will keep the current dates and limits. AI will read past examples and choose tools. Code will check the money and the rules. Users will approve new memories and saved plans. If AI fails, the basic mode stays available.

## Slide 8 - Core Innovations

Suggested time: 3:21-3:53 (32 seconds).

Our main new idea is to remember each user's choices. After the user checks a spending group, the system can use that choice for later payments with the same meaning. It should ask again if the meaning is different. This may reduce repeated work. We also plan answers that show the source records and savings plans that follow the user's limits.

## Slide 9 - Validation & Risks

Suggested time: 3:53-4:21 (28 seconds).

Our basic version passed twenty-eight tests. Our rules got eighteen of twenty made-up examples right. These are not results for AI memory. We will use new cases to check correct groups, wrong groups and repeated questions. We will also check money totals and user limits. We have not tested a real AI model yet.

## Slide 10 - Plan & Outlook

Suggested time: 4:21-5:00 (39 seconds).

We will first build the memory feature. Then we will add chat tools and savings plans. Next, we will connect the pages and test the full process. Chen Tianyu will focus on user needs and savings plans. Zhu Juncheng will focus on the server and data. Zhang Hanwen will focus on pages and tests. These are planned roles. Codex helped build the first version. We will check it and record our own work. Thank you.

## Short English Q&A

**What is your main new idea?**

The system will remember a user's checked spending groups. It will use these memories for later payments with the same meaning. If it is not sure, it will ask again. We still need to build and test this feature.

**How does memory work?**

We plan to save the user's answer in a database. For a new payment, the system will look for a useful past answer. AI will use it to help choose the right group.

**Can you give an example of a wrong group?**

A payment to our school may be for meals. After the user tells us this, we can remember it as Food. But another school payment may be for classes. We must check the notes and ask again when we are not sure.

**What about money sent to a roommate?**

It may pay for electricity or air conditioning. We will ask what it pays for and put it in Utilities if the user says yes. Moving money between the user's own accounts is different. It should not count as spending.

**Can users change or delete a memory?**

Yes. We plan to show which memory was used. Users can change it, turn it off or delete it. Changing a memory will not change old records without asking.

**What will AI and code do?**

AI will understand questions, choose tools and explain the results. Code will read records, add up the money and check the user's limits. Users approve memory rules and saved plans.

**Have you built the AI features?**

No. We have a basic version for adding records, viewing totals and making manual plans. The memory and new AI features are still plans.

**Can it leave out a large purchase?**

If a user asks to leave out a computer purchase, we will find the right record and calculate again. The original record stays in the system. If more than one record matches, we will ask the user to choose.

**Can you give a savings-plan example?**

A user may want to save six thousand yuan in six months, keep rent unchanged and leave at least two hundred yuan a month for entertainment. AI will suggest choices. Code will check them. The user can change the limits and ask for a new plan.

**What if the user cannot reach the goal?**

We will show how much is still missing. We can suggest more time or ask which limit the user wants to change. We will not change a fixed limit without asking.

**Can AI explain why someone spent money?**

Records show what was paid and when. They do not tell us why a person wanted it. If we need that information, we will ask the user.

**How will you test this?**

We will use new cases that we did not use while building it. We will count correct groups, wrong groups and repeat questions. We will also check the totals and user limits. The AI features have not been tested yet.

**What does eighteen out of twenty mean?**

Our rules got eighteen of twenty made-up examples right. This is a small check of the basic version. It does not show how well AI memory works.

**How did Codex help?**

Codex helped write the first version and the tests. We still need to read the code, build the new features and record our own work.

## Practice notes

- The ten slide paragraphs are the main script. Read the Q&A only if asked.
- Pause briefly before moving to the next slide.
- Say that the AI features and student research are still plans.
- The 18/20 score is for rules on made-up examples. We have not tested a real AI model yet.
- The team roles are planned roles.
- A payment name alone does not tell us what the money was used for.
- The system should ask again when a new payment does not clearly match a memory.
- The picture shows the basic version. It does not show the planned memory feature.

## Architecture reference

The planned AI tool use follows the [official OpenAI Function calling guide](https://developers.openai.com/api/docs/guides/function-calling). The app runs the tools and gives the results to AI. The memory design, money checks and user approval rules are our project choices. This reference is not part of the spoken script.
