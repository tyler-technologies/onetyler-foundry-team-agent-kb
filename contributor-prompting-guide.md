# Talking to your AI helper — a quick start

> ## 📖 This page is to READ. There is nothing here to copy.
>
> There is exactly **one** thing you ever paste, and it is a different file —
> [`contributor-initial-prompt.md`](contributor-initial-prompt.md).
>
> **That whole file is the thing you paste.** Open it, select everything, copy it, paste it to
> your AI. You do not have to find the right part; there is no wrong part. You use it once,
> when setting up a new computer.
>
> This page explains what to say *after* that.

**Who this is for:** anyone who has never used an AI assistant to do work before. No technical
background needed, and you will not have to learn any commands.

**When to read it:** at the start, once your computer is set up, and then again any time you are
unsure what to say. It is meant to be re-read, not memorised.

---

## Setting up, the first time

One file, one paste, once per computer.

1. Open [`contributor-initial-prompt.md`](contributor-initial-prompt.md).
2. Select **all** of it and copy it.
3. Open your AI assistant in a terminal, in whatever folder you keep work in.
4. Paste, and send.

That file contains nothing but the instructions themselves, so copying too much is not
possible. Everything explanatory lives here instead.

### What a correct setup looks like

When it finishes you should have:

- The shared files downloaded to your computer.
- Your AI having read the house rules, and able to tell you what you may and may not change.
- **Your name in the reviewer list.** Check this — it is the one thing that quietly stops
  everything else working. If your name is missing you are not on the team list yet; ask an
  admin.
- The review screen answering at a web address it gives you.
- A short summary of the phrases you will need, and a note about what is waiting to be
  reviewed.

Nothing saved, nothing published, no conversation reviewed. That part is yours.

### If setup goes wrong

| What you see | What to say or do |
|---|---|
| Your name is missing from the reviewer list | **"My name isn't in the reviewer list."** You are probably not on the team yet — an admin has to add you, then it can be refreshed. |
| It complains about permissions when checking the reviewer list | Tell it the exact message. There is a one-line fix it knows. |
| The review screen address will not open | **"The review screen isn't loading — can you restart it?"** |
| It starts changing the house rules or the tooling | **"Stop — leave those alone and tell me what you think is wrong instead."** Those files are for admins. |
| It starts filling in review verdicts for you | **"Stop. I'll do the reviewing."** An AI-written verdict is exactly the input that produces a confidently wrong change. |
| Anything else fails | **"Which step failed, and what was the error?"** Do not let it work around a failure silently. |

---

## After setup: every other day

You do not normally paste anything again. Just say:

> **"Get me set up for reviewing."**

That brings things up to date, fetches new conversations, and opens the review screen.

**The one exception.** When an admin tells you the process itself has changed, paste
[`contributor-update-prompt.md`](contributor-update-prompt.md) — again, **the whole file**, same
as the setup one. It makes your AI re-read the house rules rather than working from what it
remembers, which matters because those rules do change.

Signs it is working from stale rules: it insists you must fill in the dropdown boxes, it wants
to publish something before it has been approved, or it does not know what it may and may not
change. If you see any of those, paste the update page.

### What a good update run looks like

- **Nothing of yours thrown away.** It should check for unsaved work *before* updating and keep
  it. If it ever offers to discard your changes to get a clean start, say **"no — keep my
  work."**
- It can tell you, in its own words, what changed since last time: what you may edit, whether
  you have to fill in the boxes, and what has to happen before anything goes live. If it just
  repeats your question back, say **"re-read the files properly."**
- The review screen back up, running the new version.

### If it goes wrong during an update

| What you see | What to say |
|---|---|
| It offers to throw away your unsaved work | **"No — keep my work. Save it somewhere first."** |
| It starts editing the house rules or the tooling | **"Stop. Those are admin-only — tell me what you think is wrong instead."** |
| It says you must fill in the dropdowns before it can act | It has not read the current rules. **"Re-read the review instructions — I don't have to fill those in."** |
| It wants to publish something not yet approved | **"Not yet — that has to be approved first."** |
| The review screen looks unchanged after updating | An old copy is still running. **"Restart the review screen."** |

---

## The one thing to understand

You type in plain English. The AI does the fiddly technical parts.

Your job is the **judgement**: reading what the chatbot told someone, deciding whether it was
right, and saying what it should have said instead. The AI's job is everything else — finding
the files, making the changes, checking them, and getting them live.

You do **not** need to know how any of that works. You do need to be clear about what you want.

**A few words that come up a lot:**

| Word | What it means here |
|---|---|
| **the chatbot** / **the assistant** | The helper your colleagues use to ask questions. The thing we are improving. |
| **a transcript** | One saved conversation between a colleague and the chatbot. What you review. |
| **your feedback** | What you write when a transcript's answer was wrong or incomplete. |
| **live** | Actually in the chatbot, where colleagues will see it. Until something is live, your fix hasn't reached anyone. |
| **the review screen** | A page in your web browser where you read transcripts and write feedback. |

---

## The phrasebook

These are the things you will actually say. Copy them; they are not magic words, but they are
clear and they work.

### Getting started for the day

> **"Get me set up for reviewing."**

Brings everything up to date, fetches any new conversations, and opens the review screen. Do
this first, every time — it also picks up anything that changed since you last worked.

It should finish by giving you a web address (something like `http://127.0.0.1:7777`). Open it
in your browser. **That address only works on your own computer** — you cannot send it to a
colleague.

> **"Anything waiting for me?"**

Tells you how many conversations need reviewing, and whether anyone has passed one to you
specifically.

### While you are reviewing

You do this part in your **browser**, not by typing at the AI. Read the question, read the
answer, and if the answer was wrong, write what it *should* have said.

**You do not have to fill in the dropdown boxes.** Writing the correction in your own words is
the valuable bit. The AI works out the rest from what you wrote.

If you are unsure whether an answer is right, say so in your note rather than guessing. A
"not sure, but this looks off to me" is genuinely useful. A confident wrong verdict is not.

**Three things on that screen worth knowing:**

- **A good answer is one click.** If the chatbot got it right, change nothing and click
  **Mark reviewed & next**. The form already says "nothing wrong" — you are just confirming.
  Most conversations are like this, so a batch goes quickly.
- **The little ⓘ next to every box explains it.** Click it for what the box means and what each
  option commits you to. Use it rather than guessing — nobody expects you to know these from
  memory, and the explanations were written for exactly this moment.
- **Not your area? Use "Suggest & next" instead of "Mark reviewed".** It records your opinion
  under your name and hands the decision to whoever owns that subject — set the *awaiting* box
  to them. Your reasoning is kept either way. This is the right move when you can see something
  is off but it is not your call to make; you do not have to stay silent, and you do not have to
  pretend to authority you do not have.

### Getting your feedback acted on

> **"I've reviewed some transcripts. Please go through my feedback and make the fixes."**

The AI reads everything you wrote, works out what needs to change, and makes the changes. It
will read **all** your feedback together before starting, because often several of your notes
turn out to be the same underlying problem.

It will come back and tell you what it changed. **Read that summary** — it is where you find
out if it misunderstood you.

> **"Go ahead and wrap up the changes."**

This is the one that finishes the job. It means: *save my work properly, get it approved, and
put it live in the chatbot so colleagues actually benefit.*

Nothing reaches the chatbot until you say something like this. If you stop after reviewing,
your feedback sits there and nobody sees the improvement.

### Checking your fix actually worked

> **"Is that live now? Can you check by asking the chatbot the same question?"**

Worth asking. There is a real difference between *"the file has been updated"* and *"the
chatbot now gives the right answer"* — and only the second one matters. The AI can ask the
chatbot the original question and show you the reply.

If it comes back still wrong, that is useful, not a failure. Say **"that's still not right"**
and it will dig further.

### Finding a specific conversation again

> **"Give me the link to that conversation."**

You will get a web address you can click. If the AI ever refers to a conversation by a jumble
of letters and numbers, ask for the link and the question that was asked — you should not have
to decode anything.

---

## Phrases that keep you in control

Use these freely. You cannot break anything by saying them.

> **"Stop."** / **"Wait, I'm not done."**

Halts what it is doing. Use it any time, including mid-task.

> **"Don't do that."** / **"Leave that file alone."**

Tells it not to make a change it just proposed.

> **"Ask me before you change anything else."**

Makes it check with you first. Useful if you are not sure what it is about to do.

> **"Why did you do that?"** / **"Explain that in plain English."**

Ask this whenever an explanation goes over your head. It should answer without jargon. If it
doesn't, say **"simpler please"** — that is a reasonable request, not a silly one.

> **"That's wrong — actually, ..."**

Correct it directly. It will not be offended, and correcting it early saves undoing work later.
You know the subject matter; it does not.

---

## When the AI asks *you* a question

It will sometimes stop and ask you something instead of guessing. **That is deliberate and it
is a good sign** — a wrong guess about your feedback puts wrong information in front of
colleagues, and that is much harder to unpick than answering a question now.

Answer in plain words. "The first one", "no, I meant the other thing", "I don't know — who
would?" are all perfectly good answers. **"I don't know"** is genuinely fine; it will suggest
who might.

It should ask you **one thing at a time**. If you get a wall of questions, say
**"one at a time please"**.

---

## Three things not to do

**1. Never type a password, key or token into the chat.** If it needs one, it should tell you
where to put it yourself. Nothing about this work requires you to paste a secret into a
conversation.

**2. Don't let it rewrite the instructions.** There are a handful of files that tell everyone —
including the AI — how this work is done. Those are for the admins to change. If your AI offers
to "tidy up" or "improve" one of them, say **"leave that alone, just tell me what you think is
wrong with it."** It should then report the problem rather than fixing it.

The reason is subtle but real: an AI that edits its own instructions then follows its own
edited version, and nobody reviewing the work can tell which rules it was actually working to.

**3. Don't assume silence means success.** If you are not sure something worked, ask. "Did that
work?" and "show me" are always fair.

---

## A whole session, start to finish

What a normal hour looks like:

1. **"Get me set up for reviewing."**
   → It brings things up to date and gives you the review-screen address.

2. Open the address. Read a few conversations. Where an answer was wrong, write what it should
   have said. Click **Mark reviewed** on each one.

3. **"I've reviewed some transcripts. Please go through my feedback and make the fixes."**
   → It reads everything, makes changes, and tells you what it did.

4. Read the summary. If something looks wrong: **"that's not what I meant — ..."**

5. **"Go ahead and wrap up the changes."**
   → It saves everything, gets it approved, and puts it live.

6. **"Is that live now? Check by asking the chatbot one of those questions."**
   → It shows you the chatbot's new answer.

That is the whole loop. Steps 2 and 4 are yours; the rest it does for you.

---

## If something feels stuck

| What you are seeing | What to say |
|---|---|
| The review screen address does not open | **"The review screen isn't loading — can you restart it?"** |
| Your name is not in the reviewer list | **"My name isn't in the reviewer list."** (You may not be on the team list yet — it will explain.) |
| It is doing something you did not ask for | **"Stop. That's not what I asked for."** |
| You do not understand what it just told you | **"Explain that in plain English."** |
| You have lost track of where things stand | **"Where are we? What's done and what's left?"** |
| It has been quiet for a long time | **"What are you doing right now?"** |

If you are stuck for more than a few minutes, ask an admin. Nothing here is urgent enough to
guess at, and a wrong guess costs more time than the question.

---

## The short version

- You judge; it does the technical work.
- Write what the answer *should* have said. Skip the dropdowns if you like.
- **"Go ahead and wrap up the changes"** is what actually gets your fix to colleagues.
- Ask **"is it live?"** — updated is not the same as working.
- **"Stop"**, **"that's wrong"** and **"explain in plain English"** are always available.
- Never paste a password or key into the chat.
