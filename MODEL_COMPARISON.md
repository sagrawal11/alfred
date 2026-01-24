# LLM Model Comparison for SMS Assistant

## Current Setup
- **Model:** Gemini 2.5 Flash (via `google.generativeai`)
- **Cost:** Free tier (student account)
- **Rate Limits:** 5 req/min, 20 req/day (free tier)
- **Status:** ⚠️ Deprecated SDK (`google.generativeai` is deprecated, should migrate to `google.genai`)

## Use Case Requirements
Your SMS assistant needs:
1. **Structured extraction** (JSON parsing for food, workouts, reminders)
2. **Intent classification** (18 different intents)
3. **Entity extraction** (times, dates, people, locations)
4. **Fast response times** (SMS users expect quick replies)
5. **Cost-effective** (scalable as user base grows)
6. **Reliable** (high uptime, consistent quality)

## Model Options Comparison

### 1. **Gemini 2.5 Flash** (Current)
**Pros:**
- ✅ Free tier available (student accounts)
- ✅ Fast inference (~200-500ms)
- ✅ Good structured output (JSON)
- ✅ Competitive pricing at scale
- ✅ Google's infrastructure (reliable)

**Cons:**
- ⚠️ Free tier rate limits (5/min, 20/day) - very restrictive
- ⚠️ SDK deprecation (need to migrate to new `google.genai`)
- ⚠️ Rate limiting can cause delays

**Pricing (Paid Tier):**
- $0.075 per 1M input tokens
- $0.30 per 1M output tokens
- **Estimated cost:** ~$0.001-0.002 per SMS message (assuming 50-100 tokens)

**Verdict:** Good for development, but free tier too restrictive for production.

---

### 2. **OpenAI GPT-4o-mini** (Recommended for Production)
**Pros:**
- ✅ **Best price/performance ratio** for structured tasks
- ✅ Excellent JSON mode (structured outputs)
- ✅ Fast inference (~300-600ms)
- ✅ Very reliable API
- ✅ No rate limits on paid tier (reasonable limits)
- ✅ Great for intent classification and extraction

**Cons:**
- ❌ No free tier (but very cheap)
- ❌ Requires API key setup

**Pricing:**
- $0.15 per 1M input tokens
- $0.60 per 1M output tokens
- **Estimated cost:** ~$0.002-0.004 per SMS message

**Verdict:** ⭐ **Best choice for production** - slightly more expensive than Gemini but more reliable and better structured outputs.

---

### 3. **Anthropic Claude Haiku 3.5**
**Pros:**
- ✅ Fastest inference (~100-300ms)
- ✅ Very cheap
- ✅ Good structured outputs
- ✅ Reliable API

**Cons:**
- ❌ No free tier
- ❌ Slightly less capable than GPT-4o-mini for complex tasks

**Pricing:**
- $0.25 per 1M input tokens
- $1.25 per 1M output tokens
- **Estimated cost:** ~$0.003-0.005 per SMS message

**Verdict:** Good alternative, but GPT-4o-mini is better value.

---

### 4. **OpenAI GPT-4o** (Overkill)
**Pros:**
- ✅ Best quality
- ✅ Excellent for complex reasoning

**Cons:**
- ❌ Expensive ($2.50/$10 per 1M tokens)
- ❌ Overkill for simple SMS parsing
- ❌ Slower than mini

**Verdict:** Not needed for this use case.

---

### 5. **Local Models (Ollama, LM Studio)**
**Pros:**
- ✅ **$0 per request** (runs on your hardware)
- ✅ No rate limits
- ✅ Privacy (data stays local)
- ✅ No API dependencies

**Cons:**
- ❌ Requires GPU/server infrastructure
- ❌ Slower inference (unless you have good hardware)
- ❌ Less reliable structured outputs
- ❌ Setup/maintenance overhead
- ❌ May need fine-tuning for your use case

**Models to consider:**
- **Llama 3.1 8B** - Good balance, ~8GB VRAM
- **Mistral 7B** - Fast, good structured outputs
- **Phi-3 Medium** - Smaller, faster, less capable

**Verdict:** Good for privacy-sensitive deployments, but requires infrastructure investment.

---

## Cost Analysis (Per 1,000 SMS Messages)

Assuming average 50 tokens input, 30 tokens output per message:

| Model | Cost per 1K messages | Monthly (10K msgs) | Monthly (100K msgs) |
|-------|---------------------|-------------------|---------------------|
| **Gemini 2.5 Flash** | $0.10-0.20 | $1-2 | $10-20 |
| **GPT-4o-mini** | $0.20-0.40 | $2-4 | $20-40 |
| **Claude Haiku** | $0.30-0.50 | $3-5 | $30-50 |
| **Local (Ollama)** | $0 (hardware cost) | $0 | $0 |

---

## Recommendation

### **For Development (Now):**
✅ **Keep using Gemini** (free tier is fine for testing)
- Migrate to new `google.genai` SDK
- Use for Phase 4-5 development

### **For Production (Later):**
⭐ **Switch to GPT-4o-mini** when you launch
- Best price/performance
- Excellent structured outputs
- Reliable API
- No restrictive rate limits

### **Migration Strategy:**
1. **Phase 1-5:** Use Gemini (free tier)
2. **Phase 6+:** Add GPT-4o-mini as option
3. **Production:** Switch to GPT-4o-mini, keep Gemini as fallback

---

## Implementation: Multi-Model Support

I can refactor `GeminiClient` to be a generic `LLMClient` that supports:
- Gemini (current)
- OpenAI GPT-4o-mini
- Claude Haiku
- Easy to add more

This would let you:
- Test different models
- Switch models via config
- Use different models for different tasks
- Fallback if one model fails

**Would you like me to:**
1. Fix the current Gemini bug
2. Add multi-model support (Gemini + GPT-4o-mini)?
3. Or just document this for later?

---

## Quick Wins

1. **Migrate to new Gemini SDK** (`google.genai` instead of deprecated `google.generativeai`)
2. **Add caching** - Cache common intents/entities to reduce API calls
3. **Batch requests** - If processing multiple messages, batch them
4. **Use cheaper models** - GPT-4o-mini for simple tasks, Gemini for complex

---

## Bottom Line

**For now:** Gemini free tier is fine for development.

**For production:** GPT-4o-mini is the sweet spot - only ~$0.002 per message, excellent quality, reliable.

**At scale (100K+ messages/month):** Consider local models or hybrid approach (local for simple, cloud for complex).
