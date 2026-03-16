# Bounty Verification Bot 🤖

GitHub Action that automatically verifies bounty claims by checking:
- ✅ GitHub follow status
- ⭐ Repository star counts
- 💰 Wallet existence (RustChain)
- 🔗 Article URL validity
- 📋 Previous claim history

## Usage

Add to your bounty issue repo as `.github/workflows/bounty-verify.yml`:

```yaml
name: Bounty Verification

on:
  issue_comment:
    types: [created]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: Scottcjn/bounty-bot@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          rustchain-node-url: 'https://50.28.86.131'
          follow-required: 'true'
          rtc-per-star: '1.0'
          follow-multiplier: '1.5'
```

## How It Works

1. **Trigger**: Listens for new comments on issues
2. **Detection**: Looks for claim keywords (`claiming`, `wallet:`, `stars:`, etc.)
3. **Verification**:
   - Checks if user follows @Scottcjn (via GitHub API)
   - Counts stars on Scottcjn repos
   - Queries RustChain node for wallet balance
   - Validates article URLs (dev.to, Medium, GitHub)
   - Checks for previous claims on the issue
4. **Output**: Posts a verification table comment

## Example Output

```markdown
## 🤖 Automated Verification for @username

| Check | Result |
|-------|--------|
| Follows @Scottcjn | ✅ Yes |
| Scottcjn repos starred | 45 |
| Wallet `RTCabc123...` | ✅ Balance: 10.5 RTC |
| Article links | 1/1 live |
| Previous claims | ✅ None |

**💰 Suggested payout**: 67.5 RTC
```

## Configuration

| Input | Default | Description |
|-------|---------|-------------|
| `github-token` | `${{ github.token }}` | GitHub API token |
| `rustchain-node-url` | `https://50.28.86.131` | RustChain node URL |
| `follow-required` | `true` | Require following @Scottcjn |
| `min-stars` | `0` | Minimum stars required |
| `rtc-per-star` | `1.0` | RTC reward per star |
| `follow-multiplier` | `1.0` | Bonus multiplier for following |

## Building

```bash
npm install
npm run build
```

## License

MIT
