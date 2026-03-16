# 🤖 Bounty Verification Bot

**Automated verification for RustChain bounty claims**

This bot automatically verifies bounty claim submissions by checking:
- ✅ GitHub star count on @Scottcjn repos
- ✅ Follow status (@Scottcjn)
- ✅ RustChain wallet existence and balance
- ✅ Article URL validity (dev.to, Medium, etc.)
- ✅ Article word count and quality
- ✅ Duplicate claim detection

## 🎯 Why This Matters

Manual verification takes **2-5 minutes per claim**. With 20+ claims per session, that's **over an hour** of repetitive API checking. This bot does it in **seconds** and never makes math errors.

## 🚀 Quick Start

### Option 1: GitHub Action (Recommended)

1. Copy `.github/workflows/verify-claims.yml` to your repository
2. Add secrets to your repository:
   - `GITHUB_TOKEN` (auto-provided by GitHub Actions)
   - `RUSTCHAIN_NODE_URL` (optional, defaults to `https://rustchain.org`)
3. The bot will automatically run on new comments containing "bounty"

### Option 2: Standalone Python Script

```bash
# Install dependencies
pip install requests

# Run verification
python bounty_verifier.py
```

### Option 3: Import as Module

```python
from bounty_verifier import BountyVerifier

verifier = BountyVerifier(github_token='your_token')

claim_comment = """
Claiming this bounty!
Wallet: newffnow-github
Stars: 50
GitHub: newffnow
Article: https://dev.to/example/article
"""

results = verifier.verify_claim('newffnow', claim_comment)
print(verifier.format_verification_report(results))
```

## 📋 Claim Format

Users should submit claims in this format:

```markdown
Claiming this bounty!

**Wallet:** RTCxxxxxxxxxxxxxxx
**Stars:** 50
**GitHub:** username
**Article:** https://dev.to/username/article-title

[Optional: Additional notes]
```

## 📊 Verification Report Example

The bot posts a comment like this:

```markdown
## 🔍 Automated Verification for @username
_Verified at 2026-03-17T06:12:00Z_

| Check | Result |
|-------|--------|
| Follows @Scottcjn | ✅ Yes |
| Scottcjn repos starred | 45 |
| Wallet `RTCxxx` exists | ✅ Balance: 10.50 RTC |
| Article link | ✅ Live (dev.to, 612 words, good) |
| Previous claims | ✅ None found |

### 💰 Suggested Payout

**67.5 RTC**

**Breakdown:**
- Stars: 45 × 1.0 RTC = 45.0 RTC
- Follow bonus (×1.5): Applied
- Wallet bonus: +5 RTC
- Article bonus: +10 RTC

---
_This is an automated verification. Final payout decision by @Scottcjn._
```

## ⚙️ Configuration

### Payout Rules

Edit these constants in `bounty_verifier.py`:

```python
RTC_PER_STAR = 1.0          # Base rate per star
FOLLOW_MULTIPLIER = 1.5     # Multiplier if following + min stars
MIN_STARS_FOR_MULTIPLIER = 45  # Minimum stars for multiplier
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Recommended | `''` | GitHub PAT for API access |
| `RUSTCHAIN_NODE_URL` | Optional | `https://rustchain.org` | RustChain node URL |

## 🔒 Security

- ✅ No private keys stored
- ✅ Read-only API access
- ✅ No external dependencies beyond `requests`
- ✅ Rate-limit friendly (respects GitHub API limits)
- ✅ Open source and auditable

## 📁 File Structure

```
bounty-bot/
├── bounty_verifier.py          # Main verification logic
├── .github/
│   └── workflows/
│       ├── verify-claims.yml   # GitHub Action workflow
│       └── auto_verify.py      # Action entry point
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

## 🧪 Testing

```bash
# Run built-in demo
python bounty_verifier.py

# Test with specific claim
python -c "
from bounty_verifier import BountyVerifier
v = BountyVerifier()
r = v.verify_claim('testuser', 'Claiming! Wallet: test123 Stars: 10')
print(v.format_verification_report(r))
"
```

## 🎯 Payout Milestones

| Feature | Reward |
|---------|--------|
| Star/follow verification | 30 RTC |
| Wallet existence check | +10 RTC |
| Article/URL verification | +10 RTC |
| Dev.to word count + quality | +10 RTC |
| Duplicate claim detection | +15 RTC |
| **Total** | **75 RTC** |

## 📝 License

MIT License - feel free to fork and improve!

## 👤 Author

**刘颖 (Liu Ying)** - OpenClaw AI Assistant

Built for the RustChain bounty program.

## 🙏 Acknowledgments

- Inspired by the RustChain bounty verification workflow
- Thanks to @Scottcjn for creating the bounty program
